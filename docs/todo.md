# TODO / open work — Load-Rotation Controller

Durable backlog so nothing falls off the table across chats and Claude Code
sessions. Priority order matches how the work should flow. Check items off in
commits as they're done.

---

## P0 — Temperature conversion correctness (DO NOT LOSE THIS)

Discovered while reviewing `tools/dual_logger.py` for the fridge run. Real bug +
an architecture decision. None of it changes the freezer replace-or-not decision
(duty cycle unaffected), but it matters for clean archival thermal data and for
the fridge's freezer compartment.

### The bug
`dual_logger.py` `res_to_c()` solves ONLY the T >= 0 degC branch of
Callendar-Van Dusen. Below 0 degC, PT1000 needs the sub-zero (4th-order) formula.
So all sub-freezing temps are systematically biased (a few tenths of a degree C at
~-20 degC). Affects:
- the chest freezer thermal numbers already in `loads/chest_freezer.json`
  (freezer sits ~-20 degC / -5..0 F), and
- the fridge's FREEZER compartment on the upcoming run (~-18 degC).
The fridge's fresh-food compartment (~2-4 degC) is in the valid branch, fine.

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
- [ ] Fix `res_to_c()`: add the sub-zero CVD branch (T < 0 degC). Self-contained,
      NO header change, NO consumer edits (values change, column names don't).
- [ ] Add a tiny self-test: check a few known resistance->temp points against a
      PT1000 reference table (both above and below 0 degC).
- [ ] Cross-check script: for an existing freezer CSV, compare ESP32 degF (if in
      stream) vs dual_logger-corrected degF vs raw resistance. Confirm warm-agree
      and that cold-side now agrees after the fix. VERIFY before trusting.
- [ ] Recompute the chest freezer thermal fields in `loads/chest_freezer.json`
      from stored resistances using the corrected conversion; note the small delta
      + that duty/decision are unchanged. Bump provenance.
- [ ] Confirm whether the ESP32 serial stream carries resistance, degF, or both
      (dual_logger parses `Resistance1=`/`Resistance2=` — where from?). Paste the
      ESP32 sketch print lines to settle this. May want to also log ESP32 degF as
      its own column (SEE P2 — that's a HEADER change, batch it).

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
      (`characterize_load.ino`, `hw_verify.ino`, `trial_rotation.ino`), then swap
      their inline boilerplate for the `firmware/shared/*.h` includes.
- [ ] `requirements.txt` (or freeze) so the venv is reproducible
      (matplotlib 3.11.1 etc. — currently only in the live venv, not recorded).
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

### LEADING HYPOTHESIS (Ron's, not yet confirmed): DEFROST HEATER ENGAGEMENT
- Service manual: defrost initiates every 7-50 accumulated COMPRESSOR run-hours;
  this event was ~9.5h into the run -- plausible window.
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
- [ ] RESCALE overcurrent_trip_a for this load. Measured normal ceiling ~1.3A;
      this event's real (non-fault) component may include ~0.45A heater on top of
      whatever compressor draw remains during the transition. Set trip with real
      margin above legitimate transients -- proposed ~3A -- while still catching
      a genuine hard stall (which the manual implies is much higher). Do NOT
      reuse the dorm-fridge/chest-freezer 1.5A value for this load.
- [ ] FIX THE LATCH-AND-HALT-FOREVER BEHAVIOR. Even a CORRECT trip left the
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
