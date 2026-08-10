# TODO / open work — Load-Rotation Controller

Durable backlog so nothing falls off the table across chats and Claude Code
sessions. Priority order matches how the work should flow. Check items off in
commits as they're done.

---

## HIGH — Get outdoor temperatures for the heating-budget regression

The gas-vs-degree-days check, the UA (house heat-loss) fit, and the balance point
all need an outdoor-temperature series that is NOT in the repo. This is the gating
input for validating the whole furnace thermal model.

- [ ] Pull daily temps for the local airport station covering the gas data span
      (2021-01-02 -> present; 5 full heating seasons now in `data/gas/`).
- [ ] Preferred: DAILY station temps (sharper UA + balance point). Monthly climate
      normals reproduce the stored fit but can't resolve the balance point above ~63 F.
- [ ] Drop into `data/gas/` and wire into `tools/gas_heating_budget.py` (the
      `regress_ua` hook + a degree-day-vs-CCF correlation, base ~= balance point 63 F).
- [ ] Then: confirm seasonal CCF tracks HDD linearly through the origin (the model's
      cleanest internal check) and re-derive UA/balance point across all 5 seasons.

---

## P0 — Temperature conversion correctness (DO NOT LOSE THIS)

Discovered while reviewing `tools/dual_logger.py` for the fridge run. Real bug +
an architecture decision. None of it changes the freezer replace-or-not decision
(duty cycle unaffected), but it matters for clean archival thermal data and for
the fridge's freezer compartment.

### The bug
`dual_logger.py` `res_to_c()` solves ONLY the T >= 0 degC branch of
Callendar-Van Dusen. Below 0 degC, PT1000 needs the sub-zero (4th-order) formula.
So all sub-freezing temps are (in principle) biased. Affects:
- the chest freezer thermal numbers already in `loads/chest_freezer.json`
  (freezer sits ~-20 degC / -5..0 F), and
- the fridge's FREEZER compartment on the upcoming run (~-18 degC).
The fridge's fresh-food compartment (~2-4 degC) is in the valid branch, fine.

**MAGNITUDE CORRECTION [measured 2026-07-20].** The earlier "a few tenths of a
degree C at ~-20 degC" estimate was WRONG by ~2 orders of magnitude. The only
term distinguishing the branches is `C*(T-100)*T^3` with C = -4.183e-12, which at
-20 degC perturbs resistance by ~0.004 ohm ~= 0.001 degC. Measured old-vs-fixed
delta on real capture resistances: <0.005 degF anywhere in the fridge/freezer
range (0.000 degF at the -10 degC freezer readings; +0.004 degF at -25 degC). The
C term only matters far colder (below ~-50 degC). So: the fix is correct and worth
keeping on principle, but it corrects NO meaningful error in this temperature
range. The chest-freezer recompute below is therefore COSMETIC (provenance only),
not a data correction.

### Why it's recoverable
`dual_logger.py` logs raw resistance (`res1_ohm`, `res2_ohm`) in every row.
Ground truth is preserved; only the derived degF column is slightly off. Any
affected temps can be RECOMPUTED from stored resistance. (This is the payoff of
logging the rawest signal — keep doing it.)

### Architecture decision reached (record so we don't relitigate)
- The ESP32 HAS A DISPLAY and must convert resistance->temp for its own screen.
  So "make the ESP32 a dumb resistance-only sensor" is REJECTED — it has a face.
- Principle: log the rawest thing (resistance), derive everything else. KEEP
  resistance logging. It is the audit trail + tiebreaker for cross-checks.
- Two independent witnesses per row is a FEATURE, not redundancy to remove:
  raw resistance (truth), dual_logger degF (to be corrected), and optionally the
  ESP32's own degF (the display's conversion). Keeping all three makes the
  cross-check a permanent property of the data.
- Ron's original instinct (strip dual_logger's math + resistance printing) is
  REVERSED by this: keep resistance, FIX the conversion, treat the ESP32 print as
  the less-trusted witness. The sensor shows a human a number; the logger owns the
  correct archival conversion next to the audit trail where a unit test can pin it.

### Tasks
- [x] Fix `res_to_c()`: add the sub-zero CVD branch (T < 0 degC). DONE 2026-07-20.
      Newton-Raphson on the exact both-branch forward CVD (seam at R == R0),
      self-contained, NO header change, NO consumer edits.
- [x] Add a tiny self-test: `python3 tools/dual_logger.py --self-test` pins
      res_to_c() to 9 IEC 60751 PT1000 table points (-40..+100 degC, both
      branches). PASS, worst error 0.0013 degC (tol 0.05). The IEC table is the
      INDEPENDENT witness (not derived from our own forward formula).
