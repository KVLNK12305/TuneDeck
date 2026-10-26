# Battery Data: What TuneDeck Can and Cannot Read

This note covers which battery data TuneDeck reads, where it comes from, and
why the battery health numbers are estimates. It is not a protocol
specification. Nothing here comes from a vendor document, and anything not
listed as **confirmed** has not been checked on real hardware.

---

## 1. Sources TuneDeck Reads

| Source | Used for | Status |
|---|---|---|
| OS Bluetooth stack: BlueZ `bluetoothctl info` "Battery Percentage", UPower | Single charge level (0–100 %) | **Confirmed** on Linux with a physical headset (commit 494638e) |
| Windows PnP property `{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2` | Single charge level | Untested |
| macOS `system_profiler SPBluetoothDataType` | Single charge level | Untested |
| Airoha RACE opcode `0x0403`, then `0x0402` (RFCOMM ch 21) | Fallback single level when the OS reports nothing | **Unverified**: payload layout is a guess; on the test headset `0x0402` returned PMU status bytes, not a percentage (494638e) |

TuneDeck queries the OS first because that value is reliable.

## 2. What Is Not Read

- **TWS per-bud and case levels.** No Left/Right/Case decoding is
  implemented. TWS devices show a single level on hardware; the trio display
  exists only in the simulator.
- **Charging state.** It is not decoded from any source.
- **Cycle count, full-charge or design capacity, voltage, temperature.** No
  known JBL control protocol exposes these, and TuneDeck does not try to read
  them.
- **Speakers / PartyBox.** These use a different protocol from Airoha RACE,
  and TuneDeck does not implement it.

## 3. Why Health Is Estimated

With only a charge percentage to work from, any wear or health figure has to
be **estimated from history**, never presented as a hardware value.
`jblpc/health.py` (`BatteryHealthTracker`) does this:

1. **Periodic sampling**: stores timestamped charge readings in a local SQLite
   database (`health.db` in the platform data directory).
2. **Equivalent full cycles (EFC)**: `sum(upward charge deltas) / 100`.
3. **Discharge rate (%/hr)**: rate of drop across non-charging intervals.
4. **Retention trend**: compares the recent discharge rate with the baseline
   window.
5. **Confidence**: `low` / `medium` / `high` based on data span and sample
   count, with plain-language notes when data is insufficient.
