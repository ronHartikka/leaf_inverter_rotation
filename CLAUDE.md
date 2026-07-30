# Leaf Inverter Rotation Controller

Arduino/ESP32 hardware project: an automatic load-rotation controller that shares one
Nissan Leaf 12 V + Renogy 1000 W inverter source among household appliances (chest
freezer, kitchen fridge, gas furnace) during outages — one load at a time. The DC-DC
ceiling is ~1.0–1.2 kW, so simultaneous compressor starts are impossible. This
automates a rotation that has been done manually for years.

## Guardrails — loaded every session

@docs/lessons.md

Those are hard-won and evidence-backed, several of them purchased with hours of
debugging or a night of unpowered food. Implement them; do not relitigate them.

## Where things live

- `docs/todo.md` — the work queue, prioritized P0 → production firmware. Read the
  WHOLE file before proposing a plan: new items are appended at the bottom, so the
  freshest P0 is not necessarily the first one listed.
- `docs/hardware.md` — authoritative pin map, active-LOW relay logic, power
  architecture, rig facts.
- `docs/rotation_budget.md` — the make-or-break duty-cycle question and its status.
- `docs/rig_startup.md`, `docs/interruption_test*.md` — at-the-rig procedures.
- `loads/*.json` — per-load characterization. Control constants come from these.
- `firmware/shared/` — canonical constants, safe-startup and current-sense helpers.

## Production firmware non-negotiables

Design invariants, not future features. They apply whenever
`firmware/rotation_production/` is touched:

- **Watchdog ENABLED.** Exactly one `wdt_reset()` at the top of `loop()` — never
  inside a wait loop, never from an ISR. Petting from anywhere that still runs while
  the main logic is wedged defeats the mechanism entirely.
- **Non-blocking `millis()` state machine; no blocking waits.** Not a style
  preference: it is what makes a single top-of-loop pet a valid proof of liveness.
- **Safe startup:** `pinMode(OUTPUT)` then immediate `digitalWrite(HIGH)`, per relay,
  before anything else in `setup()`.
- **Per-channel minimum-off survives resets** (~180 s PTC cooldown).
- **Control constants scale off MEASURED running current**, per load, from
  `loads/*.json` — never off nameplate.
- Report watchdog reset count in telemetry (the chip latches the reset cause).

## Conventions

- Underscore naming for all files and folders.
- Characterization JSON carries `identity`, `channel_binding`, `electrical`,
  `control_constants`, `thermal`, `duty_cycle`, `provenance`; every value has explicit
  `confidence` and `source` fields.
- 0-indexed array index vs 1-indexed physical channel label is a recurring snare —
  state both when it matters.
- Header/column changes are atomic commits across all consumers, never piecemeal.
- `tools/dual_logger.py` in the repo is the reference copy; the Ubuntu box
  (`ron-Latitude-E6440.local`) runs its own and won't pick up edits until restarted.

## Working style

- **One step at a time.** Give one step, wait for confirmation. Do not stack six steps.
- **Follow the data, not the hypothesis.** Pull the raw log before asserting a
  diagnosis. Several confident narratives have been wrong and were overturned by
  reading the actual file.
- **Do not assert the existence or behavior of hardware, parts, or libraries without
  checking first.**
- Mark confidence honestly; prefer measured values to assumed ones.
- Append to notes files with `cat >>`, never `cat >`.
- Record hardware quirks as code comments where they apply, not only in docs.
