# Rig current over WiFi — D1 mini bridge build

**Status 2026-09-20: not built.** This is the build-and-bring-up procedure, written
before the parts are on the bench so the traps are known in advance.

**Why it exists.** The goal is Ubuntu upstairs with the rig still in the basement.
Passive USB tops out around 5 m, so moving the laptop forces the current stream onto
WiFi — it stops being a preference. Temperature was already going that way
(`docs/dual_logger_socket_ingest.md`).

```
Uno WiFi Rev2 (relays + ACS712)
  └─ hardware TX (D1), 9600 baud
       └─ 2-resistor divider (5 V → ~3.3 V)
            └─ D1 mini RX (SoftwareSerial pin)
                 └─ WiFi → TCP → dual_logger listener
```

The Uno keeps printing the same `t_ms,amps,note` lines it prints today. The bridge
never parses them. Only the transport changes, so `dual_logger`'s parser needs nothing
new and post-change numbers stay comparable to the whole existing dataset.

## Why a bridge, and not the Uno's own NINA radio

The Uno WiFi Rev2 has a radio. Two reasons not to use it, both already in the repo:

- `docs/dual_logger_socket_ingest.md` §9 — "**Unverified:** which library revision is
  installed and whether its connect can be bounded." A blocking connect is not a
  theoretical worry: the RTD node starved to 41 samples in 122 s where 1 Hz should give
  ~122 (measured 2026-09-10).
- §10 — a transmitter inches from the ACS712 analog lines may trade a comms problem for
  a measurement problem. NINA is a separate chip that schedules its own beacons, ACKs
  and retries, so "sample, then transmit" cannot be enforced from `loop()`. And
  `docs/hardware.md` already records a CONFIRMED case of this shape: a 500 mA adapter
  corrupting MAX31865 reads because "WiFi-TX current spikes brown out a marginal
  supply." The rig runs off an 850 mA brick that also feeds relay-module and sensor VCC.

A separate bridge board with its own supply, on a short cable, converts an unmeasured
risk into a layout choice. Same recipe later serves the Nano Every node between Jackery
and fridge (`docs/mcu_inventory.md` §3) — build it once, here, where the Uno is already
producing lines to test against.

---

## Step 1 — Parts check

- [ ] **D1 mini (ESP8266 ESP-12F)**, board selection `LOLIN(WEMOS) D1 R2 & mini`
      (`docs/mcu_inventory.md`).
- [ ] **Two resistors** for the divider. Target: 5 V in, **3.0–3.3 V** out, by
      `Vout = 5 × R2 / (R1 + R2)`. 1 kΩ (series from Uno TX) + 2 kΩ (to GND) gives
      3.33 V. 1.5 k/3 k or 10 k/20 k are equally fine at 9600 baud.
- [ ] **Its own USB supply for the D1 mini — 1 A or better.** Do NOT power it from the
      Uno's 5 V rail. Sharing the rail re-creates exactly the supply-droop coupling this
      whole approach exists to avoid, and the confirmed brownout case above is the
      precedent.
- [ ] Jumper wires; the D1 mini mounted where its antenna is **away from the ACS712
      wiring**, not adjacent to it.

## Step 2 — Drop the rig to 9600 baud FIRST, and prove it on USB

Do this before any wiring. It is an atomic change across two files and it is easier to
debug with the known-good USB path still in place.

Two independent reasons it has to happen:

- One UART, one baud. Tapping TX means USB and the bridge both run at whatever the
  sketch sets; they cannot differ.
- SoftwareSerial RX on an ESP8266 is not dependable at 115200. 9600 is.

It is also already queued on its own merits — `docs/todo.md`: "LOWER baud (e.g. 115200
→ 19200 or 9600). Payload is ~80 B/s, so enormous headroom / no throughput cost; slower
bits = more noise margin. **Requires the Arduino sketch + `--current-baud` changed
together.**"

- [ ] Change `Serial.begin()` in the sketch currently on the rig (`characterize_load` as
      of 2026-09-12, per `docs/todo.md`) to 9600. Re-upload.
- [ ] Run `dual_logger.py` with `--current-baud 9600`.
- [ ] **Verify:** clean `t_ms,amps,note` lines, and the corrupt-line rate from
      `tools/cur_corruption_scan.py` no worse than the 115200 baseline.
- [ ] **Stop-and-fix:** garbled lines here mean the two halves disagree on baud. Do not
      proceed into wiring with a broken baseline.

## Step 3 — Wire the tap

One-way link: the Uno talks, the bridge listens. Nothing drives the Uno's RX, so no
level shifting is needed in the other direction.

- [ ] **Common ground first.** Uno GND ↔ D1 mini GND. Without it the divider has no
      reference and the link will not work.
- [ ] **Divider from the Uno's hardware TX (D1).** R1 from TX to the junction, R2 from
      the junction to GND, junction to the D1 mini's RX pin.
- [ ] **Verify with a meter before connecting the ESP:** junction should sit at
      3.0–3.3 V while the Uno is transmitting idle-high. Over 3.6 V is out of spec for
      an ESP8266 input — recheck the resistors.
- [ ] Connect the junction to the D1 mini's **SoftwareSerial RX** pin.

### Pin traps — read before soldering

- **Do not put the serial link on the Uno's D5/D6.** `docs/hardware.md` maps
  **D5 → IN4 / Ch4** on the rig. The rig has no spare pins to give, which is why the tap
  goes on the existing TX instead. Note that `docs/mcu_inventory.md` §3 says
  "SoftwareSerial on spare pins (D5/D6)" without naming which board — it means the
  **ESP side**. Read literally against the rig's Uno it lands on a relay line.
