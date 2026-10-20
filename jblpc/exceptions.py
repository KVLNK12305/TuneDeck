"""
Custom exception hierarchy for JBLPc.

Guarantees clean, one-line error messages without raw tracebacks shown to the user.
"""


class JBLPcError(Exception):
    """Base exception for all JBLPc errors."""
    pass


TuneDeckError = JBLPcError


class ConfigError(JBLPcError):
    """Raised when configuration file is corrupt, empty, unreadable, or missing required keys."""
    pass


class BluetoothAdapterError(JBLPcError):
    """Raised when the Bluetooth adapter is missing, powered off, or bluetoothctl is unavailable."""
    pass


class DeviceNotPairedError(JBLPcError):
    """Raised when the target device is not paired at the OS Bluetooth level."""
    pass


class ConnectionError(JBLPcError):
    """Raised when Bluetooth RFCOMM connection cannot be established or maintained."""
    pass


JBLConnectionError = ConnectionError


class ProtocolError(JBLPcError):
    """Raised when a frame is malformed, has invalid checksum, unexpected opcode, or corrupt payload."""
    pass


class UnsupportedCommandError(JBLPcError):
    """Raised when a requested command is not supported by the connected device model."""
    pass


class InstanceLockError(JBLPcError):
    """Raised when another instance of JBLPc is already holding the application lock."""
    pass


class TerminalTooSmallError(JBLPcError):
    """Raised when terminal dimensions are insufficient for the TUI."""
    pass
