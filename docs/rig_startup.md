# Rig startup & end-to-end verification (dry-run-first)

Purpose: bring the capture rig up **without the usual "is it even collecting?" stress**,
by proving the whole telemetry chain on a **safe dummy load** before committing to the
fridge. Reusable for every load (fridge, freezer, furnace).

## GOLDEN RULE
**Do NOT unplug the fridge from the wall until the Mac plot shows the dummy load's
current AND both temperatures updating live.** If the chain isn't proven on the dummy,
it won't magically work on the fridge — you'll just have put the food at risk to find out.

## The data path (what you're verifying, hop by hop)
```
Arduino (current, /dev/ttyACM0) ┐
                                ├─ USB → Ubuntu: dual_logger.py → merged CSV (+ .raw)
ESP32   (temps,  /dev/ttyUSB0)  ┘                                   │
                                                    ssh tail -f  ◄───┘  (tools/watch_run.sh)
                                                        │
                                              Mac: tools/live_chart.py → plot window
```
Any hop can be the culprit. The phases below light them up in order.

> Ports now AUTO-DETECT by USB vendor id (Arduino for current, ESP32 bridge for temps),
> so ttyACM0<->1 / ttyUSB0<->1 renumbering no longer matters. `--list-ports` shows what's
> attached; pass `--current-port`/`--temp-port` only to override.
>
> CONFIRM-THESE (fill in once, they rarely change):
> - Exact command + working dir you launch `dual_logger.py` with on Ubuntu
> - Where the Ubuntu CSV lives (watch_run.sh expects `~/Documents/RetirementWork/Engineer/inverter/<name>.csv`)
> - Mac→Ubuntu file sync method (to push the fixed sketch + dual_logger.py first)

---

## PHASE 0 — Pre-flight (nothing running, fridge still on the wall)

On **Ubuntu**:
1. Both devices present: `python3 dual_logger.py --list-ports` → expect to see the Arduino
   (vid `2341`) and the ESP32's USB-UART bridge (vid `10c4`/`1a86`/`0403`). Auto-detect will
   pick them regardless of the ttyACM/ttyUSB number. If a device is missing here, fix that
   first — reseat the USB cable. (An *extra* USB-serial gadget makes auto-detect report
   AMBIGUOUS; unplug it or pass `--*-port` explicitly.)
2. No port hog: close any Arduino IDE **Serial Monitor**, and check no old logger is holding
   the port: `pgrep -f dual_logger` (should print nothing).
3. Fixed files are on this box: the **3.5 A** `characterize_load.ino` and the **fixed**
   `dual_logger.py` (P0 + no-clobber). Sync from the Mac repo and, if the sketch changed,
   re-upload it to the Arduino.

On the **Mac**:
4. SSH reaches the box *before* you depend on it: `ssh ubuntu true && echo SSH-OK`.
   (watch_run.sh uses the `ubuntu` ssh alias over mDNS — if this hangs, the plot never will.)

Green means: OS layer + link are sound. Proceed.

---

## PHASE 1 — Dry run with a DUMMY load (fridge STILL on the wall)

Use a dummy load that draws **clearly above the ~0.1 A noise floor but well under the
3.5 A trip** — roughly **0.3–1.5 A**. Good picks: a 60–100 W incandescent bulb (~0.5–0.9 A),
a small desk fan, a soldering iron. Avoid: an LED night-light (too small — reads as noise,
proves nothing) and a hair-dryer/space-heater (trips the 3.5 A cutoff at 20 s).

