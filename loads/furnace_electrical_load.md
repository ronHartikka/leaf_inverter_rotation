# Furnace as an electrical load

Companion narrative to `furnace.json`. Everything electrical in here is **estimated, not measured** — this file exists to define what to measure and why, and to record the reasoning that does not fit in the JSON.

---

## 1. What the furnace is

Carrier Infinity ICS **58MVC080-F**, 21-inch upflow cabinet, 95% AFUE condensing, three-stage gas valve, variable-speed ECM blower, variable-speed ECM inducer, Infinity communicating control on the ABCD bus.

Three firing rates, not continuous modulation:

| Stage | Gas input | Gas output | Blower CFM |
|---|---|---|---|
| Low | 32,000 | 30,000 | 540 |
| Medium | 52,000 | 49,000 | 695 |
| High | 80,000 | 74,000 | 1,220 |

---

## 2. The headline finding: this is the smallest of the three electrical loads

Estimated draw, low fire: **~79 W, ~0.8 A**. December energy: **~1.0 kWh/day**.

Compare with the fridge (~1.3 kWh/day) and the chest freezer (~1.2 kWh/day). The furnace is the largest *thermal* load in the house by an enormous margin and the *smallest* electrical load of the three. This is counterintuitive enough that it is worth stating plainly before any budgeting.

The reason is that low fire moves only 540 CFM, and ECM shaft power scales roughly as the cube of airflow. High fire at 1,220 CFM is estimated at ~426 W — more than 5× low fire for 2.5× the gas.

---

## 3. Revised system hypothesis: the "1/3 of the time" model is probably unnecessary

Steady-state worst case for all three loads simultaneously:

```
furnace low fire      0.8 A
fridge defrost        1.9 A   (measured)
chest freezer running ~1.5 A
                      -------
                      ~4.2 A  ≈ 480 W  on a 1 kW inverter
```

Aggregate steady draw is not the constraint. **Surge coincidence is**, and the surge exposure is concentrated in exactly one load:

| Load | Motor type | Start behavior |
|---|---|---|
| Kitchen fridge | BLDC inverter compressor | soft-start, measured 1.5 A peak — no LRA |
| Furnace | ECM blower + ECM inducer | soft-ramp over seconds — no LRA |
| Chest freezer | PTC-start induction compressor | **true locked-rotor inrush** |

Two of the three loads have no inrush at all. If the earlier "fridge and freezer can't run together" result was a surge-coincidence failure rather than a steady-state one, then a start-interlock that keeps the freezer compressor from starting within a few seconds of any other event may be enough to run all three concurrently — no time-slicing required.

**Open question for the project:** was the fridge/freezer conflict a surge event or a sustained-draw event? The fridge's 1.9 A defrost step is sustained, and defrost overlapping the freezer's run *plus* its start would be a plausible sustained-plus-surge failure. Worth going back to the captured data before designing the rotation logic around the wrong constraint.

**Side confirmation:** the 1.9 A defrost measurement resolves the overnight overcurrent latch event on the kitchen fridge — the step to ~2.38 A settling to ~1.9 A and held past the 20 s window was defrost heater engagement, not a fault. The latch behaved correctly; the threshold was wrong for that load.

---

## 4. Lock the furnace to low fire — it is free

Set **SW1-2** on the furnace control board (low heat only; also disables adaptive heat mode).

This cuts estimated draw from ~426 W to ~79 W. It costs nothing in heating capacity, and that is not a guess:

- House UA (output side), from regression on 2022–23 daily gas: **310–380 BTU/hr·°F**
- Design load at the local +4 °F design temperature: **20,000–24,000 BTU/hr**
- Low fire output: **30,000 BTU/hr**

Low fire alone exceeds the design load. Continuous low fire would only fail to keep up somewhere around **−13 °F to −30 °F** outdoors. Medium and high fire have almost certainly never fired for steady-state heating in this house — they appear only during recovery from the 63 °F night setback.

The equipment is roughly 3× oversized at high fire and still ~1.4× oversized at its minimum firing rate. In a backup-power scenario that oversizing becomes an asset: there is a legitimate low-draw mode with no comfort penalty.

This is also a better control lever than feeding the furnace false indoor or outdoor temperatures. The Infinity staging algorithm is adaptive and history-dependent — it decides how long to hold low or medium based on the length of the *previous* cycle — so spoofing sensors means fighting something that changes its mind. A DIP switch is deterministic.

---

## 5. Three things that will stop this working, none of them about wattage

### 5.1 Flame rectification needs a bonded neutral

The furnace proves flame by rectifying a microamp-level AC current through the flame to chassis ground. This requires correct line/neutral polarity **and** a neutral-to-ground bond. Many portable inverters have a floating output with no N-G bond.

Failure signature: burner lights, runs 5–7 seconds, drops out, retries, locks out after three or four attempts.

This presents as a gas or flame-sensor fault and is actually an electrical bonding fault. **Verify the inverter's bond before diagnosing anything else.** If the inverter genuinely floats, a bonding plug is the fix — and that bond must never coexist with a grid connection.

### 5.2 Pure sine wave, non-negotiable

ECM blower, ECM inducer, microprocessor control board. Modified sine will at best run the ECM hot.

### 5.3 It is hardwired