- [x] Cross-check script: `tools/crosscheck_temps.py <capture.raw>`. Ran on
      kitchen_fridge_run.raw (86,108 pairs). THREE-WAY result:
        - logger-degF == independent reference-degF to 0.0000 degF everywhere;
          combined with the self-test => logger == reference == IEC table = RIGHT.
        - ESP32's own Temperature print is the LESS-TRUSTED witness: deviates up
          to 0.30 degF (cold) / 0.79 degF (warm) from correct. Cold-side deviation
          is SMALLER than warm-side => NO shared sub-zero bug (the exact "agree and
          both wrong" failure mode this check existed to rule out is ruled out).
          (Likely cause: the ESP32 prints Temperature from a SEPARATE ADC read than
          the Resistance line, plus 2-decimal rounding, on the noisy breadboard
          rig. Not systematic, not a branch error.)
- [ ] Recompute the chest freezer thermal fields in `loads/chest_freezer.json`
      -> NOW COSMETIC (delta <0.01 degF, see MAGNITUDE CORRECTION above).
      Blocked on the chest-freezer CSV (not in data/ yet; only kitchen_fridge is).
      Low urgency: duty/decision provably unchanged. Bump provenance when done.
- [x] ESP32 serial stream: CONFIRMED from kitchen_fridge_run.raw that each ~1s
      TMP block carries BOTH `Resistance{1,2}=` (ohm) and `Temperature{1,2}=`
      (degF, the sketch's own conversion). dual_logger takes resistance and
      reconverts (correct archival path). Logging ESP32-degF as its own column is
      a HEADER change -> batch with P1/P2, not here.

---

## P1 — Column naming (HEADER change — batch, do when no capture running)

`dual_logger.py` header hardcodes `t1_freezer_f` / `t2_fridge_f`. These name the
dorm-fridge/freezer era, not the physical probes (they're just RTD ch1 / ch2).
For the DUAL-COMPARTMENT fridge (fresh-food + freezer in one appliance) these
names are an active trap: "fridge" vs "freezer" vs "the fresh-food compartment"
gets ambiguous, and you'll misread `--temp-col` weeks later.

Blast radius (why this is NOT a mid-capture tweak): renaming/adding columns
changes the CSV header, which is a CONTRACT with every consumer. Must edit in
lockstep, one atomic commit:
- [ ] `tools/dual_logger.py` header + row writer
- [ ] `analysis/characterize.py` `--temp-col` default + column reads
- [ ] `tools/live_chart.py` plotted column names
- [ ] any Ubuntu-side ad-hoc scripts (enumerate them first)
- [ ] DECISION NEEDED: make scripts tolerant of BOTH old and new headers?
      -> depends on whether old CSVs (dorm fridge, chest freezer) must stay
      re-analyzable. If only fridge-onward data matters, rename freely.
- [ ] Proposed neutral scheme: `t1_f`, `t2_f`, `res1_ohm`, `res2_ohm` in the CSV;
      record probe->compartment mapping in each load JSON's `rtd_channel` field,
      NOT in the header.
- [ ] **DRAFT already landed — do NOT ship piecemeal.** Commit `1700cb2` appended
      three status columns to `dual_logger.py`'s header ONLY: `relay_cmd`,
      `current_stale`, `compressor_on`. (`current_stale` implements the P0 "CAPTURE
      FILE VALIDITY" staleness guard — the merge no longer needs to silently hold a
      stale current value; `relay_cmd` = coast-FSM commanded power; `compressor_on` =
      current-inferred run state, valid only when not stale.) Additive at the end,
      existing readers unaffected, nothing broken — but it IS the piecemeal header
      change this section forbids. FOLD INTO THIS ATOMIC SITTING: propagate all three
      cols + the P1 rename across `dual_logger.py` + `characterize.py` +
      `live_chart.py` + any Ubuntu-side scripts, then scp to the Ubuntu box —
      together, at the **setting-5 restart boundary** (next intentional dial change;
      current config = FFC dial 5, freezer dial 1), when no capture is running.

Do P1 in the same sitting as any P2 column add, since both touch the header.

---

## P2 — Kitchen fridge / freezer characterization (the actual next load)

Dual-compartment real deployment load. Goal: duty cycle + warmup rate PER
COMPARTMENT, running current, inrush (method-limited), thermostat bands. Fill
`loads/kitchen_fridge.json` from `loads/schema.json`.

- [ ] Physically: carry rig upstairs running (laptop on battery keeps the one
      clock alive), plug fridge into the SAME socket the freezer used (keeps the
      current sense channel mapping identical). PAUSE before energizing if the
      fridge ran recently — manual replug bypasses the firmware min-off; hot
      restart is the PTC-stall hazard (lessons.md #2).
- [ ] Probe placement: one RTD in fresh-food air, one in freezer air. Record which
      physical probe -> which compartment -> which CSV column. Let equilibrate
      ~10-20 min before trusting readings (probes are relocating between boxes).
- [ ] START A FRESH CSV (`--out kitchen_fridge_run.csv`), do NOT continue the
      freezer file. Update `REMOTE_CSV` in `tools/watch_run.sh` to the new name.
- [ ] Capture several hours / overnight through multiple cycles.
- [ ] Run `characterize.py` once per compartment (`--temp-col` for each).
      NOTE the sub-zero fix (P0) matters for the freezer-compartment probe.
- [ ] Fill `loads/kitchen_fridge.json`: duplicate the thermal `compartments`
      block into fresh_food + freezer, each with its own rtd_channel / band /
      warmup / pulldown. Add `factory_spec` if it has a sticker/EnerGuide.
- [ ] Update the table in `docs/rotation_budget.md`.

(Ask for the detailed at-the-rig fresh-capture checklist when physically ready —
probe placement, hot-restart pause, exact commands, equilibration wait.)

---

## P3 — Repo hygiene / deferred

- [ ] Replace remaining firmware placeholders with real sketches
      (`hw_verify.ino`, `trial_rotation.ino`), then swap their inline boilerplate
      for the `firmware/shared/*.h` includes. (`characterize_load.ino` is now the
      REAL sketch, landed 2026-07-20; its boilerplate still inline -- fold into the
      shared/ headers as part of the refactor below.)
- [ ] MULTI-LOAD CHARACTERIZER REFACTOR [decided 2026-07-21, do it when we pivot to
      the FURNACE -- NOT before a data run]. To characterize furnace + a replacement
      freezer, keep ONE config-driven `characterize_load.ino` on the shared/ headers,
      NOT 3 separate sketches. Rationale: 3 sketches = 3 copies of safety-critical
      safe-startup/auto-zero/overcurrent/logging that drift (the exact anti-pattern
      shared/ exists to prevent; lessons.md #5). The loads differ ONLY in CONSTANTS,
      not logic: `TARGET_CH`, `OVERCURRENT_A`(+`_MS`), `STARTUP_HOLDOFF_MS` (180 s for
      compressors; short/0 for the furnace -- no compressor). Even the furnace, the
      most different load, needs no special code: the characterizer's job (close one
      relay, log the RMS current curve, hold an overcurrent backstop) is load-agnostic;
      you read the furnace's multi-stage startup in the DATA, not the code. Shape:
      `#define LOAD FRIDGE|FREEZER|FURNACE` -> per-load config table
      { ch, overcurrent_a, overcurrent_ms, holdoff_ms }; common machinery in shared/.
      This same change completes the "swap inline boilerplate for shared/ includes"
      item above. KEEP IT MINIMAL -- the characterizer is a throwaway measuring tool;
      real per-load behavior (compressor vs furnace sequencing, defrost, min-off)
      belongs in the PRODUCTION firmware driven by loads/*.json, not here.
- [x] `requirements.txt` (or freeze) so the venv is reproducible
      (matplotlib 3.11.1 etc.). DONE 2026-08-04 — frozen from the venv (commit f25a6c8).
- [ ] Push repo edits of `dual_logger.py` back to the Ubuntu box after changes
      (repo is now the reference copy; Ubuntu runs its own — keep them in sync;
      the running process won't pick up edits until restarted).
- [ ] Optional DHCP reservation on router as mDNS backup (belt + suspenders).
- [ ] Later loads: furnace after the fridge. Re-characterize the REPLACEMENT
      freezer when it arrives — do NOT inherit the old unit's numbers.

---

## Later — production firmware

- [ ] Assemble the Claude Code production-firmware build (foundation ready: pin
      map, active-LOW, megaAVR safe-startup, per-channel min-off surviving resets,
      overcurrent latch-off rescaled per load, auto-zero sanity, NUM_CHANNELS
      bounds, watchdog + non-blocking millis(), WiFiNINA telemetry, per-load
      control constants from `loads/*.json`). Build AFTER fridge + replacement
      freezer are characterized (constants come from those JSONs).

---

## P0 UPDATE — ESP32 sketch located, conversion question sharpened

ESP32 sketch confirmed: `ESP_WROOM_32_096_Adafruit_MAX31865_x2.ino` (2x MAX31865,
PT1000, RREF 4300, RNOMINAL 1000, SSD1306 display). Committed to repo under
`firmware/` when convenient (currently only in uploads).

Serial stream per ~1s cycle prints ALL of: `RTD{1,2} value`, `Ratio{1,2}`,
`Resistance{1,2} =`, `Temperature{1,2} =` (degF), plus `Fault ...` lines.
=> Both witnesses already on the wire. dual_logger grabs only Resistance and
reconverts; the ESP32's own degF (sketch line ~69) is unlogged but available.
Adding an ESP32-degF column later is trivial (data already flows).

ESP32 conversion path: `thermo.temperature(RNOMINAL, RREF)` (Adafruit lib) then
`*1.8+32` in-sketch (lines 62-66). Display shows degF (lines 75-76).

CRITICAL correction to the earlier cross-check plan:
- Do NOT assume Adafruit's `temperature()` handles sub-zero correctly. OLDER
  library versions use the SAME single positive-branch CVD quadratic dual_logger
  uses; only newer versions add sub-zero linearization.
- Therefore ESP32-degF and dual_logger-degF may AGREE on the cold side and BOTH
  be WRONG vs a reference. Agreement != correct.
- Cross-check MUST be THREE-WAY: ESP32 degF vs dual_logger degF vs an INDEPENDENT
  PT1000 reference (standard resistance->temp table, or correct 4-term sub-zero
  CVD computed fresh). Only that distinguishes "agree and right" from "agree and
  both wrong (same bug)."
- Check the installed Adafruit_MAX31865 version too (which branch its
  temperature() uses) as corroboration.

---

## P2+ — Inverter-fridge rotation architecture (NEW, from LTCS20020 findings)

Emerged from characterizing the LG LTCS20020 (linear BLDC inverter). Depends on
tomorrow's data: DOES the compressor ever fully shut off, or modulate continuously?

### CONTROL ARCHITECTURE — demand-aware dispatch ["New Thinking", Ron, 2026-07-23]
Supersedes the blind round-robin mental model. Records a significant design shift.

OLD (blind offering): the only way to learn whether a load "wants" power was to OFFER it
(close its relay) and watch the current. Offering is EXPENSIVE -- you tie up the inverter
on a load that may not need it, and a "refusal" (load already satisfied) is a wasted slot.
Especially costly for the fridge and furnace (each offer must be held long enough to see
if it draws sustained current).

NEW (demand-aware): MONITOR ALL TEMPERATURES CONTINUOUSLY -- fridge fresh-food, fridge
freezer, chest freezer, (deployment) freezer, HOUSE, and outdoor -- so demand is KNOWN,
not probed. Offer power to a load ONLY when its temperature says it needs it:
- Knowing freezer temp -> only offer when it's above its cut-in -> far fewer refusals.
- Knowing house temp -> only offer the furnace when the house actually needs heat.
This converts the scheduler from blind polling into DEMAND-AWARE DISPATCH: no wasted
offers, no probing loads that don't need power.

CONSEQUENCES:
1. Temperature telemetry is promoted from "nice enhancement" to the SPINE of the control
   loop. This makes the ESP32->Arduino temp push (TEMP-TO-CONTROLLER LINK, below) central,
   not optional -- the controller must know temps while a load's relay is OPEN.
2. ABORT-ON-Tmax safety law (same requirement, safety side): when power is cut from the
   fridge for a planned/rotation off-period, watch BOTH compartments and RESTORE power the
   instant EITHER crosses its Tmax; hold power until recovered to setpoint before it's
   eligible to be offered-away again. Tmax on our air RTDs DECIDED: fresh 42 F, freezer
   19 F (docs/interruption_test.md). The SHORTER-coasting compartment governs, and which
   one that is depends on config (ice blocks flip it). Note the air-leads-food offset is
   timescale-dependent (validate with the food-simulant probe) -- do not over-trust "air
   over 40 = food safe" on hours-scale coasts.
3. FAIL-SAFE (critical): abort-on-Tmax depends on LIVE temps, so losing a temp feed
   mid-off-period is a SAFETY event. Rule: telemetry drops -> fail safe -> RESTORE POWER
   (or fall back to a dead-reckoned worst-case warmup and restore conservatively). NEVER
   continue a planned off-period blind. => This raises the stakes on sensor reliability:
   the breadboard ESP32 (intermittent, ~3-8% faults) must be rebuilt on soldered protoboard
   (P3) before demand-aware control can be TRUSTED for safety; until then dead-reckon warmup
   stays the PRIMARY safety basis, telemetry an enhancement (see SAFETY SEQUENCING NOTE).
The interruption/coast experiments (docs/interruption_test.md) characterize the inputs this
architecture needs: the Tmax margins, per-compartment coast times, and warmup slopes for
dead-reckoning.

**RESOLVED [2026-07-20]: it CLEANLY SHUTS OFF — continuous-modulation scenario
ruled out.** The 2026-07-19/20 run showed hard cycling with clean off-windows:
after an initial ~6 h continuous pulldown, it ran ON ~30 min / OFF ~20, 20, 10 min
(3 observed shutoffs) before the overcurrent event. So this compressor does NOT
modulate continuously; rotation has real 10-20 min idle gaps to fill and does NOT
have to FORCE interruptions on it. => The "binding-constraint / must-force-off"
branch below is OFF THE TABLE for this load; the ordinary duty-cycle budget model
DOES apply. (Still confirm from the actual current trace via characterize.py; the
off-durations above are eyeballed. Duty ~64% provisional — see rotation_budget.md.)

If it modulates continuously (no clean off-windows):
- The fridge has no idle gaps for rotation to fill; rotation must FORCE power
  interruptions on it. Combined with the LG 3-min lockout, this fridge becomes the
  binding constraint the whole schedule bends around (guarantee >=3min off AND a
  recovery on-window each time it's cut; cannot observe it while unpowered).
- => The rotation budget model (sum of duty cycles < 100%) may not apply to this
  load. Model it as: min on-window, max tolerable off-window (from warmup rate),
  mandatory >=3min lockout-avoidance off.

Knowing fridge temp while its relay is OPEN (two approaches, build BOTH):

1. TEMP-TO-CONTROLLER LINK (measured, preferred long-term):
   ESP32 (owns RTDs + WiFi) PUSHES temperature directly TO the Arduino controller
   (WiFiNINA), device-to-device. The Ubuntu laptop leaves the control path entirely
   and stays a pure logger. This is the production-appropriate topology: two embedded
   devices form the control loop; no laptop dependency.
   - Gives the Arduino fridge temp even while the fridge relay is OPEN (the blind
     window during freezer/furnace service).
   - Likely protocol (decide in Claude Code): ESP32 pushes a short UDP packet ~1 Hz
     (t1, t2, ms, fault). Arduino rule: no fresh packet in N sec -> fall back to
     dead-reckoning. Stateless, self-healing. HTTP/MQTT are heavier alternatives.
   - SAFETY: Arduino treats incoming temp as ENHANCEMENT over dead-reckoning (#2),
     never as the sole basis. Fail-safe to the model, not fail-blind. Don't lean on
     it hard until the ESP32 is rebuilt off breadboard (P3).

2. DEAD-RECKON WARMUP (fallback / safer primary for now): estimate fridge temp from
   last-known value + measured constant warmup slope while unpowered. Build anyway --
   RTD rig faults ~1-2/thousands of samples.

SAFETY SEQUENCING NOTE: promoting the ESP32 into the CONTROL loop elevates it from a
losable passive logger feed to a safety-critical telemetry source. Current ESP32 is
BREADBOARDED + intermittent (needs soldered-protoboard rebuild, see P3). Until that
rebuild, dead-reckon warmup should be the PRIMARY safety basis and telemetry only an
enhancement -- the inverse of the intuitive ordering. Do NOT make rotation safety
depend on the breadboarded ESP32.

### DEFROST-OPPORTUNITY SCHEDULING (design direction, NOT built) [2026-07-21]
Source: a Gemini brainstorm (daytime-rotation / nighttime-defrost-window framing),
refined against OUR measured data + Ron's priorities. Captured now so it isn't lost;
implement at the production-firmware phase, after the fresh capture gives real defrost
duration + cadence + per-compartment warmup.

MEASURED [2026-07-21, live off the fresh-capture power-up -- full detail in
loads/kitchen_fridge.json "defrost"]:
- Defrost DURATION ~28-30 min => the MIN UNINTERRUPTED WINDOW the scheduler must grant the
  fridge once a defrost is detected. Do not cut it inside this window.
- Defrost LOAD: flat ~1.8 A / ~198 W (heater; compressor OFF -- confirmed by observation +
  drain-pan melt water), with PERIODIC BRIEF DIPS to ~1 A every ~10 min (board sampling the
  coil temp). => the detector MUST DEBOUNCE: require current low for several seconds before
  declaring "defrost over", or it false-ends on every measurement dip.
- Sensor-based ADAPTIVE defrost (thermistor-terminated) confirmed -- a smart board deciding
  when to stop, not a fixed bimetal.
- POST-DEFROST: ~7 min dwell (no compressor), then restart at ~1.0-1.4 A (inverter high-speed
  pulldown of the warm box) tapering toward ~0.8 A. Budget the fridge block as one
  indivisible unit: ~30 min defrost + ~7 min dwell + a pulldown-recovery window.
- PROTECTED WINDOW = DEFROST + RECOVERY ~= 2.5 h [Ron's strategy point, measured 2026-07-22].
  After defrost the box is at its WARMEST (freezer +17..+22 F) and un-recovered; the clean
  2nd defrost then ran the compressor CONTINUOUSLY ~2 h to pull back to cut-out. Cutting the
  fridge anywhere in defrost-or-recovery = warming from the worst point + food-safety risk.
  RULE: once a defrost is detected, protect the fridge through defrost AND the ~2 h recovery
  before it is eligible to be cut for rotation. (This EXTENDS the "min uninterrupted window":
  it is not ~30 min but ~2.5 h when a defrost is in play.)
- DEFROST TRIGGER (manual-confirmed): compressor RUN-HOURS (7-50 h, adaptive by door-open
  time; 4 h after a true power restore). => rotation, by interrupting the fridge, STRETCHES
  the calendar interval between defrosts (run-hours accrue slower). And door activity shortens
  it (daytime defrosts sooner than undisturbed nights).
- OPEN (the big one): defrost fired IMMEDIATELY on this power-up (vs the shakedown's 6 h
  pulldown-first). If defrost is POWER-ON-triggered, EVERY rotation re-power could defrost and
  dominate the whole schedule. Unresolved -- watch for a 2nd defrost this run, or test by
  cycling power. Single most important thing to pin down next.

Core reframing (corrects the brainstorm): defrost is an EVENT TO ALLOW, not a window
to schedule or a state to force.
- Defrost triggers on 7-50 accumulated COMPRESSOR run-hours -- NOT nightly, NOT
  wall-clock. Interrupting the fridge doesn't prevent it; run-hours just accrue
  slower and it fires later. So you never "force" it. You DETECT it and PROTECT it.
- DETECT: the defrost signature is now characterized -- a flat ~1.9 A / 198 W draw
  (compressor OFF, resistive heater), distinct from ~0.75 A cycling. When the fridge
  current shows it, hold the fridge relay ON (uninterrupted) until the draw collapses
  to ~0 (heater terminated) -> defrost complete -> resume rotation / exit early. Do
  NOT cut mid-defrost (incomplete melt + the ~3-min lockout).
- ALLOW, not force (Ron): the point of any "fridge window" is to PERMIT a defrost to
  finish if one fires, not to make one happen.

PRIORITY ORDERING (Ron, 2026-07-21) -- the scheduler backbone, highest first:
  1. House warm / pipes safe / occupants comfortable  (furnace)
  2. Freezer safe  (do not let it cross the refreeze/safety line)
  3. Fridge defrost-allowance + fridge safe
  4. Normal duty-cycle balancing
=> Defrost-allowance is PREEMPTABLE: a cold house or an at-risk freezer reclaims the
   fridge's window. NB Michigan outages are coldest OVERNIGHT -- exactly when the
   furnace is needed most -- so a "furnace-off all night to give the fridge a block"
   scheme (the brainstorm's) is REJECTED; house safety outranks defrost.

ENABLING REQUIREMENT (Ron's Appendix): to arbitrate that ordering the controller must
know HOUSE + FREEZER + FRIDGE(both compartments) temps CONTINUOUSLY, including while a
given load's relay is OPEN (the blind-window problem above, now generalized from the
fridge to the freezer, PLUS a new house-temp sensor). Feeds the temp-to-controller
link + dead-reckon fallback already specced above. House temp is a new channel to add.

DAYTIME PRE-CONDITIONING (thermal storage): over-condition freezer/house during the
day to coast through preemption gaps -- BUT size every coast off MEASURED warmup
rates, not appliance-general optimism. Reality check: the chest freezer warms
~0.18 F/min (~2-3 h from -10 F to 15 F), NOT the "8-12 h" the brainstorm assumed;
the fridge freezer compartment coasted ~3.7 F/hr in the overnight event. Replacement
freezer TBD -- re-measure, don't inherit.

OPEN INVESTIGATION: does THIS LG board's adaptive defrost actually use the door
switch (door-open counts) + runtime, and does "no overnight door openings -> defrost
deferred toward the 50 h cap" hold? Unverified assumption; check before relying on it.

---

## P0 (CONFIRMED ROOT CAUSE) — Overnight overcurrent latch, 2026-07-20 00:38:17

SUPERSEDES earlier wrong diagnoses in this doc (do not act on any "Arduino stalled"
or "logger bug" write-up if one exists above -- ground truth below is from the
Arduino's own raw log line + the plotted raw current waveform).

### What happened (confirmed from raw serial log + raw current waveform)
- Sketch: characterize_load.ino, TARGET_CH=3 (Spare) -- CONFIRM this matches the
  fridge's actual physical socket; not yet verified (open item, see below).
- 00:37:57 (t=-20s): current STEPS in one sample from steady ~0.75A to ~2.38A
  (one transitional sample at 0.977A), holds ~2.35-2.38A for ~2s, eases to ~2.25A,
  then SETTLES to a dead-flat ~1.90A (+/-0.01A, very low noise) and holds there.
- The step crosses the sketch's 1.5A threshold and stays above it continuously.
- 00:38:17 (t=0): sketch logs verbatim:
  "# OVERCURRENT: >1.5A for >20s -> relay opened, latched off (likely stalled
  compressor)." Relay opened, fridge lost power. Latch is PERMANENT (no retry) --
  sketch then sat silent on the CUR stream (no more current-data lines) until Ron
  manually restarted it ~07:22 (confirmed: fresh boot banner at that epoch).
- Freezer (t1) warmed slowly and continuously ~7h (~-4F -> +22F, ~4F/hr) while
  unpowered -- consistent, expected, matches an outage-scale warmup measurement.
- Fresh-food (t2) and freezer were BOTH flat/normal in the 60s before the step --
  no thermal sign of trouble; compressor was cooling fine right up to the event.
- Food safety: freezer air never exceeded ~22F over ~7h -- very likely never
  crossed the refreeze-safety threshold (40F / loses ice crystals). Food probably
  fine; user to visually confirm ice crystals present.
- Fridge restarted CLEANLY on wall power this morning, cooling normally -- no
  lingering fault, no LED blink code observed (LED read was moot -- power had
  already been cycled by the relay-open + wall-plug, clearing any state before
  it could be read; see manual's "check before reset" caveat, already missed).

### Why is this current level anomalous (NOT normal inverter modulation)
- Checked: max current ELSEWHERE in the entire run (excluding Ron's own startup
  transients while getting the two data streams running) was ~1.3A. 1.9A NEVER
  recurred anywhere else in the dataset. This is a genuine one-off outlier, not a
  normal operating band for this compressor.
- Timing is backwards for "ramping up to cool harder": both compartments were
  AT TEMPERATURE and flat -- this looked like it was approaching (per the pattern
  of 3 prior ~20min shutoffs in the preceding ~2h) a 4th expected shutoff, not a
  point where healthy cooling demand would justify doubling current.
- EMI-from-fridge-power-cord-near-ESP32-USB-cable hypothesis (Ron's physical
  observation: cord runs near ESP32 cable, not Arduino's) considered and
  DEPRIORITIZED: a clean 20+ second flat DC step is not the signature of induced
  noise/EMI (which produces transients/hash, not a stable held level). The
  current was almost certainly REAL.

### CONFIRMED CAUSE (was Ron's leading hypothesis): DEFROST HEATER ENGAGEMENT
Confirmed 2026-07-20 by the interior nameplate ("Defrosting input: 198 W") closing
the magnitude question; timing was already a tight fit. Detail below.
- Service manual: defrost initiates every 7-50 accumulated COMPRESSOR run-hours.
  TIMING NOTE [added 2026-07-20, from cycling detail]: accumulated compressor
  RUN-time by the event was ~8 h (a ~6 h continuous pulldown at the start + ~2 h
  of on-time during the subsequent cycling), which lands right at the 7 h defrost
  floor -- a much tighter fit than the earlier "~9.5h wall-clock" figure. A first
  defrost-since-power-on coming due right here is strongly consistent with the
  observed timing (the spike hit exactly at an about-to-shut-off moment).
- CURRENT NOTE [added 2026-07-20; CORRECTED same day by nameplate]: originally
  read the flat ~1.9A as inverter-drive current-limiting, because a 52W (254.7 ohm,
  from the service manual) heater is only ~0.45A -- a 4x gap. SUPERSEDED and
  RETIRED: the fridge's INTERIOR STICKER reads "Defrosting input: 198 W" =
  ~1.7A @ 115V, which matches the observed flat ~1.9A directly. So the defrost
  HEATER explains the current after all -- the manual's 52W/254.7 ohm figure was
  the wrong part or wrong value; the nameplate wins. The ~2.4A entry step is a
  SEQUENCED HANDOFF (per the manual's COMP/heater/fan switching order): a few-second
  compressor+heater OVERLAP as the inverter compressor de-energizes while the heater
  is already on, settling to heater-alone (~1.9A). Confirmed reproducible across two
  defrosts (07-20 comp 0.73A -> 2.38A; 08-08 comp 0.99A -> 2.56A) and the peak fits a
  VECTOR sum of the lagging compressor (PF ~0.55) + resistive heater, NOT scalar
  addition -- full profile in loads/kitchen_fridge.json defrost.entry_transient. The
  flat 1.9A settle is just a resistive heater on steady voltage (earlier over-read). NET: defrost-heater engagement now fits BOTH timing (~8h
  run-hrs ~ the 7h floor) AND magnitude (198W nameplate). This is now the confirmed
  explanation; the inverter-drive-fault hypothesis is dropped.
- Defrost heater = 254.7 ohm +/-5% -> ~52W @ 115V -> ~0.45A alone. Does not by
  itself reach 1.9A, but defrost ENTRY is a scheduled control-logic transition
  (per 8-1-3 sequential-operation-of-electric-parts): compressor/fan/heater states
  change together. A transient combined draw (compressor not yet fully
  disengaged + heater + fan reconfig) at a scheduled control event fits the
  timing (right at an expected-shutoff point) far better than a benign inverter
  ramp-up. THIS IS THE LEADING EXPLANATION but NOT CONFIRMED.
- Alternative not ruled out: a genuine partial mechanical labor/stall-like event
  that self-cleared (compressor restarted cleanly afterward with no lingering
  issue, which argues against a hard/persistent stall).
- Open item: correlate against the manual's defrost-entry conditions and, if a
  next capture shows a similar current signature at ~7-50h compressor-run-hour
  boundaries, that would confirm the defrost hypothesis.

### FIXES NEEDED (all confirmed-necessary regardless of which hypothesis is right)
- [x] RESCALE overcurrent_trip_a for this load. DONE [2026-07-21]: set to 3.5 A in
      characterize_load.ino, anchored to the NAMEPLATE whole-unit max (115 V / 2.7 A)
      -- the unit never legitimately draws more than 2.7 A in any mode incl. defrost
      (observed ~2.4 A peak sits under it), so 3.5 A is ~30% over the rated ceiling:
      no false-trip on rated-normal operation, still catches a genuine hard stall
      (much higher). 20 s debounce ignores brief peaks. (Supersedes the earlier
      "~3 A / ~0.45 A heater" guess -- the 2.7 A nameplate is the clean basis.) Do
      NOT reuse the dorm-fridge/chest-freezer 1.5 A value. Recorded in
      loads/kitchen_fridge.json control_constants.
- [x] FIX THE LATCH-AND-HALT-FOREVER BEHAVIOR. DONE [2026-07-20]: characterize_load.ino
      now auto-retries after the 3-min compressor min-off; after MAX_TRIPS it latches
      but prints a loud repeating alarm instead of going silent. (Production firmware
      still wants telemetry/alarm too.) Even a CORRECT trip had left the
      fridge dead and silent for 7 hours with no retry and no alarm -- itself a
      hazard independent of whether the trip was a false positive. Production
      firmware needs auto-retry-after-cooldown and/or an alarm/telemetry signal,
      not a silent permanent latch that only a human noticing the food warming
      will catch.
- [ ] CONFIRM CHANNEL TARGETING: sketch banner says TARGET_CH=3 (Spare); confirm
      this is actually the fridge's physical socket (fridge is on the freezer's
      old socket from the prior characterization run) -- not yet verified.
- [ ] IF the defrost hypothesis is right, the control logic needs to EXPECT and
      exclude the defrost-heater load from the compressor's overcurrent budget,
      or use a longer/higher threshold specifically during defrost windows
      (defrost timing is knowable: accumulated compressor run-hours 7-50).
- [ ] Re-verify PCB fault LED code was NOT captured this event (power was already
      cycled before it was read) -- for a FUTURE event, read the LED BEFORE any
      power-cycle per the manual's explicit instruction.

### CAPTURE FILE VALIDITY
kitchen_fridge_run.csv is valid current data ~15:00 (prior day) through 00:38:17.
After 00:38:17, current column is FROZEN at the last real value (1.896A) --
logger sample-and-holds a stale value with no staleness guard (separate, still-
valid logger fix noted elsewhere in this doc). Temps remain valid/real throughout
(separate device, unaffected). Raw current waveform for the event itself is
preserved in analysis outputs (overcurrent_event.png) generated 2026-07-20.

### CURRENT-CHANNEL SERIAL CORRUPTION -> false 0.000 A [found 2026-08-01]
Occasional CUR serial lines arrive GARBLED on the USB link. The Arduino's computed
value is fine -- corruption is IN TRANSIT (t_ms usually survives intact while the
amps field is trashed; isolated single lines). The old parser
`^\s*(\d+),([\d.]+),?(\w*)` matched a PREFIX, so a garbled line like
`38906058,0)<junk>` yielded amps="0" -> a FALSE 0.000 A. Confirmed from the .raw:
adjacent lines are clean ~0.96 A; the corrupt one carries high/garbage bytes.
Clusters as current levels off near setpoint -- HYPOTHESIS: inverter-compressor
low-speed PWM noise coupling into that USB lead (the EMI path already flagged in the
overcurrent write-up). `current_stale` does NOT catch these -- a corrupted line is
fresh, just wrong.
- [x] Parser hardened [2026-08-01, dual_logger.py]: end-anchored, decimal-required
      `^\s*(\d+),(\d+\.\d+),(\w*)\s*$`. Corrupted lines are dropped (merge holds the
      prior value, a ~250 ms gap, well under current_stale). Real 0.000 still logs.
      NO header change. Deploys with the setting-5 restart (same as the P1 batch).
- [ ] Reduce the corruption at the source. Test ONE change at a time (change nothing
      else; measure the corrupt-CUR-line RATE from the .raw before vs after -- the raw
      is preserved even though the parser now drops the bad lines):
      a. LOWER baud (e.g. 115200 -> 19200 or 9600). Payload is ~80 B/s, so enormous
         headroom / no throughput cost; slower bits = more noise margin. Requires the
         Arduino sketch + --current-baud changed together.
      b. Physical: ferrite on the current USB lead + shield / re-route it away from the
         compressor cord.
      Isolating a vs b tells us whether it's a timing-margin problem or a coupling
      problem.
- [ ] Robust long-term: add a checksum to the Arduino CUR line so ANY corruption is
      rejectable -- the regex only catches the leading-"0"/garbage class, not a
      corrupted-but-structurally-valid value.

---

## Reminder — rename tools/free_cycle_scan.py (coined+wrong name)

- [ ] Rename `tools/free_cycle_scan.py` (and its output labels "cut-out"/"cut-in").
      "free-cycle" is a coined term Ron banned; use concrete hardware-state words
      (relay open/closed, compressor running, defroster running). Also RELABEL what
      it reports: it finds "compressor-off while relay closed" stretches but does NOT
      separate the fridge's fixed ~7-min post-power-on startup delay from a genuine
      compressor stop, so it over-counts. For the fridge's OWN compressor-stop
      behavior use `tools/fridge_compressor_stops.py` instead. Decide a name with Ron
      before renaming (his consent required for terms).
