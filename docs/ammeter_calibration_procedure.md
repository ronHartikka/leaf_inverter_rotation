# The Ammeter — calibration procedure

Written 2026-10-02 from Ron's draft. Purpose: calibrate the Ammeter over the range it
will actually be used in, without needing Claude.

**Why this exists.** The Ammeter's previous fit was anchored at 2.00 A and 4.98 A for
surge work. The sketch's own comment records the hazard: *a fit anchored outside the
range actually used mispredicted 2.00 A by 5.6%*. The next job is the furnace, which
lives at **0.8 A steady and 2.4 A during the 17 s igniter warm-up**, so the fit has to be
taken over that span.

---

## Hardware

- **The Ammeter** — ACS712 (20 A) → ADS1115 → (level shifter) → Wemos Lolin32.
  The ACS712, ADS1115 and level-shifter high side run on the **7805**; the ESP32 runs on
  USB. See "The rail" below.
- **The DMM** — KAIWEETS ____________ (fill in model)
- **Lab power supply (PS)** — generic 30 V / 5 A, or any current source
- **Leads** suitable to carry PS current to the ACS712 (22 AWG silicone wire works)
- **Laptop** with CoolTerm

## Firmware

`firmware/esp32_ads1115_cycle_stats/esp32_ads1115_cycle_stats.ino` — the same sketch used
for measurement. There is no separate calibration program and none is needed.

Serial is **115200 baud**. Output columns:

```
t_ms, n, mean_v, dc_a, rms_a, pk_a
```

- **`mean_v`** is the raw differential volts. **This is the calibration quantity.**
- On a DC run `rms_a` falls to ~0 — a useful confirmation the run is clean.
- `dc_a` uses the constants currently compiled in, so it is wrong until step 17. Ignore it
  until then, when it becomes the verification.

---

## The rail — RESOLVED 2026-10-02

**The ACS712 runs on the 7805's regulated output, measured 5.012 V.**

