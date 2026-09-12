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
- **2026-08-02 17:35:53** Food in fridge seems 'really cold' the last couple of days, according to Sue. Not frozen but noticeably colder than usual.
- **2026-08-03 08:08:14** FC=3 clean-night duty (run_auto_0802_1649, night 08-02→03): **65%** over 00:21–05:21 (off 106 min, 2 coasts). Defrost 08-02 22:14–22:48 fell pre-midnight, cleanly excluded. LOW CONFIDENCE — first full night after the mid-day FC 1→3 transition, so freezer-pulldown likely inflates duty (cf. the "poor-settle" Jul-27 FC=3 night). FC comparison now: FC=1 ~39% (3 nights, steady) vs FC=3 44% (Jul) & 65% (this pulldown night) — magnitude still unpinned, keep gathering.
- **2026-08-03 08:08:14** OBSERVED ~4am fridge free-cycle (fridge's OWN thermostat, not our coast): compressor cut out **03:53:18** (I 0.79→0.13 A) with **relay STILL CLOSED (relay_cmd=1)**, our FFC RTD reading **36.1 °F**; came back on **04:14:43** at **38.4 °F** (~21 min off, ~2.3 °F RTD rise). Ron's read: the fridge's internal FFC sensor hit its own cutout while our co-located RTD still read 36.1 °F — a placement/lag offset between the two sensors. Possibly just the transition; unlikely to be the new perfboard RTD since it was validated vs the old module within ~0.1 °F. Flag to watch on later FC=3 nights.
- **2026-08-03 09:45:26** DATA-QUALITY flags on early CSVs (found while sweeping for FFC3 native-cutout data; use tools/free_cycle_scan.py):
    - **kitchen_fridge_run2.csv (Jul 20 07:39 → Jul 21 11:50, ~28 h): UNUSABLE.** current_a flatlines ~0.10 A for the entire run and t2_fridge_f is blank — the current clamp was not reading the fridge. No compressor cycles recoverable. Do not use.
    - **kitchen_fridge_run.csv (Jul 19 15:29 → Jul 20 07:32): FIRST ~7 h INVALID.** Probes swapped/settling — early rows read fridge=14.8 °F / freezer=42.6 °F (backwards) with current blank. Valid only from ~Jul 19 22:00 on, where temps settle to fridge ~39 / freezer ~-4. The 3 clean evening cutoffs (22:21, 23:11, 00:01) are the only solid FFC3 kitchen-fridge free-cycles we have.
    - **Appliance provenance:** the Jul 17–19 files (run.csv, my_run.csv, good_run.csv, copy_of_run.csv, freezer_run.csv, freezer_run2.csv) are the CHEST FREEZER, not the kitchen fridge — different compressor, not comparable to the fridge coast experiment. temps.csv / temps_Freezer.csv are an older 5-col format.
    - **FFC3 vs FFC5 native cutoff (fridge shuts its OWN compressor off, no controller):** FFC3 ~39–40 °F (thin: ~3–4 clean events) vs FFC5 ~35 °F (52 events, run_20260721_135703) — a ~4–5 °F warmer cutoff at FFC3, consistent with the 07-21 reconstructed FFC3→5 note. With the coast controller ON, FFC5 cutoffs sit ~40 °F (controller pulls power at Tmax=40 before the fridge reaches its own ~35). No drift in cutoff temp >24 h after any setting change (checked <24h vs ≥24h per run).
- **2026-08-03 17:09:06** CURRENT-CHANNEL DROPOUT correlation + EMI read (analysis of run_auto_0802_1649 12-col + run_auto_0728_0447). Stale-fix history: current_stale/amps_updated_at committed 07-30 (1700cb2), strict-regex false-value reject 08-01 (8d69cce), both DEPLOYED to the ubuntu logger 08-02 — so all 9-col runs (incl. 0727, 0728) predate the fix and log dropouts raw.
    - **Correlation (Aug-2 run):** of stale rows with relay commanded ON (genuine dropouts, ~9.5 min total), **~89% froze at a RUNNING current (>0.5 A); the ~11% "off" are essentially the single 65 s boot transient.** So excluding boot, ~100% of power-on dropouts occur while current is FLOWING — none while idle. Coasts (relay=0) dominate total stale time (209k rows) and are expected.
    - **1.9 A = DEFROST, not compressor inrush (per Ron).** Verified 7/28 ~13:33 defrost = steady ~1.84 A with freezer warming (t1 3.7→4.5 °F). Compressor run ceiling ~1.6 A (Ron's estimate, UNCONFIRMED). Consequence: derived compressor_on=1 misfires during defrost; earlier "07:12 recovery = compressor restart" read is downgraded (that 1.9 blip was likely defrost/corruption, not inrush).
    - **Corruption is real + frequent pre-fix:** run_auto_0728_0447 has 3902 exact "1.000" and 30 "0.000" current readings (lenient-regex garble artifacts; value is 1.000 not 1.0000000 — logger writes %.3f).
    - **EMI read:** dropouts occur during DEFROST too (resistive heater, NO motor switching) — so cause is likely NOT purely the BLDC drive's PWM. Common factor is current FLOWING in the fridge cord (compressor OR defrost). Consistent with current-coupled noise (radiated compressor switching and/or magnetic coupling of cord current into the sensor leads); rules out random idle-time dropouts. NOT proven — clean confirmation = scope on serial/current line during a running/low-speed spell.
    - **Mitigation to try:** snap-on/clamp-on ferrite on the fridge cord (common-mode), and/or on the current-sensor signal leads + Arduino USB cable (the link actually corrupting). Cheap, reversible, good diagnostic — if dropouts drop, EMI confirmed. Ties to the deferred "EMI baud/shielding for current channel" backlog item.
- **2026-08-04 07:41:30** FC=3/FFC=5 night Aug 3→4 (run_auto_0802_1649). Duty **20%** over CLEAN window 03:33–07:00 (3.4 h, off 165 min, 1 coast) — but COMPROMISED: the 00:34–01:00 defrost chopped the night, leaving a short/late/post-recovery window (not comparable to night-1's 65% over 00:21–05:21; late early-AM windows read low anyway). NO clean FC=3 steady-state duty yet (65% pulldown night + 20% defrost-chopped). **No deep cutoff last night** — all 4 free-cycles shallow ~40 °F/7-min, freezer only +1.8..+11 (vs night-1's 36 °F/−11 °F/21-min). The fridge-first "flip" did NOT recur ~2 days post-transition → leans TRANSIENT (pulldown), good for validity. Still need a night with a well-timed/absent defrost for a full ~5 h window.
- **2026-08-04 09:05:56** CORRECTION (Ron) — the fridge controller has a FIXED ~7-min startup delay after power is restored before it starts the compressor (anti-short-cycle), even when cooling is called for. Verified 08-03: relay re-closed 18:27:20 (door-triggered coast end) → compressor stayed off (fresh ~0.12 A, power available) → compressor started 18:35:56 (~7 min). CONSEQUENCE: the ~60 uniform "7-min compressor-off / relay-closed" hits from tools/free_cycle_scan.py are NOT the fridge shutting off a running compressor — they are this post-power-on startup delay after each of OUR coasts. (Supersedes two earlier wrong reads of those hits: "fridge thermostat shut it off" and "current_stale dropouts.") The 5 DEEP events (19–24 min, ~36 °F cut-out, cold freezer, running-preceded: Jul 27 ×4 + 08-03 03:53) remain the only genuine fridge-own-thermostat cutoffs. DESIGN NOTE for rotation: every coast defers cooling by ~7 min on power-restore — a hidden penalty; factor into coast/rotation strategy. free_cycle_scan needs relabeling (it conflates startup-delays with cutoffs).
- **2026-08-04 11:30:55** FRIDGE'S OWN COMPRESSOR CYCLING characterized (baseline run_20260721_135703, FC3/FFC5, no relay control; scratch tool /tmp/fridge_compressor_off.py on ubuntu). 61 events where the fridge stopped its own running compressor (relay closed, fresh current, non-defrost).
    - **Compressor-off FFC temp (our RTD, 1-min avg):** median 34.97 °F, core(≤37) mean 35.14 / std 0.79 (n=55); 6 warm excursions to 42.7 (post-dial-change settling Jul 21 + door/defrost-recovery). So the fridge stops the compressor at **~35 °F**, tight ±0.8. The 36.1 Ron noted is the WARM EDGE, not center. Our coast Tmin=36 sits ~1 °F ABOVE the fridge's ~35 stop → cooling passes 36 (our relay-open) before 35 (fridge's stop), which is why our relay opens first almost every cycle (fridge won only once in the coast file: 03:53, 36.28).
    - **Compressor-off DURATION (natural cycling):** median 23.1 min (mean 22.6, min 4.4, max 57.9); 6 of 60 restarted in <7 min → NO 7-min floor on natural cycling.
    - **DESIGN INSIGHT (rotation):** the ~7-min wait is a POWER-ON delay only — it appears solely because WE open then close the relay. Natural cycling (relay stays closed) gives long compressor-off windows (median 23 min) during which the inverter is free at ~0.1 A draw, with ZERO 7-min penalty. So coasting a load to cut its own duty is likely a NET LOSS (adds 7-min no-cool per restore); prefer to RIDE the loads' natural off windows for rotation and only force a relay-open (eating 7 min) on genuine conflict = two compressors calling for power at once. Interrupt on conflict, not preemptively. (Reframes the coast experiment: coast benefit must beat the 7-min cost, which we weren't counting.)
