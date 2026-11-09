# Research Document: Airoha RACE PEQ Decompilation & Protocol Specification

> **Status**: Research Guide & Protocol Analysis  
> **Applies to**: JBL Tune Series (Tune 770NC, Tune 230NC, Tune 130NC) & Airoha-based hardware  

---

## 1. Objective

TuneDeck's existing equalizer implementation relies on an unverified opcode (`OP_EQ_SET = 0x0A01`) with a naive raw-byte payload `[len(bands), band0, band1, ...]`. This does not match real Airoha DSP architectures and cannot be confirmed on physical hardware without `TUNEDECK_EXPERIMENTAL=1`.

This document specifies the research workflow to decompile the official mobile companion app and extract the genuine Parametric EQ (PEQ) packet structure.

---

## 2. Target APK Packages

The official Harman / JBL mobile applications for Android:
- **JBL Headphones App**: Package ID `com.harman.hkcompanion` (or `com.jbl.headphone`)
- **Airoha SDK components**: Bundled inside the APK under native and Java namespaces:
  - `com.airoha.race.*`
  - `com.airoha.race.peq.*`
  - `com.airoha.lib.*`

---

## 3. Decompilation Methodology

### Tooling
Use `jadx` (or `apktool` + `jadx-gui`):

```bash
# Decompile the APK
jadx -d ./decompiled_jbl ./jbl_headphones.apk
```

### Search Queries & Grep Targets

Search for Airoha RACE command builders and PEQ constants:
```bash
cd ./decompiled_jbl
# Search for RACE opcodes related to EQ
grep -rn "0x0A0" .
grep -rn "0x0E0" .
grep -rn "RACE_PEQ" .
grep -rn "PEQ_SECTOR" .
grep -rn "setPeq" .
grep -rn "Biquad" .
```

---

## 4. Expected Airoha RACE PEQ Architecture

Based on Airoha AB156x / AB158x DSP firmware specifications, genuine PEQ packet structures do not transmit raw ASCII or integer gains. Instead, they structure equalization into **Biquad IIR Filter Banks**:

### Biquad Filter Formula
$$H(z) = \frac{b_0 + b_1 z^{-1} + b_2 z^{-2}}{a_0 + a_1 z^{-1} + a_2 z^{-2}}$$

### Expected Payload Fields
1. **Target Subsystem / Channel**: Left, Right, or Stereo master.
2. **Band Index**: $0 \dots N-1$ (e.g. 10 bands for Tune 770NC, 5 bands for Tune 230NC).
3. **Filter Type**:
   - `0x00`: Peaking / Bell filter
   - `0x01`: Low Shelf
   - `0x02`: High Shelf
   - `0x03`: High Pass / Low Pass
4. **Center Frequency ($f_0$)**: 16-bit or 32-bit fixed point (Hz).
5. **Quality Factor ($Q$)**: 16-bit fixed point ($Q \times 1000$).
6. **Gain ($G$)**: 16-bit signed fixed point ($dB \times 100$).
7. **Pre-Scale Attenuation**: Master digital headroom trim ($dB$) to prevent $0\text{ dBFS}$ intersample clipping.

---

## 5. Software Safety Integration

Until real hardware responses validate the exact decompiled opcode, TuneDeck retains:
1. `TUNEDECK_EXPERIMENTAL=1` hardware command gate.
2. Digital headroom scaling calculation via `jblpc.dsp.calculate_preamp_headroom()`.
3. Fully functional and animated UI simulation curves across CLI, TUI, and GUI.

