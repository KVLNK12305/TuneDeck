# JBL Bluetooth Battery Field Protocol Probe Report

**Target Protocols**: Airoha RACE (`0x05 5A/5B/5C`) & JBL Portable / Harman BLE  
**Specification Reference**: Airoha AB156x RACE Command Specification & Harman App Reverse Engineering  
**Scope**: All JBL Consumer Headphones, TWS Earbuds, Portable Speakers, and PartyBox devices.

---

## 1. Executive Summary

Consumer Bluetooth audio firmware prioritizes low latency and minimal Bluetooth packet overhead. When querying battery status over RFCOMM Channel 21 or BLE GATT characteristics:

> [!IMPORTANT]
> **JBL devices do NOT expose hardware cycle counters, full-charge capacity (mAh), design capacity (mAh), voltage (mV), or battery temperature (°C) over their consumer Bluetooth control protocols.**
> 
> The firmware only exposes **battery charge percentage (0–100%)** and **binary charging status (charging / discharging)**. Any metric regarding battery health, wear, cycle counts, or retention degradation on a PC must be mathematically estimated by tracking charge and discharge patterns over time.

---

## 2. Protocol Battery Probe Findings by Device Family

### Family A: Over-Ear & On-Ear Headphones
*(Tune 770NC, Tune 760NC, Tune 720BT, Live 770NC, Live 660NC, Tour One M2, Club 950NC)*

- **Transport**: RFCOMM Channel 21 (Airoha RACE)
- **Battery Request Opcode**: `0x0402` (`OP_BATTERY_GET`)
- **Packet Structure**:
  ```
  Request:  05 5A 02 00 02 04
  Response: 05 5B 03 00 02 04 [Payload: 1 byte]
  ```
- **Field Matrix**:
  | Field Name | Present? | Format | Value Range | Notes |
  |---|---|---|---|---|
  | **Charge Level** | **YES** | `uint8` | `0` – `100` (%) | Current state of charge |
  | **Charging State** | **PARTIAL** | Status event | `0` = Discharging, `1` = Charging | Event notification on USB plug-in |
  | **Charge Cycles** | **NO** | — | — | Not exposed in firmware |
  | **Full-Charge Capacity** | **NO** | — | — | Fuel gauge register not accessible |
  | **Design Capacity** | **NO** | — | — | Hardwired spec (e.g. 500 mAh) |
  | **Battery Voltage** | **NO** | — | — | Locked to factory UART mode |
  | **Battery Temperature**| **NO** | — | — | Not transmitted over RFCOMM |

---

### Family B: True Wireless Earbuds (TWS)
*(Tune 230NC TWS, Tune 130NC TWS, Tune Beam, Tune Flex, Live Pro 2, Tour Pro 2, Wave/Vibe Buds)*

- **Transport**: RFCOMM Channel 21 / BLE GATT
- **Battery Request Opcode**: `0x0402` or vendor query `0x0403`
- **Response Structure**:
  ```
  Response: 05 5B 05 00 02 04 [Left Byte] [Right Byte] [Case Byte]
  ```
- **Field Matrix**:
  | Field Name | Present? | Format | Value Range | Notes |
  |---|---|---|---|---|
  | **Left Bud Level** | **YES** | `uint8` (Bits 0–6) | `0` – `100` (%) | Left earbud charge percentage |
  | **Left Bud Charging** | **YES** | `bit 7` | `0` = No, `1` = Charging | Set when left bud is seated in case |
  | **Right Bud Level** | **YES** | `uint8` (Bits 0–6) | `0` – `100` (%) | Right earbud charge percentage |
  | **Right Bud Charging**| **YES** | `bit 7` | `0` = No, `1` = Charging | Set when right bud is seated in case |
  | **Case Level** | **YES** | `uint8` (Bits 0–6) | `0` – `100` (%) | Charging case battery percentage |
  | **Case Charging** | **YES** | `bit 7` | `0` = No, `1` = Charging | Set when case is plugged into USB |
  | **Charge Cycles** | **NO** | — | — | Not reported for buds or case |
  | **Full-Charge Capacity** | **NO** | — | — | Fuel gauge not queried |
  | **Design Capacity** | **NO** | — | — | Not transmitted |
  | **Voltage (mV)** | **NO** | — | — | Not exposed |
  | **Temperature** | **NO** | — | — | Internal safety cutoff only |

---

### Family C: Portable Speakers
*(Flip 5/6/7, Charge 4/5, Xtreme 3/4, Boombox 2/3, Pulse 4/5)*

- **Transport**: BLE GATT Service / RFCOMM SPP (JBL Portable / PartyBoost)
- **Field Matrix**:
  | Field Name | Present? | Format | Value Range | Notes |
  |---|---|---|---|---|
  | **Battery Percentage** | **YES** | `uint8` | `0` – `100` (%) | Read from Battery Service or vendor GATT |
  | **Power Input State** | **YES** | `uint8` flag | `0` = Battery, `1` = DC/USB In | Indicates external power connection |
  | **Charge Cycles** | **NO** | — | — | Not exposed |
  | **Full-Charge Capacity**| **NO** | — | — | Not exposed |
  | **Design Capacity** | **NO** | — | — | Not exposed |
  | **Voltage / Temperature**| **NO** | — | — | Internal BMS handles safety |

---

### Family D: PartyBox Series
*(PartyBox 110, 310, 710, Stage 320, Club 120)*

- **Transport**: BLE GATT (JBL PartyBox Protocol)
- **Field Matrix**:
  | Field Name | Present? | Format | Value Range | Notes |
  |---|---|---|---|---|
  | **Battery Percentage** | **YES** | `uint8` | `0` – `100` (%) | Single percentage |
  | **AC Main Power** | **YES** | `uint8` flag | `0` = Battery, `1` = AC Mains | Switched mode power status |
  | **Charge Cycles / Health**| **NO** | — | — | Not exposed over Bluetooth |

---

## 3. Engineering Conclusion & Strategy for JBLPc

Since no JBL hardware exposes cycle counters or true state-of-health wear registers over Bluetooth, **JBLPc must never present estimated values as true hardware health**.

Instead, JBLPc implements the **`BatteryHealthTracker`** estimator:
1. **Periodic Sampling**: Collect timestamped readings of battery level and charging state in a local SQLite database (`~/.local/share/jblpc/health.db`).
2. **Equivalent Full Cycles (EFC)**: Sum all positive percentage deltas over time and divide by 100 (`sum(Δcharge) / 100`).
3. **Discharge Rate (%/hr)**: Calculate the rate of percentage drop during active playback / connected non-charging intervals.
4. **Retention Trend**: Compare recent discharge rate against baseline discharge rate from the initial recording window.
5. **Confidence Scoring**: Assign explicit `low`, `medium`, or `high` confidence ratings based on data volume, and display plain-language notes when data is insufficient.