- **2026-08-05 10:51:19** 1) set FFC=4 and immediately 2) press test button 2x (unless I want to confirm TEST 1 does what it is supposed to do) 3) check that defrost is happening and wait for it to end 4) check FFC=3 (the reset happened) 5) hope and check for a defrost 4 hours later. 6) if no defrost at 4 hours, use open door strategy to get a defrost, say, between 8pm and 10pm. Remove control board cover (10:33) Confirm FFC=5 - that's what we are running. (10:43). Confirm relay closed and not about to open - FFC @ 37.1 (10:44) Set FFC = 4 (little change) avoid fridge cut off. (10:48) Press TEST confirm "TEST 1" = every display LED ON (same as FFC=5) (10:48) Press TEST confirm "TEST 2"= LEDS for FFC 1,3,5 all ON(10:48) Clamp meter shows 1728mA. Waiting for defrost to end.(10:48)
- **2026-08-05 11:15:29** Noticed defrost ended. Back to setting FFC=4 - not FFC3 as hoped/expected.
- **2026-08-05 11:18:08** Set FFC back to 5 to continue our run
- **2026-08-05 11:21:26** DEFROST INVESTIGATION + forced-defrost test (LG LTCS20020S kitchen fridge; complements Ron's manual-action entry).
    - **Defrost model (manual §8-1-2/8-1-7, confirmed vs data):** defrost triggers at 7–50 accumulated COMPRESSOR-RUN-hours, shortened by door-open time (toward the 7 h floor); **4 run-hours** after a genuine initial power-on / power restore; ends when the defrost sensor reaches **10 °C (50 °F)** (else 1–2 h = fault). Observed run-hour intervals in run_auto_0802_1649: 7.78 / 8.00 / 8.50 / 7.47 — low end = normal door activity holding it near the 7 h floor. Defrost heater draws ~1.85–1.9 A (≈2.8 A warm-up spike); the derived compressor_on flag misreads that as "compressor on" (heater ≥1.7 A is excluded from run-hour math).
    - **The 4-hour "power-restore" mode does NOT arm on our power interruptions.** Across the run, defrosts fired at cumulative ~7–8 run-hours while the relay was opened (fridge power cut) 3–5× (tens of min each) between them; compressor run-time since the last relay-close at each defrost was ~0 h, never ~4. So a brief relay-open — and, by the same physics, a brief unplug — is NOT seen by the fridge as a real "power restore." Likely mechanism (Ron): no clock while unpowered, so the fridge infers outage duration from physical evidence (capacitor charge, temperature drift); brief interruptions leave none, so the 4-hour mode never arms. Genuine 4-hour arming would need a long (hours) outage.
    - **Forced-defrost test 2026-08-05:** set FFC=4 (reset detector), pressed PCB test button to **TEST 2** (§8-1-12; display lights 1,3,5). Forced defrost ran **10:48:11 → 11:13:25 (~25 min)**, auto-ended at defrost-sensor 10 °C; freezer air −2.7 → ~21 °F. **FFC stayed 4 after exit (NOT the default 3)** → the TEST 2 auto-exit preserves settings, is NOT a factory reset → did not arm the 4-hour mode. PREDICTION: next defrost at the normal ~7–8 run-hours from 11:13 (watching to confirm). The 3rd-press "Reset to default" (→ FFC 3) was NOT tried — the only untested reset path.
    - **KEEPER capability:** TEST 2 (two presses of the PCB test button) = **forced defrost on demand (~25 min).** This is the reliable way to place a defrost at a chosen wall-clock time — no 4-hour shortcut needed. Force one in the EVENING (~8–10 PM) to push the next natural defrost to late morning and clear the overnight scoring window (overnight defrosts at 00:34 / 01:52 wrecked the last 3 FC=3 windows).
    - **DATA CONTAMINATION:** everything in run_auto_0802_1649 since ~10:48 (forced defrost + FFC=4) is OFF-EXPERIMENT. Set FFC back to **5** to resume FC=3/FFC=5.
    - **Open (compressor type):** manual mentions PTC + O.L.P (overload protector), against the "inverter, no PTC/locked-rotor" working assumption. Possibly manual carryover from a prior variant (manuals = hints). Data shows soft starts / no measured inrush, but 10 Hz can't resolve inrush — unresolved; a scope would settle it. Matters for furnace.json cross-load surge notes (which call the chest freezer the ONLY locked-rotor load).
- **2026-08-06 08:12:20** OVERNIGHT Aug 5→6: 3-HOUR CURRENT DROPOUT + partial score.
    - **Dropout 04:07:53–07:08:57 (~3 h):** the current-sensing Arduino stopped responding — current froze at ~0.95 A, current_stale=1 for 93% of the window (flag worked). Because that Arduino also drives the relay, the commanded power-cut could not be enforced: relay_cmd sat at 0 the whole time, but the fridge STAYED POWERED and ran normally — temps cycled (FFC 34–38, FC −5..+5 °F; a truly unpowered fridge would warm far past that). Fail-safe-to-power-ON worked; food never at risk. Controller wedged at relay_cmd=0 for the full max_off (180 min) and "restored" at 07:08 (= the 180-min mark from 04:08). For that window ONLY the temps are trustworthy; current + relay_cmd are stale/wrong.
    - **SCORE (pre-dropout stretch 00:00–04:08, 4.13 h, defrost-free; FFC restored to 5 on 08-05 11:18):** duty = **57%** (relay-closed / window, tool convention); relay-open 107 min, 4 power-cut events, no defroster. Cleanest SETTLED FC=3/FFC=5 duty so far (not pulldown, not defrost-recovery, not a late chopped window) — but it's an EARLY window (00:00–04:08), so not apples-to-apples with the late chopped windows (03:xx–07:00) of Aug3→4 (20%) / Aug4→5 (42%); duty runs lower later at night. Directionally FC=3 (57–65%) > FC=1 (~39%), consistent with the damper model. Rest of the overnight window blown by the dropout.
    - **TWO ISSUES:** (a) current channel — a 3-h dropout confirms the EMI/serial reliability problem needs mitigation (shield/ferrite/lower baud); (b) the relay-open control WEDGES at relay_cmd=0 when the current goes stale — it should restore power / ride through stale current instead of holding a phantom power-cut for the full max_off.
- **2026-08-06 09:03:30** CORRECTION to the 2026-08-06 08:12:20 entry (pulled the RAW serial log — earlier diagnosis was wrong).
    - **NOT EMI, and NOT an Arduino hang/dropout.** During 04:08–07:09 the raw log (run_auto_0802_1649.raw) shows the CUR Arduino was neither silent nor emitting garbled lines — it emitted HOLD-OFF COUNTDOWN messages ("N:N remaining...", ~65 cycles). That means it was being REPEATEDLY RESET, i.e. dual_logger's own power-cut mechanism (reset the Arduino to hold relays open). So the frozen current for that window is the BY-DESIGN signature of a commanded power-cut, not a fault. RETRACT the earlier "Arduino stopped responding" and the "EMI/serial reliability problem (issue a)" — both wrong for this event. (Separate and unproven: the brief corruption-flagged dropouts during current flow MIGHT be EMI; not this.)
    - **THE REAL PUZZLE (flagged, unresolved):** the temps CYCLED (FFC 34–38 °F, cooling → fridge POWERED) throughout the 3-hour commanded power-cut, while the Arduino was reset-looping to hold the relays OPEN. So the relay very likely did NOT actually cut power — the controller ran a PHANTOM 3-hour power-cut while the fridge kept running normally. The power-cut mechanism may not be reliably de-energizing the fridge. The only witness to real power is the current (frozen during a cut); the temps are what expose the mismatch. TO INVESTIGATE: does a commanded relay-open actually de-energize the fridge? relay wiring / target channel (firmware says "Target channel: 3") / the reset-hold approach itself?
    - **Still stands:** food never at risk (fridge stayed powered). The 57% score for 00:00–04:08 stands. Note issue (b) is really part of the same puzzle — the controller held relay_cmd=0 for the full max_off and never restored at Tmax=40 even though FFC went above 40, and meanwhile the cut wasn't actually cutting.
- **2026-08-06 11:49:56** HARDWARE-CONFIG NOTES (retroactive, for data hygiene):
    - **Fridge control/driver board cover OFF + power cord ON the board:** from ~yesterday's forced defrost (Aug 5 ~10:48) until Aug 6 ~11:20, the fridge's control/driver board cover was off AND the fridge power cord was routed on top of / touching components on that board. EMI/interference risk to the FRIDGE's OWN control (compressor drive, defrost, sensors) — NOT our relay side, so it does not explain the phantom cut, but it's another reason the whole Aug 5→6 window is suspect (already flagged: forced defrost, FFC=4 excursion, the 3-h relay-not-actually-cutting night). Cover replaced and cord rerouted ~11:20 Aug 6.
    - **Combined current clamp since ~10:25 Aug 6:** for the phantom-cut AC-witness test the wiring is now switched-outlet → 1 ft cord (clamp here) → power strip → laptop + fridge, so the logged current reads laptop + fridge COMBINED. Laptop baseline ~0.2–0.4 A (varies with battery charge state; ~0.4 charging, less when Full). Current-derived metrics (run-hours, compressor-on/off, defrost detection) are contaminated until the clamp is fridge-only again — fridge current ≈ total − laptop.

## 2026-08-07 ~07:35 — Compressor current step-up mid-run, and freezer temp lags it (~2 min)

Observed on run_auto_0802_1649.csv (FC=3 / FFC=5, BLDC inverter compressor). During a
long compressor-on period the controller steps the compressor CURRENT up partway
through the run; a small transient step UP in FREEZER temp accompanies it. Question
asked: does the freezer-temp step precede or follow the current step? **Answer from the
data: it FOLLOWS, by ~2 min.**

Measured precisely on the current run (relay closed 06:17, compressor running 06:17→,
started warm at freezer +13 °F after a long relay-open power cut 04:xx–06:08 + the
~7-min startup delay — NOT a defrost):

- Current: steady ~0.822 A through 07:04:33, then **step-up onset 07:04:36**
  (0.822 → 0.866 in ~3 s, settling ~0.90 A by 07:06:00). **Size ≈ +80 mA.** ~48 min
  into the run.
- Freezer temp: keeps *cooling* for ~90 s after the current rises (floor −5.6 → −6.0),
  then **warm-step onset ~07:06:36** (−5.9 → new warmer floor ~−4.5 by 07:08:30).
  **Size ≈ +1.4 °F.**
- So current LEADS; freezer temp FOLLOWS by ~2 min (thermal lag). Because the freezer
  temp lags, **freezer temperature did not trigger the step-up** — the controller
  commanded the higher compressor speed for another reason (likely fresh-food-side
  demand or an FC-damper reconfiguration at FC=3, diverting air to the starved FFC),
  and the freezer warming is the consequence.

**Confirmed on the previous compressor-on period too — the run that started 03:12**
(compressor on 03:12 at freezer +11.6 °F, warm after a relay-open cut + the ~7-min
startup delay):
- Current declined on pulldown to a floor ~0.84 A (03:35–03:47), then **stepped up at
  ~03:47–03:48** (0.855 → 0.887 → 0.905), settling ~0.91 A by 03:50. **Size ≈ +70 mA**,
  ~36 min into the run.
- Freezer temp fell to a floor **−5.0 °F at 03:50**, then **warm-stepped at
  ~03:50–03:51** to a warmer floor ~−3.6 by 03:57. **Size ≈ +1.4 °F.**
- Again the freezer FOLLOWS the current, by ~2 min. So **two runs now show the identical
  signature (03:12 and 06:17)** — repeatable FC=3 behavior, not a one-off. (Ron's live-chart
  read of the two was ~75/85 mA at ~45–50 min; the measured 03:12 step is ~+70 mA at
  ~36 min — same phenomenon, size/timing vary run to run.)

**Hypothesis to test (Ron):** the compressor speed increase produces a transient rise
in EVAPORATOR temperature, which shows up at the freezer sensor as the step UP in FC
temp. (A refrigerant-side transient on speed change, seen through the evaporator/air
thermal mass — consistent with the ~2 min lag.)

**Also queued for next session:** how does FC=3 (FFC dial constant at 5) compare with
FC=1 (FFC 5) — duty and run-structure.

- **2026-08-08 ~08:00** FC=3/FFC=5 clean-night duty (run_auto_0802_1649, night 08-07→08): **51%** over CLEAN window 00:00–05:00 (5.0 h, off 146 min, 3 coasts; clean_window_duty.py). No overnight defrost (the 20:00–20:12 one fell pre-midnight, excluded); no dropout/fault — the ~47% current_stale is entirely the by-design current-freeze during the two ~77-min commanded power-cuts (CUR Arduino reset-loops while relays held open). Regular rhythm: ~77-min coasts (02:05→03:21, 04:36→05:53, plus one straddling midnight), each ending when the fridge warmed to Tmax=40 °F → relay re-closed. Current is fridge-only again (idle ~0.12 A, compressor running ~0.95 A; the earlier laptop-combined-clamp contamination is gone). t2 spike to 50.8 °F / t1 to ~13 °F at 07:18–07:30 = morning door activity, outside the scoring window (normal, not a fault). SIGNIFICANCE: cleanest STEADY-STATE FC=3/FFC=5 night yet (6 days post FC 1→3 transition, so not pulldown) — firms the comparison **FC=3 ~51% vs FC=1 ~39%** (both FFC=5, clean), ~12 pp higher duty at FC=3, consistent with the damper model and the FC=1-for-rotation decision.

- **2026-08-08 ~15:00** POWER-ON (coast-restart) SEQUENCE characterized — "how the fridge works" piece. From run_auto_0802_1649, **n=44** cleanly-captured power-ons (every relay-close = a power-on for the fridge). Deterministic, 44/44 identical: **power restored → ~0.5 s → defrost heater ON ~4.0 s (~1.9 A) → heater OFF → ~7.05 min hold (423 s, anti-short-cycle) → compressor + freezer fan start.** Heater duration rock-solid 4.0 s (min 4.0/max 4.1), independent of t1 (freezer-air probe ranged −2.4…+12.5 °F). Resolves the ambiguity between the two LG LTCS20020 "INITIAL POWER ON" else-branch flowcharts: the **10 s-heater version is RULED OUT**; heater ~4 s (≈4.5 s allowing for the sub-1.5 A rise/fall edges the >1.5 A threshold clips) is consistent with the **5 s-heater version**. BUT the heater-off→compressor time (~7 min) matches **neither** flowchart's post-heater wait (0.5 s or 10 s) — on our restarts the manual's short compressor step is overridden by the ~7-min power-restore anti-short-cycle (consistent with the 08-04 note; not shown in either flowchart). Every capture showed the heater pulse = the "else" branch (evap ≤113 °F inferred from *behavior*; we do NOT measure the fridge's defrost/evap sensor, so the branch condition can't be confirmed directly — t1 is freezer AIR, not the evap sensor). Caveat: all events are brief-coast restarts, which the fridge may not treat as a genuine cold plug-in; the flowchart's short compressor timing is untestable with our rig. Method: current clamp; detect brief >1.5 A pulse preceded by fresh idle, measure on→off and off→compressor.

- **2026-08-11 — FFC compressor control law identified (P + Bias) from kitchen_fridge_run.csv.**
  Controller senses FRESH-FOOD temp ONLY (verified: at ON/OFF edges FFC is ~3x tighter than
  freezer — cut-out FFC std 0.18 °F vs frz 0.61; cut-in 0.51 vs 1.69). For the SETTLED running
  cycles (07-19/20 cycles B, C, D) the running current is well predicted by a proportional law:
  **current ≈ 784 + 31·(FFC − 39.5) mA**, i.e. **Kp ≈ 31 mA/°F**, **Bias ≈ 784 mA** (at FFC 39.5),
  fit RMS ~17 mA (~2%). Fitted as shared-Kp + per-cycle-Bias across B/C/D; the per-cycle Bias came
  out essentially constant (785/781/786 mA). **Ki (integral) appears small** — proportional-only
  already fits to ~2%; P and I aren't separable within a monotonic cooldown, so Ki is only bounded
  as minor, not measured. **Cutoff** falls on the same line: at the cut-out FFC (~38.9 °F) the law
  gives ~765 mA — the observed min-speed floor. So "min-speed floor" and "FFC hit 38.9" are the same
  event; the data can't say which is the trigger. **Cycle A (the pulldown) runs ~200 mA ABOVE the
  law** → a different (higher) effective Bias, but we DON'T know the pre-A history — the file is a
  mess before A — so A's bias is not pinned. Plot: `analysis/ffc_control_law.png` (actual current,
  the law, and FFC temp over cycles A–D). CORRECTS the earlier "restart current decreases → Bias
  tracks thermal mass" reading (loads/kitchen_fridge.json compressor_control_model): the raw restart
  drop (873→839→814 mA) is mostly cut-in-FFC differences + the ~1-min restart boost, not a falling
  Bias — B/C/D share one line. JSON still to be synced to this.

- **2026-09-04 15:05 — POWER-ON DELAY CONFIRMED AFTER A MULTI-HOUR OFF PERIOD (real outage).**
  Extends the n=44 characterization of 2026-08-08, whose stated caveat was that *"all events are
  brief-coast restarts, which the fridge may not treat as a genuine cold plug-in."* During the
  2026-09-03/04 outage the kitchen fridge sat **unpowered ~2 h** (rotation gave the inverter to the
  chest freezer ~13:00–14:58), then: **powered 14:58 → compressor + freezer fan started 15:05,
  ≈7 min.** Same delay as the brief-coast restarts. So the anti-short-cycle hold is NOT specific to
  short coasts; it survives a multi-hour outage-scale off period. The flowchart's "genuine cold
  plug-in" branch remains untested (that would need a truly cold/long-dead unit), but the practical
  range of the ~7-min constant is now much wider than the Aug-8 entry could claim.
  METHOD NOTE: 15:05 is the observed compressor start; the power-on time was a wall-clock guess
  ("14:55 or so"). Ron correctly inverted the inference — the 7.05 min constant is measured 44/44
  identical, the human timestamp was not, so the constant calibrates the timestamp: 15:05 − 7.1 min
  = **14:58**. Trust the hard number over the soft one, not the reverse.