The ESP32's 5 V pin was originally tied to the same bus, so the ACS712 was actually being
fed by USB-derived 5 V (4.805 V — USB less the board's protection-diode drop). That link
was cut on 2026-10-02. The 7805 now feeds exactly the ACS712, the ADS1115 and the level
shifter's high side; the ESP32 stays on USB for serial. Grounds remain common, and the
level shifter is the boundary between the two domains. Verified working: the ESP32 talks
to the Mac and the system responds to current.

**Why it matters.** The ACS712's zero is its own Vcc/2 and its volts-per-amp scales with
the same rail, so everything it reports rides on that supply. The two rails differ by
**4.3%** (5.012 vs 4.805 V) — which is the size of the error the sketch's ratiometric
correction existed to chase, and it was previously set by whichever cable and port were in
use that day.

**Consequence: the rail is now a property of the instrument, not of the session.**

| | |
|---|---|
| `VCC_CAL` | the rail measured at calibration — a constant of the instrument |
| `VCC_NOW` | the same value, unless the 7805's output has actually changed |

So there is **no per-session re-flash**. Mac or Dell, this cable or that one, bench or
furnace — none of it touches the ACS712's supply any more. Re-measure the rail only if the
7805's input supply changes, or occasionally as a check; a 7805 drifts slightly with
temperature and load, but it is a different order of problem from USB.

**Measure at the ACS712's own Vcc pin**, not at the 7805's terminal, so any drop in
between is included.

**One sequencing rule from the change.** The 7805 should be powered whenever USB is. With
the 7805 off, the ESP32 would be driving level-shifter and I²C lines into unpowered parts.
The level shifter limits this to pull-up currents, so the realistic worst case is that I²C
fails rather than that something is damaged — but there is no reason to run it that way.

---

## Procedure

### Setup

**0.** Connect the laptop to the Wemos Lolin32 by USB.

**1. Let the Ammeter warm up.** The ACS712's zero-current offset drifts with die
temperature, and the 7805's output drifts as it heats. Everything below assumes one stable
offset across the whole session.

*Criterion, not a fixed time:* with **zero current flowing**, watch `mean_v`. When it stops
trending and only jitters, it is warm. Re-check the rail at that point.

**2. Measure the rail** at the ACS712's Vcc pin with the DMM (see "The rail" above).
Record it. Measure it warm, after step 1 — a cold rail is not the one you will be
calibrating against.

**3. No edit and no re-flash are needed before collecting data.**

The sketch has four calibration constants:

| constant | line | what it is |
|---|---|---|
| `V_OFFSET_CAL` | ~71 | fitted intercept, volts |
| `SENS_CAL` | ~72 | fitted slope, volts per amp |
| `VCC_CAL` | ~69 | the rail those two were measured at |
| `VCC_NOW` | ~79 | the rail in use now |

It computes `scale = VCC_NOW / VCC_CAL` and applies it to both `V_OFFSET_CAL` and
`SENS_CAL`, because the ACS712's zero and its volts-per-amp both ride on its supply.

**None of the four touches `mean_v`**, which is the raw differential reading and the only
column this calibration uses:

```c
mean_v = mean_c * LSB_V;            // raw -- no constants
dc_a   = (mean_v - offset) / sens;  // constants enter only here
```

So collect the data with whatever is currently compiled in, and enter all four constants
**once**, at step 16. `dc_a` will read wrong during collection — ignore it; it becomes the
verification at step 18.

**4.** Set the unloaded PS to **2 V** (exact value not critical — low, so a wiring error
cannot dump much).

**5.** Turn the current-limit Coarse and Fine knobs to minimum.

**6.** Wire the loop so the PS is shorted **through the DMM and the ACS712 in series**:

```
PS(+) → DMM → ACS712 current terminals → PS(−)
```

**7.** Set the Fine knob to the middle of its range.

**8.** Raise the Coarse knob until the PS display shows roughly the first calibration
point.

**9.** Read the current on the DMM and trim to the target. **The DMM is the reference —
ignore the PS display.** Measured 2026-10-01: the PS reads low by 5.2% at 0.5 A and 2.8%
at 2 A. The DMM's 600 mA and 10 A ranges agree with each other to 0.6%, so either may be
used.

### Taking the readings

**10. LOWER point — target 0.8 A.**

- Start the CoolTerm capture **before** connecting the port, so the `#` header lines land
  in the file. They state which constants were compiled in — that is the run's provenance.
- Let the reading settle; discard the rows recorded during the change.
- Average `mean_v` over **20–30 s** (≈1200–1800 rows) → **LOWER_V**
- Record the DMM current at the same time → **LOWER_A**

**11. UPPER point — target 2.4 A.** Repeat step 10. → **UPPER_A**, **UPPER_V**

Keep the polarity the same as the LOWER point and do not disturb the sensor wiring.

**12. Optional but worth it — MID point, target ~1.5 A.** Repeat step 10. It should fall
on the line through the other two within ~1%. If it does not, the part is nonlinear across
the working range and the anchors should be narrowed.

### Computing

**13.** Both currents run the **same direction**. The offset is common to both readings and
cancels in the subtraction, so polarity reversal is not needed to get the slope:

```
sens   = (UPPER_V - LOWER_V) / (UPPER_A - LOWER_A)
offset = LOWER_V - sens * LOWER_A
```

`offset` is the fitted line's intercept at zero current — an extrapolation, and correctly
so. `dc_a = (mean_v - offset) / sens` only has to be right over 0.8–2.4 A.

> **Why not polarity reversal?** Reversing at ±I gives a secant symmetric about **zero**,
> but the working range is entirely on one side. On a part whose nonlinearity is referred
> to full scale those are different secants — which is the exact failure the sketch's
> comment records. Reversal is a zero check (step 15), not a slope method.

**14. Sanity-check before accepting.**

| constant | expect | currently in file |
|---|---|---|
| `sens` | near 0.100 V/A (ACS712-20A nominal) | 0.10174 |
| `offset` | tens of millivolts | 0.01240 V |

If either is far from those, **stop and find the wiring or arithmetic error** rather than
shipping it.

**15. Optional zero check — polarity reversal at one current.** Record `mean_v` with the
current one way (V₊) and reversed (V₋), reading the DMM separately each time:

```
offset_rev = (V+ + V-) / 2
```

Compare with the fitted `offset`. A difference means the part is nonlinear between 0 and
0.8 A. **Record it; do not change the constants.** Reversal cancels every additive offset
in the chain — sensor zero and ADS1115 offset together — so it is a genuine independent
measurement of the zero.

### Installing and verifying

**16.** Enter into the sketch: `V_OFFSET_CAL`, `SENS_CAL`, and the measured rail in both
`VCC_CAL` and `VCC_NOW`.

**17.** Re-flash.

**18. Close the loop.** Set the PS back to one anchor current and confirm **`dc_a` now
reads what the DMM reads.** This is the only step that proves the constants took, and it
catches typos and sign errors.

**19. AC validation** — 80 W resistive load on mains:

| check | expect |
|---|---|
| current | ~0.645 A at 124 V |
| crest factor (`pk_a` / `rms_a`) | ≈ 1.414 (√2); measured 1.4125 last time |
| `rms_a` × line volts | ≈ 80 W |

This now sits just below the working range rather than far outside it.

**20. Record provenance** in the calibration comment block at the top of the sketch: date,
rail voltage, DMM model and ranges used, anchor currents, old and new constants, and the
validation result. Leave superseded values commented out, as the file already does.

**21. Commit.**

---

## Two don'ts

Both follow from the drift reason behind step 1 — everything above assumes **one offset
across the whole session**:

- **Do not split the anchors across sessions or a power cycle.**
- **Do not disturb the sensor wiring between anchors.**

---

## Data sheet

Date: ____________  Operator: ____________

Rail (VCC) measured: __________ V    Warm-up confirmed (step 1): ☐

DMM model: ______________  Range used: ☐ 600 mA  ☐ 10 A

| point | target | DMM current (A) | averaged `mean_v` (V) | rows averaged |
|---|---|---|---|---|
| LOWER | 0.8 A | | | |
| UPPER | 2.4 A | | | |
| MID (optional) | 1.5 A | | | |

Computed:

```
sens   = (UPPER_V - LOWER_V) / (UPPER_A - LOWER_A) = __________ V/A
offset = LOWER_V - sens * LOWER_A                  = __________ V
```

MID falls on the line within ____ %   ☐ n/a

Optional zero check: V₊ = _______ V at _______ A, V₋ = _______ V at _______ A

```
offset_rev = (V+ + V-) / 2 = __________ V     vs fitted offset __________ V
```

Verification (step 18): PS set to _______ A, DMM reads _______ A, `dc_a` reads _______ A

AC validation (step 19): `rms_a` _______ A, `pk_a` _______ A, crest factor _______,
line volts _______ V, computed watts _______ W

Capture file(s): ______________________________________

---

## Rail check log (occasional, not per session)

Since the 7805 was separated from the USB bus there is nothing to do before an ordinary
measurement session. Re-measure the rail only if the 7805's input supply changes, if the
board is reworked, or as a periodic check. If it has moved, set `VCC_NOW` to the new value
and leave `VCC_CAL` and the two calibration constants alone.

| date | rail at ACS712 Vcc (V) | why checked | action |
|---|---|---|---|
| 2026-10-02 | 5.012 | after separating the 7805 from the USB bus | calibration baseline |
| | | | |
| | | | |

Notes: