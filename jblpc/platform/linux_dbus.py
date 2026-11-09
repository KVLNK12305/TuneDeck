"""
Native BlueZ D-Bus backend for JBL device discovery and battery monitoring.

Uses dbus_fast (async D-Bus library) to query the BlueZ object hierarchy
directly, avoiding the 50-200ms latency and parsing fragility of shelling
out to bluetoothctl / upower.

The module is safe to import even when dbus_fast is not installed: everything
is guarded behind the DBUS_AVAILABLE sentinel.
"""

import asyncio
import re
import threading
from typing import Optional, Callable

# ─── Guarded import ──────────────────────────────────────────────────────────

try:
    from dbus_fast.aio import MessageBus  # type: ignore[import-not-found, import-untyped]
    from dbus_fast import (  # type: ignore[import-not-found, import-untyped]
        BusType,
        Variant,
        Message as DBusMessage,
        MessageType,
    )
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    MessageBus = None  # type: ignore
    BusType = None  # type: ignore
    DBusMessage = None  # type: ignore
    MessageType = None  # type: ignore
    class Variant:  # type: ignore
        def __init__(self, type_str, value):
            self.type = type_str
            self.value = value


# ─── Constants ───────────────────────────────────────────────────────────────

BLUEZ_SERVICE = "org.bluez"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
DEVICE_IFACE = "org.bluez.Device1"
BATTERY_IFACE = "org.bluez.Battery1"

# Harman International (0x0057) and HARMAN CO.,LTD. (0x075A)
HARMAN_VENDOR_IDS = {"0057", "075A"}
_MODALIAS_VENDOR_RE = re.compile(r"bluetooth:v([0-9A-Fa-f]{4})", re.IGNORECASE)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_jbl_device_name(name: str) -> bool:
    """Check if a Bluetooth broadcast name belongs to a JBL device."""
    if not name or not isinstance(name, str):
        return False
    return "JBL" in name.upper()


def _is_harman_modalias(modalias: str) -> bool:
    """Check if a BlueZ Modalias string contains a Harman vendor ID."""
    if not modalias:
        return False
    m = _MODALIAS_VENDOR_RE.search(modalias)
    if m:
        return m.group(1).upper() in HARMAN_VENDOR_IDS
    return False


def _unpack_variant(variant):
    """Extract the value from a dbus_fast Variant, or return as-is."""
    if hasattr(variant, "value"):
        return variant.value
    return variant


def _extract_device_props(props: dict) -> dict:
    """Pull standard BlueZ Device1 properties from a variant dict."""
    return {
        "address": _unpack_variant(props.get("Address", "")),
        "name": _unpack_variant(props.get("Name", "")),
        "alias": _unpack_variant(props.get("Alias", "")),
        "connected": _unpack_variant(props.get("Connected", False)),
        "paired": _unpack_variant(props.get("Paired", False)),
        "modalias": _unpack_variant(props.get("Modalias", "")),
    }


def _is_jbl(dev: dict) -> bool:
    """Match a JBL device by name OR Harman vendor ID in Modalias."""
    return (
        _is_jbl_device_name(dev.get("name", ""))
        or _is_jbl_device_name(dev.get("alias", ""))
        or _is_harman_modalias(dev.get("modalias", ""))
    )


def _object_path_to_address(path: str) -> str:
    """Extract a MAC address from a BlueZ object path like /org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF."""
    parts = path.rsplit("/", 1)
    if len(parts) == 2 and parts[1].startswith("dev_"):
        return parts[1][4:].replace("_", ":").upper()
    return ""


# ─── Async core ──────────────────────────────────────────────────────────────

async def _get_managed_objects() -> dict:
    """Query BlueZ GetManagedObjects and return the raw dict."""
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        introspection = await bus.introspect(BLUEZ_SERVICE, "/")
        proxy = bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
        manager = proxy.get_interface(OBJECT_MANAGER_IFACE)
        return await manager.call_get_managed_objects()
    finally:
        bus.disconnect()


async def _discover_jbl_devices_async() -> list[dict]:
    """Discover JBL devices via BlueZ D-Bus ObjectManager."""
    objects = await _get_managed_objects()
    devices = []
    for path, interfaces in objects.items():
        if DEVICE_IFACE not in interfaces:
            continue
        dev_props = _extract_device_props(interfaces[DEVICE_IFACE])
        if not _is_jbl(dev_props):
            continue
        display_name = dev_props["name"] or dev_props["alias"] or dev_props["address"]
        devices.append({
            "address": dev_props["address"],
            "name": display_name,
            "connected": dev_props["connected"],
        })
    # Sort: connected devices first, then alphabetically by name
    devices.sort(key=lambda d: (0 if d.get("connected") else 1, d.get("name", "")))
    return devices