- **Do not use the D1 mini's hardware UART (GPIO1/GPIO3).** They are shared with its
  USB-serial converter, so the link would fight flashing and serial debugging — the same
  family of trap as lesson #6.
- On the D1 mini, **D5 (GPIO14), D6 (GPIO12), D7 (GPIO13)** are the safe SoftwareSerial
  choices. Avoid D0 (GPIO16, no interrupt, so it cannot serve as SoftwareSerial RX) and
  the strapping pins D3 (GPIO0), D4 (GPIO2), D8 (GPIO15). This mapping is the standard
  D1 mini silkscreen — **confirm against the board in hand** before soldering.
- Tapping TX does not disturb USB. TX is an output and can drive two listeners, so the
  USB stream keeps running in parallel. That is deliberate — Step 6 depends on it.

## Step 4 — Bridge firmware

Not written yet; this is the specification it must meet. The job is deliberately small:
read lines, push them, reconnect. It is **not** a port of `esp32_rtd_wifi_node`, which
also does RTDs, a web page, LittleFS and an OLED.

- [ ] **Credentials from `firmware/shared/wifi_secrets.h`** (`WIFI_SSID` / `WIFI_PASS`),
      which is git-ignored, with `wifi_secrets_example.h` as the template. **This repo is
      public on GitHub — never inline credentials in a committed sketch.**
- [ ] **Config block** carrying `NODE_ID` and role, matching the existing node's shape.
- [ ] **Never block in `connect()`** (§9). Bound the attempt and keep reading serial
      regardless.
- [ ] **Drop unsent lines on reconnect — never replay** (§5). A replayed sample arrives
      with an arrival-stamp wrong by the length of the outage, which is lesson #8 again.
- [ ] **Hello line on connect** giving role and node id. `docs/dual_logger_socket_ingest.md`
      §3 leaves one-port-with-hello vs port-per-role open; **one port with a hello line is
      the choice**, because five senders are now in view (rig current, three RTD nodes,
      the Jackery node) and port-per-role means assigning ports forever.
- [ ] **Heartbeat** even when nothing changes (§4), so a gap means "node silent"
      unambiguously.
- [ ] **Disconnect/reconnect records into the stream**, not just Serial (§2).
- [ ] **Line-format rule for anything the bridge generates itself:** prefix with `#`.
      `cur_re` is whole-line anchored so `#` lines cannot be mistaken for samples — but
      **`fault_re` is `[Ff]ault` and matches anywhere in any line**, so the word "fault"
      must never appear in a hello, heartbeat or status line.

### Unresolved: the shared connect routine is ESP32 code

`docs/esp32_wifi_production.md` specifies best-AP selection
(`WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN)` + `WIFI_CONNECT_AP_BY_SIGNAL`), the
`WiFi.onEvent` disconnect handler, and mDNS — all **ESP32** APIs. The D1 mini is
ESP8266: different library, different event API, and the ESP8266 core's scan/sort
behaviour is **not verified here**. Settle the ESP8266 equivalents before writing the
sketch; the requirement (pick the strongest of two same-SSID APs, log every transition,
identify the AP by **BSSID, not channel**) carries over unchanged even though the calls
do not.

## Step 5 — Bench test against a stand-in listener

The `dual_logger` listener does **not exist yet** — `docs/dual_logger_socket_ingest.md`
is scope only. Prove the chain without it first, so a failure here is unambiguously the
bridge.

- [ ] On Ubuntu: `nc -l 9000 | tee /tmp/bridge_test.txt`
- [ ] Power the bridge.
- [ ] **Expect:** the hello line, then a steady stream of `t_ms,amps,note` lines
      identical in shape to what arrives over USB.
- [ ] **Compare directly:** capture USB and TCP over the same window and diff the
      payloads. They come from one UART, so they should agree line-for-line.
- [ ] **Stop-and-fix:** nothing arriving → check common ground, then the divider voltage,
      then that RX is on a pin that can do SoftwareSerial. Garbage arriving → baud
      mismatch or a divider sitting too low.

## Step 6 — The §10 interference test (do it while both transports run)

Tapping TX means USB and WiFi carry the **identical byte stream at the same time**, so
this is a same-data comparison rather than the same setup run twice.

- [ ] Dummy load drawing a steady current (Ch4 / "Spare", per `docs/rig_startup.md` — not
      an appliance).
- [ ] Log with the bridge powered but idle, then with it transmitting continuously.
- [ ] **Compare the mean and the spread of the current samples**, not the corrupt-line
      rate — measurement corruption and comms corruption are different failures and
      `tools/cur_corruption_scan.py` only sees the second.
- [ ] A shifted mean or a widened noise floor is the answer §10 asks for. If it appears,
      move the bridge further from the sense wiring and repeat before changing anything
      else.

## Step 7 — Hand off to the listener

Once the chain is proven, build the listener side per
`docs/dual_logger_socket_ingest.md`: one new generator with the same contract as
`_serial_lines()`, `--current-port socket`, bind up front, nodes may join late. Nothing
in the parser, the merge, or the CSV columns changes.

---

## Open items this doc cannot close

- **ESP8266 equivalents** of the ESP32 connect routine (above). Blocks Step 4.
- **Where does the listener actually live?** `esp32_rtd_wifi_node.ino` has
  `HOST = "192.168.1.243"`, and **nothing answers at .243** (checked 2026-09-20). The
  Mac is .138 and the Ubuntu box is .110 — both DHCP. Pin the logger's address with a
  DHCP reservation before committing a HOST into two sketches, or the first lease change
  silently kills every node.
- **`docs/mcu_inventory.md` §3's "D5/D6"** does not say which board. Fix it there so the
  ambiguity does not survive to the Nano Every build.
