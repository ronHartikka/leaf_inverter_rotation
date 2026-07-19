# LEAF + Inverter — Load-Rotation Controller

Automatic load-rotation controller for managing home appliances during power
outages. Power source: Nissan Leaf 12V → Renogy 1000W inverter. The Leaf's DC-DC
converter ceils ~1.0–1.2 kW, so the system enforces a **one-load-at-a-time** policy:
an Arduino rotates inverter power among major loads (freezer, fridge, furnace) on
timed / current-aware slots so only one compressor ever draws a start surge at a
time. Years of manual one-at-a-time operation already worked; this automates it.

## Current phase
Characterizing real loads to get the numbers that decide whether one-at-a-time
rotation of 3 loads is viable (see `docs/rotation_budget.md`).
- Dorm fridge (test piece / method shakedown) — **done**, ~50% duty.
- Chest freezer (real load) — **done**, ~70% duty, **flagged for replacement**.
- **Kitchen fridge — NEXT** (dual-compartment: two thermal blocks, two RTD channels).
- Furnace — later.

## Repo layout
```
README.md                     this file — the live state doc / front page
docs/
  hardware.md                 pin map, active-LOW, power arch, RTD rig
  lessons.md                  the 10 hard-won lessons (megaAVR trap, PTC stall, etc.)
  rotation_budget.md          duty tally + the "does 3×duty < 100%?" question
  todo.md                     prioritized backlog — the work queue (START HERE)
  claude_code_kickoff.md      paste-in prompt for the first Claude Code session
loads/
  schema.json                 reusable per-load template (copy -> <load>.json)
  dorm_fridge.json            done (also the original worked example)
  chest_freezer.json          done — flagged for replacement
  kitchen_fridge.json         NEXT — dual-compartment placeholder
  furnace.json                later — placeholder
firmware/
  characterize_load/          single-load current profiler
  hw_verify/                  hardware verification sketch
  trial_rotation/             fixed-slot rotation trial firmware
  rotation_production/        the FINAL firmware (build after loads are characterized)
  shared/                     pins.h / safe_startup.h / current_sense.h — ONE home
tools/
  dual_logger.py              one-machine one-clock current+temp logger
data/
  .gitignore                  raw capture CSVs are big + local (git-ignored)
analysis/
  characterize.py             CSV -> duty/current/thermal numbers for the JSON
```

## Workflow for the next load (kitchen fridge)
1. Wire the fridge to a channel; note socket/relay/sense pins.
2. Capture several hours undisturbed through multiple cycles:
   `python3 tools/dual_logger.py --current-port /dev/ttyACM0 --temp-port /dev/ttyUSB0 --out data/kitchen_fridge_run.csv`
   Assign one RTD to fresh-food air, one to freezer air; record which is which.
3. Crunch it: `python3 analysis/characterize.py data/kitchen_fridge_run.csv`
   (Run twice, once per `--temp-col`, for the two compartments.)
4. Copy `loads/schema.json` → fill `loads/kitchen_fridge.json`. Dual-compartment:
   duplicate the thermal `compartments` block into fresh_food + freezer.
5. Update the table in `docs/rotation_budget.md`.

## Placeholders to replace (not attached when this repo was scaffolded)
- `loads/dorm_fridge.json` — the real completed JSON.
- `firmware/*/*.ino` — the real sketches (then swap inline boilerplate for the
  `shared/` includes).
- `tools/dual_logger.py` — the real logger.

## Firmware guardrails (all in docs/lessons.md, enforced in shared/)
pinMode-first safe startup · per-channel min-off surviving resets · overcurrent
latch-off (rescale per load) · auto-zero sanity · NUM_CHANNELS bounds · watchdog +
non-blocking millis(). Scale control constants off MEASURED running current, never
nameplate.

## Style
Deep, careful debugging partner; establish authoritative facts before moving on;
document hardware quirks in code comments; non-blocking millis() architecture;
prefer measured data over assumed; mark confidence honestly. The 0-indexed array vs
1-indexed physical channel label is a recurring snare — state both when it matters.
