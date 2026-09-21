# Prior-art sketches — Nov 2024 to Mar 2025, outside the repo

Surveyed 2026-09-21. **23 Arduino sketches** sit in
`~/Documents/RetirementWork/Engineer/inverter/` on the Mac — the data directory, one
level above this repo — and **none of them are in version control**. They predate the
repo by about eighteen months and several of them are directly relevant to work now
being designed here.

They are NOT copied in, because **10 of the 23 have the live WiFi SSID and password
hard-coded** and this repo is public on GitHub. Anything moved in must first take
credentials from `firmware/shared/wifi_secrets.h` (git-ignored, template in
`wifi_secrets_example.h`).

## The ones that matter

| Sketch | Date | Why it matters |
|---|---|---|
| `continuous_ADS1115` | 2024-12-26 | Interrupt-paced ADS1115 sampling, 860 SPS |
| `nonblocking_ADS1115` | 2024-12-26 | `startADCReading` / `conversionComplete` shape |
| `timer_interrupt_esp32` | 2024-12-26 | ESP32 hardware-timer ISR |
| `rms_ac_with_filters_master` | 2025-01-02 | True-RMS with two-point calibration |
| `running_statistics_socket_server_2` | 2025-02-02 | The convergence: ISR sampling + RMS + socket |
| `esp32_acs712_ads1115` | 2025-03-08 | Bring-up sketch for the §7 perfboard node |
| `socket_server` | 2024-12-20 | ESP8266 — the only ESP8266 network code here |

## Worth reusing

**Interrupt-paced ADS1115 sampling.** `continuous_ADS1115` and
`running_statistics_socket_server_2` already have the correct non-blocking pattern:
`IRAM_ATTR` ISR on ALERT/RDY setting a `volatile bool`, `startADCReading(...,
continuous=true)`, `getLastConversionResults()` in the loop, `RATE_ADS1115_860SPS`.
This is what the ALERT/RDY line on GPIO16 exists for (`docs/mcu_inventory.md` §7).

**`RunningStatistics` from the Filters library.** `inputStats.sigma()` is AC RMS with
DC removed, which is the right measure for an AC current. Note what goes unused:
`inputStats.mean()` is already computing the DC offset — a **live zero** — and every one
of these sketches then ignores it and hard-codes `2.5`. Lesson #4's auto-zero wants
exactly that number.

**Two-point calibration.** `rms_ac_with_filters_master` computes
`Amps_TRMS = intercept + slope * sigma()`. That is the mechanism `mcu_inventory.md` §5
says is mandatory before any ADS1115 number can join the existing dataset.

## Do NOT reuse — the socket half is the wrong shape

Seven sketches implement a `WiFiServer` on port 80. Both of its properties are wrong
for this system:

- **Direction is backwards.** `docs/dual_logger_socket_ingest.md` §2 requires nodes to
  **dial out** to the logger, so the logger never needs to know a node's address and
  DHCP can move nodes freely. These wait to be connected to.
- **They block.** The pattern is `while (client.connected()) { while
  (client.available()>0) {...} delay(5); }`. While a client is connected the sampling
  loop never runs. That is §9's starvation failure by construction — the one measured on
  the RTD node at 41 samples in 122 s where 1 Hz should give ~122.

**Drop the NTP machinery too.** Node-side time is not wanted: §5 arrival-stamps every
line at the logger, and a node clock is a second clock (lesson #8).

The echo loops and the `while(a<9) client.write("a")` counters are demo scaffolding from
whatever tutorial these started as. Nothing to carry over.

## Flags

**The differential arrangement was written, then parked.**
`readADC_Differential_2_3` appears in four sketches, but
`running_statistics_socket_server_2` runs `ADS1X15_REG_CONFIG_MUX_SINGLE_0` with the
DIFF_2_3 line commented out. So §5's "electrically better than what the rig does"
arrangement exists in code but is not what runs. Decide it deliberately rather than
inheriting a comment-out.

**Single-ended reads use a hard-coded 2.5 V zero**, with a commented-out `2.325` from
some earlier bench session sitting next to it — the drift lesson #4's auto-zero window
exists to catch.

## An opening on lesson #10

These sample at 860 SPS but keep only `sigma()` over a ~167 ms window, so peaks are
averaged away before anything records them. **A per-window max-hold on the raw samples
would cost nothing and would bound the chest freezer's inrush**, which lesson #10 says
is currently unmeasured and which `docs/jackery_300_plus.md` calls the single strongest
argument for a scope measurement.

At ~14 samples per 60 Hz cycle this still cannot give a true instantaneous peak —
lesson #10's conclusion is unchanged — but it would move that number from "unmeasured"
to "bounded", and unlike a scope it can sit for days waiting for a cold start.

## What this does NOT answer

`socket_server` proves basic ESP8266 connect works (`ESP8266WiFi.h`, `WiFi.begin`,
`WiFi.status`, `localIP`). It does **not** close the open item in
`docs/wifi_bridge_build.md`: nothing here does best-AP-by-signal, WiFi event handlers,
or BSSID logging, so the ESP32→ESP8266 translation of `docs/esp32_wifi_production.md`
is still unanswered.