- **2026-09-04 — PRE-POWER OVERLAP: analyzed, NOT adopted, NOT tested. Recorded so it is not
  re-derived from scratch.** IDEA (Ron): since the fridge does nothing for ~7 min after power-on,
  apply power to the fridge ~7 min BEFORE removing power from the other load, so the anti-short-cycle
  hold elapses during the overlap and cooling resumes the instant the swap completes. This would hide
  the "hidden penalty" flagged in the 2026-08-04 design note (every relay-open costs ~7 min of no
  cooling on restore).
  WHY IT IS PROBABLY SAFE: the binding constraint in this system is **surge coincidence, not steady
  draw** (docs/hardware.md; loads/furnace_electrical_load.md §3). During the overlap the fridge draws
  1.9 A for 4.0 s (defrost-heater pulse) then ~0.12 A idle; the chest freezer runs at 0.72 A. Worst
  instant ≈ 2.6 A ≈ 300 W against a 1000 W inverter. And when the fridge compressor does come up it is
  a **BLDC inverter compressor — soft start, measured 1.5 A peak, NO locked-rotor inrush** — so its
  start alongside a running freezer costs nothing.
  RESIDUAL RISK (the reason this is not adopted): if the chest freezer's mechanical thermostat happens
  to cycle it **ON** during the 7-min overlap, its locked-rotor surge coincides with the fridge's
  draw. That surge is the one real inrush in the system and is still UNMEASURED — lessons.md #10 says
  the ~3.5 A figure is method-limited (10 Hz / 100 ms RMS cannot resolve it) and the true peak is
  likely much higher. Short window, real risk, unquantified.
  RELATION TO EXISTING GUIDANCE: does not contradict "interrupt on conflict, not preemptively"
  (2026-08-04 design insight) — it only reduces the cost of a swap that has already been decided on.
  TO SETTLE IT: measure the chest freezer's actual LRA magnitude and duration with a scope + shunt
  (already an open item in loads/furnace.json provenance.open_items).