async def _read_battery_async(address: str) -> Optional[int]:
    """Read battery percentage from BlueZ Battery1 interface for a device."""
    objects = await _get_managed_objects()
    addr_upper = address.upper()
    for path, interfaces in objects.items():
        if DEVICE_IFACE not in interfaces:
            continue
        props = interfaces[DEVICE_IFACE]
        dev_addr = _unpack_variant(props.get("Address", ""))
        if dev_addr.upper() != addr_upper:
            continue
        if BATTERY_IFACE not in interfaces:
            return None
        battery_props = interfaces[BATTERY_IFACE]
        pct = _unpack_variant(battery_props.get("Percentage", None))
        if pct is not None and 0 <= pct <= 100:
            return int(pct)
        return None
    return None


async def _check_dbus_available_async() -> bool:
    """Quick connectivity check to the system D-Bus and BlueZ service."""
    try:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        try:
            await bus.introspect(BLUEZ_SERVICE, "/")
            return True
        finally:
            bus.disconnect()
    except Exception:
        return False


async def _subscribe_property_changes_async(
    callback: Callable[[str, str, object], None],
    stop_event: asyncio.Event,
) -> None:
    """
    Listen for PropertiesChanged signals on Device1 and Battery1 interfaces.

    Calls ``callback(address, property_name, new_value)`` when
    ``Connected`` or ``Percentage`` changes.

    Runs until *stop_event* is set.
    """
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        def _on_properties_changed(
            interface_name: str,
            changed_properties: dict,
            _invalidated: list,
            *,
            msg=None,
        ):
            path = msg.path if msg else ""
            address = _object_path_to_address(path)
            if not address:
                return

            if interface_name == DEVICE_IFACE and "Connected" in changed_properties:
                val = _unpack_variant(changed_properties["Connected"])
                callback(address, "Connected", val)

            if interface_name == BATTERY_IFACE and "Percentage" in changed_properties:
                val = _unpack_variant(changed_properties["Percentage"])
                callback(address, "Percentage", val)

        # Subscribe to PropertiesChanged on any BlueZ path
        bus.add_message_handler(lambda msg: None)  # keep bus alive
        match_rule = (
            "type='signal',"
            "sender='org.bluez',"
            f"interface='{PROPERTIES_IFACE}',"
            "member='PropertiesChanged'"
        )
        await bus.call(
            bus.make_method_call(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "AddMatch",
                "s",
                [match_rule],
            )
        )

        # Register a low-level message handler for the signal
        def _message_handler(msg: DBusMessage) -> bool:
            if (
                msg.message_type == MessageType.SIGNAL
                and msg.interface == PROPERTIES_IFACE
                and msg.member == "PropertiesChanged"
                and msg.body
                and len(msg.body) >= 2
            ):
                iface_name = msg.body[0]
                changed = msg.body[1]
                invalidated = msg.body[2] if len(msg.body) > 2 else []
                _on_properties_changed(iface_name, changed, invalidated, msg=msg)
            return False  # do not consume

        bus.add_message_handler(_message_handler)

        # Wait until asked to stop
        await stop_event.wait()
    finally:
        bus.disconnect()


# ─── Synchronous public API ─────────────────────────────────────────────────

def _run_async(coro):
    """Run an async coroutine from synchronous code, safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're inside an already-running event loop — spin up a thread.
        result = None
        exc = None

        def _target():
            nonlocal result, exc
            try:
                result = asyncio.run(coro)
            except Exception as e:
                exc = e

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join()
        if exc:
            raise exc
        return result
    else:
        return asyncio.run(coro)


def check_dbus_available() -> bool:
    """Synchronous check: can we reach the BlueZ service on the system D-Bus?"""
    if not DBUS_AVAILABLE:
        return False
    try:
        return _run_async(_check_dbus_available_async())
    except Exception:
        return False


def find_jbl_devices_dbus() -> list[dict]:
    """
    Discover JBL devices via native BlueZ D-Bus.

    Returns list of dicts matching the format of
    ``protocol.find_jbl_devices()``:
    ``[{"address": "AA:BB:...", "name": "JBL Tune 770NC", "connected": True}, ...]``
    """
    return _run_async(_discover_jbl_devices_async())


def get_battery_level_dbus(address: str) -> Optional[int]:
    """
    Read battery percentage from BlueZ Battery1 via D-Bus.

    Returns integer 0-100 or None if unavailable.
    """
    return _run_async(_read_battery_async(address))


class PropertySubscription:
    """Handle for a running D-Bus property change subscription."""

    def __init__(self):
        self._stop_event: Optional[asyncio.Event] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, callback: Callable[[str, str, object], None]) -> None:
        """Start listening in a background thread."""
        if self._thread is not None:
            return

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._stop_event = asyncio.Event()
            try:
                loop.run_until_complete(
                    _subscribe_property_changes_async(callback, self._stop_event)
                )
            except Exception:
                pass
            finally:
                loop.close()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop listening."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None


def subscribe_property_changes(
    callback: Callable[[str, str, object], None],
) -> PropertySubscription:
    """
    Subscribe to BlueZ property changes (Connected, Percentage).

    The *callback* is called with ``(address, property_name, new_value)``
    from a background thread whenever ``Connected`` or ``Percentage``
    changes on any BlueZ device.

    Returns a :class:`PropertySubscription` handle; call ``.stop()`` to
    unsubscribe.
    """
    sub = PropertySubscription()
    sub.start(callback)
    return sub