1. Plug the **dummy load** into the switched socket (Ch4 / "Spare" — the fridge's socket).
   **Not the fridge.**
2. **Ubuntu:** start the logger to a THROWAWAY file (unique name — the no-clobber guard
   refuses an existing file):
   ```
   python3 dual_logger.py \
       --out "$HOME/Documents/RetirementWork/Engineer/inverter/dryrun_$(date +%H%M).csv"
   ```
   Watch its console: it should print `# auto-detect current: /dev/ttyACMx …` and
   `# auto-detect temp: /dev/ttyUSBx …` (both devices found), then `# current: …`/`# temp: …`.
   An `auto-detect: no … found` / `AMBIGUOUS`, or a `refusing to write … already exists`
   line, is a stop-and-fix.
3. **Reset the Arduino** (so the run starts clean). EXPECTED, do not panic:
   - For the first **~3 minutes** the sketch holds all relays OPEN (the min-off hold-off)
     and prints `  2:59 remaining...` etc. During this window **temps flow but current is
     blank** — this is the hold-off, NOT a failure. (This is the exact thing that has
     stressed you before.)
   - Then it auto-zeros: watch for each channel `offset = ~2.5 V`. Any `OUT OF RANGE` /
     `ABORT` = a sensor is unpowered/miswired — fix before going further.
   - Then it closes the target relay → the **dummy lamp lights** → current appears.
4. Sanity-check the streams at the source (Ubuntu CSV): tail the throwaway file and confirm
   `current_a` is a sensible non-zero (the lamp) and the two temp columns are populated.
5. Confirm which probe is which: **warm one RTD probe with your hand** → that temperature
   column should rise within seconds. Do both. (This also nails probe→column mapping you'll
   need for the fridge's two compartments.)
6. **Mac:** point the chart at the throwaway file and start it:
   - set `REMOTE_CSV` in `tools/watch_run.sh` to the dry-run filename, then
   - `./tools/watch_run.sh 1`  (1-hour window is plenty for a dry run)

### SUCCESS GATE (all three, live, on the Mac plot):
- [ ] `current_a` line shows the dummy load (non-zero, drops to ~0 if you pull the lamp)
- [ ] `t1` temperature line present and responds to the hand-warm test
- [ ] `t2` temperature line present and responds to the hand-warm test

If any is missing → see Troubleshooting; **do not proceed to Phase 2.**
When green: Ctrl-C the logger and the chart. (Optionally delete the `dryrun_*.csv`/`.raw`.)

---

## PHASE 2 — Real capture (only after Phase 1 is green)

Key safety rule: **the switched socket is live ONLY after the sketch closes the relay
(~3 min after a reset). Do all plugging while it is DEAD.** If you need more time, just
reset the Arduino again — it reopens the relay and restarts the 3-min hold-off.

1. **Reset the Arduino** → relays open, 3-min hold-off begins (socket now DEAD).
2. While DEAD: unplug the dummy → **unplug the fridge from the wall** → plug the fridge into
   the switched socket. (If the fridge just ran, the wait is fine — its own controller
   enforces the compressor lockout / head-pressure equalization; our hold-off only adds margin.)
3. **Ubuntu:** start a FRESH logger to the real capture file (must NOT already exist):
   ```
   python3 dual_logger.py \
       --out "$HOME/Documents/RetirementWork/Engineer/inverter/kitchen_fridge_run2.csv"
   ```
   (`kitchen_fridge_run.csv` is the shakedown and is protected by no-clobber — hence `run2`.)
4. **Mac:** set `REMOTE_CSV` → `kitchen_fridge_run2.csv` in `tools/watch_run.sh`, then
   `./tools/watch_run.sh 8`.
5. The sketch finishes hold-off → auto-zeros → closes relay → **fridge energizes** (its
   board then applies its own start delay). Re-confirm on the plot: current + both temps live.
6. Let the probes equilibrate ~10–20 min before trusting temps, then let it run for many
   hours / multiple cycles (skip the pulldown when reading duty).

Record at the rig: probe→compartment→column mapping, ambient temp, and which physical
socket/channel the fridge is on.

---

## Troubleshooting (the frequent failures)

| Symptom | Likely cause | Fix |
|---|---|---|
| `auto-detect: no … found` | device unplugged / cable | reseat USB; `--list-ports` to confirm it appears |
| `auto-detect: AMBIGUOUS` | an extra USB-serial device attached | unplug it, or pass `--current-port`/`--temp-port` explicitly |
| `port open failed` / busy | IDE Serial Monitor or an old logger holds it | close Serial Monitor; `pgrep -f dual_logger` |
| `refusing to write … already exists` | no-clobber guard (CSV name taken) | pick a fresh `--out` name (and update `REMOTE_CSV` to match) |
| Current blank for ~3 min, temps flowing | the 180 s startup hold-off | EXPECTED — wait it out (or watch the countdown lines) |
| `offset OUT OF RANGE` / `ABORT` | current sensor unpowered/miswired | fix wiring, reset; sensor 5 V + ground must be present |
| Temps never start streaming | ESP32 breadboard rig often needs a USB re-cycle to begin | unplug/replug the ESP32 USB **before/at** logger start (see ESP32 warning below) |
| Temps flatline mid-run after an ESP32 glitch | ESP32 dropped / re-enumerated | logger now RE-RESOLVES on reconnect and self-heals (watch for `# temp: reconnected on …`, up to a few s). If it stays flat, the device is truly gone — reseat USB |
| `Fault` spam | ESP32 breadboard flaky (P3) | reseat the MAX31865 / RTD leads; a few faults/thousands is normal |
| Plot window empty on the Mac | SSH/mDNS down, or `REMOTE_CSV` wrong | `ssh ubuntu true`; confirm `REMOTE_CSV` matches the actual `--out` path |
| Plot legend says `t1_freezer_f` after a P1 rename | live_chart labels are hardcoded (it plots by column index, not name) | cosmetic only — data is correct; update the label strings when convenient |

## Firmware upload settings (Arduino IDE on Ubuntu) — for `characterize_load.ino`
- **Board:** Tools → Board → **Arduino megaAVR Boards → Arduino Uno WiFi Rev2**.
  If that board isn't listed, install "Arduino megaAVR Boards" via Boards Manager —
  without the core, `A1`..`A4` show as *"not declared in scope"* (they're board-defined macros).
- **Registers emulation:** Tools → **None (ATMEGA4809)**. Silences the ATMEGA328-emulation
  `#warning`, and makes `analogRead` a bit faster (a few more samples per RMS window). Safe:
  the sketch uses only the standard Arduino API, no legacy-register access.
- **Port:** Tools → Port → the `ttyACM…` (the Arduino).
- **CLI equivalent:** `arduino-cli compile/upload --fqbn arduino:megaavr:uno2018:mode=off`

## ESP32 (temps) — known breadboard flakiness
The temp rig is breadboarded and intermittent (P3: rebuild on soldered protoboard).
- It frequently needs a **USB re-cycle to start streaming** — do that *before/at* logger
  start (it must be present when the logger resolves the port, or auto-detect errors).
- If the ESP32 re-cycles **mid-capture** and Linux hands it a *different* `ttyUSB` number,
  the logger now **re-resolves and reconnects automatically** (prints `# temp: reconnected
  on /dev/ttyUSBx`), so temps self-heal within a few seconds. The current column is
  unaffected either way (separate device). Only if the ESP32 is truly gone (nothing to
  re-resolve) do temps stay flat — then reseat the USB.

## Notes
- `live_chart.py` reads by column **index** (2 = current, 4 = t1, 5 = t2) and skips the
  header by name — so a P1 column rename does NOT break plotting, only the legend text.
- A dummy-load dry run is cheap insurance every time; make it a habit for the furnace and
  freezer captures too.
