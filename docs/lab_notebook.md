# Lab notebook — Leaf inverter / fridge experiments

Append-only log of the physical things the data can't record on its own: dial
settings, cold-packs in/out, door-heavy days, defrosts noticed, hardware swaps,
probe moves. One line per event. Add entries with `tools/lab_notebook_app.py`
(text box + button) or by hand — always **append**, newest at the bottom.

Timestamp = when the event happened (local time). Backfilled/approximate entries are
marked `~` or `UNKNOWN`; fill them in if you reconstruct them.

## Entries

- **2026-07-2? ??:??** FFC dial 3 → 5. EXACT DATE UNKNOWN — in effect by 2026-07-26 20:07 (reconstruct if possible).
- **2026-07-26 20:07** Coast-control run begins; params held constant Jul 26–31: Tmin 0/36 °F, Tmax 15/40 °F, max-off 180 min.
- **2026-07-29 07:58** FC (freezer/damper) dial 3 → 1, at FFC = 5. (start of run_auto_0729_0758)
- **2026-07-30 ~00:00** Defrost observed (fridge freezer air spiked ~+27 °F).
- **2026-07-31 18:38** Defrost, during heavy evening door openings; ~7 h recovery (vs ~2.5 h usual).
- **2026-08-01 04:34** Defrost (2nd — cascade after the long recovery run burned through the ~7 h run-hour floor).
- **20??-??-?? ??:??** Cold-packs in freezer: in/out dates UNKNOWN (flag to reconstruct).
