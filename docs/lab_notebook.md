# Lab notebook — Leaf inverter / fridge experiments

Append-only log of the physical things the data can't record on its own: dial
settings, cold-packs in/out, door-heavy days, defrosts noticed, hardware swaps,
probe moves. One line per event. Add entries with `tools/lab_notebook_app.py`
(text box + button) or by hand — always **append**, newest at the bottom.

Timestamp = when the event happened (local time). Backfilled/approximate entries are
marked `~` or `UNKNOWN`; fill them in if you reconstruct them.

## Entries

- **2026-07-21 ~13:57** FFC dial 3 → 5 (RECONSTRUCTED, high confidence). Coincides with the start of run_20260721_135703. Evidence: FFC free-cycle band shifted ~5 °F colder across the file boundary — Jul 19–20 run cut out ~39 °F (band 39–42), Jul 22 & 24 cut out ~34 °F (band 34–39); both non-coast, so it's the fridge's own thermostat, and cut-out temp is ambient-independent. Bracketed to the data gap [Jul 20 07:32 – Jul 21 13:59]; exact minute within the gap unknown.
- **2026-07-26 20:07** Coast-control run begins; params held constant Jul 26–31: Tmin 0/36 °F, Tmax 15/40 °F, max-off 180 min.
- **2026-07-29 07:58** FC (freezer/damper) dial 3 → 1, at FFC = 5. (start of run_auto_0729_0758)
- **2026-07-30 ~00:00** Defrost observed (fridge freezer air spiked ~+27 °F).
- **2026-07-31 18:38** Defrost, during heavy evening door openings; ~7 h recovery (vs ~2.5 h usual).
- **2026-08-01 04:34** Defrost (2nd — cascade after the long recovery run burned through the ~7 h run-hour floor).
- **20??-??-?? ??:??** Cold-packs in freezer: in/out dates UNKNOWN (flag to reconstruct).
- **2026-08-01 11:18:06** FC1/FFC5 freezer-air highs (3.4-day review, 10 excursions >15 °F): all are defrost (25–29 °F, ~25–40 min) or door events; coast peaks only reach ~16 °F for <1 min, so the load-shedding is NOT warming the freezer. Single highest 36 °F on 08-01 07:28 (defrost + heavy AM doors), brief. ~2 defrosts/day. Air (not food), brief — judged fine.
- **2026-08-01 19:42:42** New ESP32 board (2× PT1000, same pins as existing WROOM-32) VERIFIED over USB serial: both RTDs ~1099 Ω / ~78 °F, matched within 0.3 °F, no faults. Upload failed at 921600 baud (flash-comm / serial-noise error); fixed by lowering upload speed + re-plugging USB, sensors left connected — so NOT a strapping-pin issue. Next: WiFi for temps; current-sense path (Arduino→USB→ubuntu) unchanged.
- **2026-08-01 20:52:41** ESP32 WiFi RTD node — end-to-end networking test PASSED. New board (2× PT1000) → WiFi (RSSI −51) → TCP → Mac listener (192.168.1.243:9000), live temps ~1098 Ω / 77 °F, both channels matched, ~1/s. Strapping-pin upload issue (SPI on GPIO 2/12/15) sidestepped by SOCKETING the ESP32: pull module to flash (RTD lines disconnected), replug to run. Sketch firmware/esp32_rtd_wifi_test (temporary; scrub WiFi creds before any commit). Next: retarget to ubuntu + dual_logger socket ingest.
- **2026-08-02 08:36:44** Adopted CLEAN-WINDOW duty rule (tools/clean_window_duty.py): score each night over the longest defrost-free span in 00:00-07:00 (defrost + recovery excluded), not a fixed 00:00-06:30. Finding: the fixed window was biased HIGH by defrost recovery. Cleaned duties (all FFC=5): FC=1 → 35/41/42% (mean ~39%, 3 nights); FC=3 → 44% (1 clean night; Jul27 69% poor-settle, low-conf). FC=1 still lower (~5pp) — need more clean FC=3 nights. NEXT DATA STEP: switch freezer dial FC 1→3 (keep FFC=5); that dial change is the deferred deploy boundary (status cols + parser fix + P1 rename + ubuntu scp).
- **2026-08-02 14:05:40** POWER LESSON (WiFi RTD node): cheap 500 mA USB adapter CONFIRMED to corrupt MAX31865 reads — one channel dead (−403 F), touch-sensitive, cross-channel interference; cleared INSTANTLY on laptop USB, so it was power, not wiring/CS. 850 mA Motorola = SUSPECT only (display blanked after a few min; not reproduced/isolated). Cause: ESP32+2×MAX31865+OLED peaks <1 A but WiFi-TX current spikes brown out a marginal/noisy supply. Fix: solid 1–2 A RPi-grade supply; now on 2.5 A CanaKit w/ captive cable (no connector to fail).
- **2026-08-02 16:39:22** Just set FC to 3 for testing at FC=3 and FFC=5
- **2026-08-02 16:40:56** Just connected new temp module to ubuntu for testing at FC=3 and FFC = 5
- **2026-08-02 16:57:10** TRANSITION FC 1→3 (freezer dial); FFC stays 5. Swapped temp module: OLD breadboard ESP32 → NEW perfboard ESP32 (esp32_rtd_node.ino). New probes co-located & validated vs old within ~0.1 °F; CS swapped in sketch so freezer→ch1/t1_freezer (confirmed in log: t1=11.8 cold, t2=40.3 warm). FC=1 run ENDED run_auto_0729_0758 (clean through ~16:44; last few min contaminated — swap done while old logger still ran). FC=3 run STARTED run_auto_0802_1649.csv ~16:49, same coast params (Tmin 0/36, Tmax 15/40, max-off 180). Deployed updated dual_logger: +3 status cols (relay_cmd/current_stale/compressor_on) + serial-corruption parser fix; P1 rename DEFERRED. New module browned out on ubuntu USB at first (dropped off, no temps) — Ron fixed; OLED + watch_run OK. Goal: clean FC=3 nights to firm the FC=1-vs-3 duty comparison.