Unlike the fridge and freezer, this load is not cord-and-plug. It needs either a cord-and-plug conversion at the junction box or a panel interlock. Never backfeed a receptacle.

Also do not forget the ancillaries: if a **condensate pump** is fitted it must be powered, or the furnace locks out on the condensate switch. Same circuit thinking applies to a humidifier (24 V, 0.5 A max) or electronic air cleaner (115 V, 1.0 A max) if present.

---

## 6. Load-shedding policy: do not shed the furnace

Shed the fridge and freezer; let the furnace run to completion. Three reasons:

1. Restoring furnace power re-triggers the ECM DC-bus charging inrush — tens of amps for about a millisecond. Between normal cycles this never happens, because the ECM module stays energized and is commanded by 24 V PWM inputs rather than by switching line power. A shedding relay reintroduces it on every restore.
2. An aborted cycle wastes a full 17-second igniter warm-up.
3. Repeated aborts drive the control toward a 3-try lockout.

There is no hot-restart *damage* hazard here — unlike the PTC-start compressors, the gas valve simply closes — but the cycle economics are bad.

Two timing constants matter for any rotation logic:

- **Blower off-delay** (selectable 90/120/150/180 s) runs after burner shutoff to extract residual heat. This tail is part of the load and must not be cut short.
- **After any power reset**, the control forces 16 minutes of low heat before it will consider stepping up. Convenient in backup mode, but not something to induce deliberately.

---

## 7. Proposed control constants

| Constant | Proposed | Rationale |
|---|---|---|
| `OVERCURRENT_A` | **4.0** | For low-heat-locked operation (0.8 A steady, 2.4 A igniter). Raise to 6.0 if the stage lock is not engaged. |
| `OVERCURRENT_HOLD_S` | **25** | Must exceed the 17 s igniter warm-up or the latch fires on every normal ignition — the same failure mode as the fridge's 1.9 A defrost step against a 20 s window. |
| `MIN_RUN_S` | TBD | Set from measured full cycle length including blower off-delay. |

Both thresholds are proposals to be re-derived from the measured igniter peak.

---

## 8. Measurement plan

All of it can be done before heating season by forcing heat calls in warm weather. Keep runs short.

### Sensing

- Tap at the **115 V feed at the junction box**, upstream of everything, so blower + inducer + igniter + control board land in one signal.
- The blower access panel has an interlock switch that kills 115 V when opened — plan the tap accordingly.
- **Do not use a 100 A CT.** At 0.8 A that is 0.8% of full scale. Use a 5–10 A split-core, or pass the hot conductor through a larger CT five times for 5× sensitivity.
- Capture **VA and power factor**, not just watts. The inverter is VA-limited. ECM drives without active PFC can run PF 0.5–0.6, which would nearly double apparent power against the watt estimates above. The igniter is resistive. This is the single largest unknown in the whole budget.

### Runs

1. **Low heat locked** — SW1-2 ON. Capture steady W, VA, PF; igniter transient at ≥1 kHz; full sequence timing; standby W between cycles.
2. **Medium heat locked** — SW4-2 ON. Steady W, VA, PF.
3. **High heat** — both stage locks OFF, force a long call. Steady W, VA, PF; stage transition ramp shape and duration.
4. **End-to-end inverter test** — furnace + fridge + freezer on the 1 kW inverter, LEAF in Ready. Does the furnace prove flame at all (the N-G bond check)? What does the inverter do on freezer compressor start? Worst observed combined VA?

Run 4 is the one that actually answers the project question, and it needs an afternoon, not a winter.

**Afterward:** return the stage-lock switches to their original positions and label the setting inside the furnace door.

---

## 9. Duty cycle (measured, via gas)

From utility daily gas exports, 2022–23 season, baseload-subtracted, assuming low fire throughout:

| Month | Runtime fraction |
|---|---|
| Oct | 11% |
| Nov | 25% |
| Dec | 41% |
| Jan | 39% |
| Feb | 36% |
| Mar | 30% |
| Apr | 17% |
| May | 9% |

Season total: 470 CCF of heating gas → 605 full-fire-equivalent hours → **~1,510 clock hours at low fire, 26% of the Oct–May season**.

Peak observed: 2022-12-24 to 12-27 (Elliott cold snap), 5.165 CCF/day → 19,935 BTU/hr average input → **62% duty at low fire**. Even in the worst cold snap in years, the furnace was off nearly 40% of the time. Note that figure is a 4-day interpolated interval average; the true single-day peak inside it was higher.

Gas baseload (water heater, range), for reference when re-deriving: 0.37 CCF/day summer, ~0.50 winter, 0.43 annual average from the regression intercept. Consistent across the summer 2023 and summer 2026 exports.

---

## 10. Open items

- Every furnace electrical measurement
- Power factor / VA for every stage
- Daily local airport-station temperatures for 2022–23 to replace climate normals in the UA regression (would tighten UA from ±20% to ±10% and actually resolve the balance point, which the monthly fit cannot do above ~63 °F)
- Inverter neutral-ground bond verification
- Chest freezer LRA magnitude and duration — the one real surge in the system, and now the critical path for whether all three loads can run concurrently
- Re-examine the original fridge/freezer conflict data: surge event or sustained-draw event?
