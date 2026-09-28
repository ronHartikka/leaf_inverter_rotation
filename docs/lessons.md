# Hard-won lessons (must carry into firmware)

1. **megaAVR pinMode trap.** On ATmega4809, `digitalWrite` BEFORE `pinMode` does NOT
   pre-set the output latch (unlike classic AVR). Latch powers up 0, so
   `pinMode(OUTPUT)` alone drives LOW = relay closed = all relays energized at boot.
   **Always pinMode first, then immediate digitalWrite HIGH.** (See
   `firmware/shared/safe_startup.h`.) Cost hours.

2. **PTC-start compressors stall on hot re-energize.** A sub-second blip to a running
   PTC-start compressor (e.g. a controller reset that opens then re-closes ~1s later)
   stalls it: ~1.9A locked-rotor, heats to 160–170°F, overload trips. **Enforce a
   per-channel minimum-off (~3 min PTC cooldown) that SURVIVES RESETS** — on any
   startup, hold all relays open before energizing a possibly-recently-run compressor.
   Implemented as a 180s relays-open hold-off.

3. **Overcurrent cutoff works and won't false-trip.** A healthy start (dorm fridge)
   exceeds 1.5A for only ~1.9s, so ">1.5A for >20s → open + latch off" is safe.
   NOTE: the 1.5A threshold suits ~0.7A-class compressors — **rescale per load** off
   measured running current.

4. **Auto-zero sanity.** Reject sensor offsets outside ~2.3–2.7V (catches
   unpowered/miswired sensor). A stale/bad zero silently corrupts all readings.
   (See `firmware/shared/current_sense.h`.)

5. **Loop bounds from ONE constant (NUM_CHANNELS).** Hand-edited `< 4` vs `< 5`
   caused an array overrun. (Canonical in `firmware/shared/pins.h`.)

6. **D1/TX conflict.** Never put a relay on D1 (hardware TX) — serial print and
   uploads chatter it. Fixed by the +1 pin shift.

7. **Watchdog + pull-ups + safe-startup compose.** Watchdog converts hangs→resets,
   pull-ups make the float-during-reset safe, safe-startup lands reset all-open.
   Requires non-blocking millis() (one wdt_reset at top of loop).

8. **Two clocks are painful.** Arduino millis() runs ~0.24% slow (2380 ppm, ceramic
   resonator). Merging two separately-clocked logs needs rate-scaling AND phase
   alignment. Solution: one logger, one machine, one clock — `tools/dual_logger.py`.

9. **Nameplate amps ≠ run current.** The chest freezer's 5.0A nameplate is a
   locked-rotor-inclusive MAX; it runs at ~0.72A. Running current is set by
   compressor CLASS, not box size (dorm fridge ~0.68A, freezer ~0.72A — all ~0.7A).
   **Scale every control constant off MEASURED running current, never nameplate.**

10. **10 Hz / 100 ms-RMS sampling CANNOT resolve inrush.** The start transient is
    sub-100ms and falls between samples / is averaged out. Any "inrush" from
    `dual_logger.py` is method-limited, NOT a true surge peak (freezer showed ~3.5A;
    real instantaneous surge is unmeasured, likely much higher). Use scope + shunt if
    a true surge number is needed for inverter sizing.
    **MEASURED 2026-09-27**, at ~881 SPS with
    `firmware/esp32_ads1115_cycle_stats`: the chest freezer's start is **17.8 A peak /
    11.75 A RMS held ~1.1 s**. The scope advice stands for a true instantaneous number;
    the figure is now bounded rather than unknown. See `loads/chest_freezer.json`.

    **But two specifics above are WRONG, corrected the same day by re-reading the source
    capture — and the correction matters more than the number.**

    - **The transient is NOT sub-100 ms.** It is a ~1 s locked-rotor plateau ending in an
      abrupt PTC dropout. Nothing "falls between samples" on a 100 ms scale.
    - **The rig did NOT miss it.** `latest_chest_freezer_run.csv` holds a maximum of
      **12.128 A**, which agrees with the new instrument's 11.75 A RMS to within 3%. The
      3.5 A that reached `chest_freezer.json` does not reproduce from its own stated
      derivation.

    The real failure mode is different and worth knowing: dual_logger emits rows at
    10/s, but the current VALUE only changes every **1.06 s** — sample-and-hold repeats
    each reading ten times, so the chain's true resolution is ~1 Hz. Across 26 starts it
    caught the surge on **9** and missed it on **17**, and a miss looks exactly like a
    start with no surge at all.

    **So the operative lesson is not "the rig can't see inrush" — it is that a derived
    number must be recomputed from the raw file before it is trusted, and that this
    chain samples starts intermittently enough that any single start proves nothing.**

11. **A long capture on a laptop dies silently when the laptop sleeps — and a gap
    looks exactly like a real cycle boundary.** A 6.9 h freezer capture (2026-09-27)
    developed ten gaps; after the first, **47% of elapsed time was missing** from the
    log, in a repeating pattern of ~46 s recorded and ~16 min absent. Nothing in the
    file announces this: `t_ms` never resets, no error appears, and the rows on either
    side of a gap are valid. Three of five cycles were analysed, and a whole narrative
    about run lengths built, before the gaps were found. **Check for time gaps BEFORE
    analysing any capture** — `t[i] - t[i-1]` greater than a couple of sample intervals
    — and mark which segments are clean. Prevention: `caffeinate -i` while capturing, or
    a dedicated logger that is not someone's laptop (which is why the Ubuntu box exists).
