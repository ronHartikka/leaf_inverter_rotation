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
