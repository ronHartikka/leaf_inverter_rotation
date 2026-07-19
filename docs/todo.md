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
