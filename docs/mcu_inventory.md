# MCU inventory, board selections, and the sensing-node decision

Recorded 2026-09-14, from a bench inventory while Ron was soldering the perfboard RTD
nodes. Purpose: stop re-deciding this, and write down the one thing most likely to bite
— the relay startup order differs between the two AVR families now on the bench, and
the correct order is **opposite** between them.

## 1. What is on hand

| Board | Chip | Logic | WiFi | Arduino IDE board | Role |
|---|---|---|---|---|---|
| Uno WiFi Rev2 | ATmega4809 (megaAVR) | 5 V | yes (NINA-W102, **never used here**) | `arduino:megaavr:uno2018` | the rig |
| **Nano Every** | **ATmega4809 (megaAVR)** | **5 V** | no | `arduino:megaavr` core | **chosen: sensing node** |
| Nano (classic) | ATmega328P | 5 V | no | Arduino Nano | spare |
| Uno R3 | ATmega328P | 5 V | no | Arduino Uno | spare; box marked "no boot loader?" |
| Yún | ATmega32U4 + Atheros AR9331 | 5 V | yes (Linux side) | Arduino Yún | **discontinued** — see §4 |
| ESP32 boards w/ OLED | ESP32-WROOM-32 | 3.3 V | yes | `WEMOS LOLIN32` | RTD nodes (`cf.local`) |
| NodeMCU, 30-pin | ESP8266 ESP-12E | 3.3 V | yes | NodeMCU 1.0 (ESP-12E Module) | spare radio |
| **D1 mini, 16-pin** | **ESP8266 ESP-12F** | **3.3 V** | **yes** | **LOLIN(WEMOS) D1 R2 & mini** | **chosen: radio bridge** |
| XIAO nRF52840 ×2 | nRF52840 (Cortex-M4F) | 3.3 V | **no — BLE/NFC only** | Seeed XIAO nRF52840 | house-temp candidate, §6 |
| Parallax Board of Education | see §6 | — | no | — | bench platform at best, §6 |
| Gemma M0 | ATSAMD21E18 | 3.3 V | no | Adafruit Gemma M0 | **no role here**, §6 |
| ADS1115 | 16-bit I2C ADC | — | — | — | see §5; a board is built for it, §7 |

`ESP8266MOD` is the silkscreen on the ESP-12E/F metal can, not a separate part.

The Uno R3's label is untested. Try an upload first; `stk500_getsync(): not in sync:
resp=0x00` is consistent with a missing bootloader — but equally with the wrong board or
port, so rule those out. If it really is gone, burn it with the **classic Nano** as ISP
(Arduino as ISP + six wires to the ICSP header). Not the Uno WiFi Rev2 — different core,
awkward ISP host.

## 2. RELAY STARTUP ORDER DIFFERS BY AVR FAMILY — the thing to get right

lessons.md #1 is specifically about the **ATmega4809**: `digitalWrite` before `pinMode`
does NOT pre-set the output latch there, *unlike classic AVR*. So:

- **megaAVR (4809: Uno WiFi Rev2, Nano Every)** — `pinMode(OUTPUT)` first, then an
  immediate `digitalWrite(HIGH)`. This is what `firmware/shared/safe_startup.h` does,
  and it is correct **for these chips only**.
- **Classic AVR (328P: Nano, Uno R3; 32U4: Yún)** — the opposite. `pinMode(OUTPUT)`
  first drives the pin LOW (the PORT bit powers up 0) = **relay CLOSED**. The safe idiom
  is `digitalWrite(HIGH)` FIRST, which pre-sets the latch (and meanwhile enables the
  pull-up), THEN `pinMode(OUTPUT)`.

**Do not lift `safe_startup.h` unchanged onto a 328P or 32U4 board.** It would open a
brief relay-closed window on exactly the chips the lesson's parenthetical exempts.

Correct on both families:

```c
digitalWrite(pin, RELAY_OPEN);   // classic AVR: pre-sets the latch (+ pull-up)
pinMode(pin, OUTPUT);
digitalWrite(pin, RELAY_OPEN);   // megaAVR: the one that actually takes
```

PROPOSED, NOT DONE: fold that three-line form into `safe_startup.h` so one helper is
correct everywhere. Not changed here because safe startup is a production-firmware
invariant and that edit should be made deliberately, not as a side effect of writing a
doc. The rig's external 10k pull-ups cover the window regardless — but the code should
not depend on them.

## 3. DECISION — the sensing node between Jackery and fridge

```
ACS712 + relay -> Nano Every -> 9600 baud SoftwareSerial -> D1 mini -> WiFi -> dual_logger
```

**Why the Nano Every for sensing.** It is the same ATmega4809 as the rig, so it is the
only board on the bench where the existing firmware is correct *as written* rather than
as translated: `safe_startup.h` applies unchanged, `pins.h` and the lesson #7 watchdog
composition are the same family, and code developed on the rig's board runs on it as-is.
It is 5 V, so the ACS712's 2.5 V zero is read ratiometrically against the same rail and
`current_sense.h`'s 2.3–2.7 V auto-zero window (lesson #4) is valid as written. And the
10-bit ADC is proven adequate for this exact measurement — every number in the dataset
came through it, resolving 0.12 A idle against 0.75 A running.

**Why the D1 mini for the radio.** It keeps the ESP32s free for the RTD nodes, and the
bridge job is small: read lines from serial, push over TCP, reconnect on drop. It is NOT
a port of `esp32_rtd_wifi_node`, which also does RTDs, a web page, LittleFS backup and an
OLED — none of which a bridge needs.

**Why this shape at all.** The Nano Every emits the same `t_ms,amps,note` lines the
Arduino produces today, so the measurement chain is byte-identical to the existing one
and `dual_logger`'s parser needs nothing new. Only the transport changes. New numbers are
directly comparable to old with no cross-calibration run — which is the whole reason to
stay on the ACS712 (see `docs/hardware.md`, Current sensors).

### Wiring specifics

- **Two-resistor divider on Nano Every TX → D1 mini RX.** ESP8266 inputs are not 5 V
  tolerant.
- **Use SoftwareSerial on spare pins (D5/D6), not the hardware UART.** On the D1 mini,
  GPIO1/GPIO3 are shared with the USB-serial converter, so the link would fight flashing
  and serial debugging. Same family of trap as lesson #6 (the D1/TX conflict that forced
  the rig's +1 pin shift).
- **Run the link at 9600 baud.** Payload is ~80 B/s, so there is enormous headroom, and
  slower bits buy noise margin for free — the same fix queued for the USB link in
  `docs/todo.md`, applied where it costs nothing.
- ACS712 breakout: buy the variant **with mounting holes** (`docs/hardware.md`).

## 4. Considered and rejected — do not re-litigate without new information

**Yún** — genuinely tempting: one board, 5 V AVR *and* WiFi, no divider, and its Linux
side could open a TCP socket in a few lines with networking outside the sampling loop.
Rejected on three unknowns against zero: it is discontinued with an old Linino/OpenWrt
image, the AVR↔Linux Bridge throughput is untested (fine at 1 Hz, questionable at the
10 Hz the current stream bursts to), and it has been in a box, so network setup is
unestimated. The Nano Every + D1 mini pairing has both halves already proven here.
Revisit only if the pairing disappoints.

**ESP8266 as the SENSING MCU** — rejected. It has exactly one analog input: no second
current channel, and no spare channel to sample the ACS712's 5 V rail for ratio
correction, so supply drift lands straight in the readings uncancellable. ADC is also
noisy and disturbed by WiFi activity. (In its favor, for the record: NodeMCU/D1 mini
divide A0 to 0–3.3 V, so a 2.5 V zero fits without extra parts, and 10 bits over 3.3 V
is *finer* per step than 10 bits over 5 V. Range was never the problem.)

**ESP32 + a divider on the ACS712 output** — rejected. A fixed divider breaks the
ratiometric cancellation the 5 V read gives for free, and `current_sense.h`'s absolute
auto-zero window would have to be re-derived. Also note: **on ESP32, ADC2 is unusable
while WiFi is active** — ADC1 pins only (GPIO 32–39).

This rejection is about a DIVIDER, and does not describe the assembled board in §7,
which has none — it reads the ACS712 through an ADS1115 instead.

**A metering smart plug** (watts/VA/PF over WiFi, no wiring) — not rejected, but it
answers a different question. Roughly 1 Hz, so duty cycle and energy yes, transients no,
and it is a different measurement chain from every existing number. Worth keeping in mind
if VA/PF for the fridge becomes the goal.

## 5. ADS1115 — good part, two specific limits

Best trick here would be **differential mode**: measure the ACS712 output against a
Vcc/2 reference derived from the sensor's own 5 V rail. The ACS712's zero *is* Vcc/2, so
differencing cancels supply drift in hardware and the PGA amplifies what is left. That is
electrically better than what the rig does.

- **860 SPS ceiling** — ~14 samples per 60 Hz cycle. Fine for a clean sine; the fridge's
  current is not one (BLDC inverter compressor, PF ~0.55, real harmonic content), and
  anything above ~430 Hz aliases into the RMS figure. Likely still adequate for duty
  cycle and energy, but it is a NEW chain and would need a cross-check against
  ACS712+Arduino before its numbers could join the dataset.
- **NOT usable for power factor.** The natural idea — sample voltage and current, compute
  real power — fails because the ADS1115 MULTIPLEXES its channels rather than sampling
  simultaneously. At 860 SPS the inter-channel gap is ~1.2 ms, about **25° of phase error
  at 60 Hz**. Fatal for PF. VA/PF stays a scope job, or a metering IC that samples both
  channels together.

Keep it for a future node where resolution matters more than continuity with existing
data. **That node already exists in hardware** — see §7.


## 6. The rest of the bench — where they do and don't fit

### XIAO nRF52840 (×2) — park them for HOUSE TEMPERATURE

**No WiFi.** The nRF52840 is BLE and NFC only, so these cannot serve as the radio half
of the sensing node. They are also 3.3 V; the SAADC can select VDD/4 as its reference,
which would normally restore ratiometric behaviour, but that does not help here because
the ACS712 needs its own 5 V rail — different rails, no cancellation.

**Where they genuinely fit:** the house-temperature channel that
`docs/todo.md`'s demand-aware dispatch section says the controller will need and that
does not exist yet. That sensor has to sit in living space, which is exactly where a wall
wart and a cable are unwelcome. Tiny, BLE, onboard battery charging — built for it.

The receiving end is half-there already: the Ubuntu box has a Bluetooth dongle attached
(`0a12:0001 Cambridge Silicon Radio`, seen 2026-09-12); **unconfirmed** whether that part
is BLE-capable or Bluetooth-only.

NOTE FOR THE SOCKET-INGEST WORK: a BLE source would be a second transport alongside TCP,
which `docs/dual_logger_socket_ingest.md` does not currently anticipate. Not a problem —
it would join the same merge on the same clock — but worth knowing before that code is
written.

### Parallax Board of Education — depends which one, neither is an MCU candidate

**OPEN: which version is it?**

- **Classic Board of Education** (BASIC Stamp 2 carrier) — out. The BS2 has no analog
  input at all, no WiFi, and PBASIC is interpreted at a few thousand instructions per
  second. Current sensing needs fast repeated sampling inside a ~100 ms RMS window; this
  is orders of magnitude short. Still usable as a powered breadboard with the Stamp
  module pulled.
- **BOE Shield for Arduino** — not an MCU, a carrier: breadboard, power and servo headers
  over an Uno-form-factor board. **Real value as the bench platform for building this
  node** — ACS712, relay module and the divider wired on the breadboard with the Uno R3
  underneath, before anything is committed to the Nano Every.

### Gemma M0 — no role here

Wearables board: three I/O pads, 3.3 V, no radio. Recorded so it is not reconsidered.

## 7. Assembled node — ESP32 + ACS712 + ADS1115 on perfboard

Recorded 2026-09-21 from Ron. **It was built before §1's bench sweep and that sweep
missed it**, which is why the ADS1115 reads as a loose part in §5.

**Populated:** ESP32-WROOM-32 with the 0.96" OLED, ACS712, Adafruit 4-channel
**BSS138** bi-directional level converter, 7805 regulator.
**Not populated:** the ADS1115 itself — confirmed 2026-09-21: it is sitting on the upper
board loose, neither fastened nor connected electrically.

**It is a TWO-BOARD STACK on standoffs**, not one perfboard: ADS1115 on the upper board,
ESP32 + OLED + ACS712 + 7805 on the lower, joined by header strips. The ACS712 is
already wired in-line through its green screw terminal with external strain-relief
clamps. Both perfboards carry printed coordinate grids (columns A–W, rows 04–19) — use
those coordinates to record a wiring map, which will outlast tracing wires from photos.
The level shifter **is installed**, socketed on the upper board (silkscreen "4
Bi-Directional / Level Shifter", pins `GND A1 A2 A3 A4`), sitting directly below where
the ADS1115's socket will go — check clearance before soldering that socket.

### Interconnect: Dupont jumpers, and what to do about them

The inter-board wiring is Dupont jumpers, which Ron flagged (2026-09-21) as working
against the reason for moving to perfboard at all — `docs/hardware.md` records the
breadboard RTD node at ~1–2 faults per thousands of samples, and crimped Dupont sockets
are the same CLASS of failure, usually at a lower rate.

Two of these connections are legitimately pluggable, so the answer is not "solder
everything":

- **The ESP32 must stay socketed.** `docs/hardware.md`: GPIO 2/12/15 are strapping pins
  AND are used by the RTD software SPI, so the module is pulled to flash and replugged
  to run.
- **Two boards on standoffs need some separability**, or neither can be serviced.

Sort the connections by **how a bad contact fails**, not by how many there are:

- **I²C (SDA/SCL) and ALRT fail LOUDLY** — a NACK, a failed `ads.begin()`, or interrupts
  that stop. You find out immediately.
- **The ACS712 analog output fails SILENTLY.** An intermittent there throws no error; it
  returns a WRONG NUMBER that looks like data. On a surge instrument that is precisely
  the reading you would quote.

**So if one thing changes, solder the ACS712 output and its ground reference.** Leave the
module sockets; consider latching JST for the board-to-board run (a JST is already in use
for the battery input).

Then settle it with data rather than argument, the way the breadboard node's
intermittency was quantified: assemble, run, wiggle the harness while logging, count
faults.

**CONFIDENCE: the board is not known to be finished.** Ron's recollection (2026-09-21)
is that this was built on a breadboard and was part-way through being moved to perfboard
when the work was interrupted — the same breadboard→perfboard motion `docs/hardware.md`
records for the RTD node. Nothing in the repo records either version, so the parts list
above is what is VISIBLE on the board, not a claim that the wiring is complete.
**Continuity-check every connection against the intended schematic before powering it**;
do not assume an absent connection is a design decision. The missing ADS1115 may be the
point at which the work stopped rather than the only thing outstanding.
**Supply as built:** 9 V battery → 7805 → 5 V.

**Board markings (Ron, 2026-09-21).** Module can: `ESP-32D` / `WiFi+BT` / `N4XX`.
Carrier PCB: **`HW-724`**, printed front and back. The can marking matches the module
already recorded in `docs/hardware.md` for the RTD node, so it is the same
WROOM-32D-class part — **N4 = 4 MB flash, no PSRAM**, which is what makes GPIO16 free
here (measured against the board, not inferred). `HW-724` is a generic carrier
designator with no findable public documentation (searched 2026-09-21), so identify this
board by the COMBINATION of can marking, `HW-724`, and its pin count. **The silkscreen
on the board is the authority for pin labels** — not any online pinout diagram for a
differently-named board.

### Wiring as recorded

- **MCU GPIO 5, 4 and 16 go to the 3.3 V side of the level shifter.** 5 = SDA and
  4 = SCL match the SSD1306 convention already in `docs/hardware.md`. **16 is the
  ADS1115's ALERT/RDY — CONFIRMED 2026-09-21** from Ron's own sketches, which declare
  `constexpr int READY_PIN = 16;` under the comment "Pin connected to the ALERT/RDY
  signal for new sample notification" (`continuous_ADS1115`,
  `running_statistics_socket_server_2`; see `docs/prior_art_sketches.md`). Use it: the
  conversion-ready interrupt paces sampling at the 860 SPS ceiling instead of polling
  for it, and working ISR code for it already exists.
- **GPIO16 is free on a WROOM-32** (no PSRAM — `docs/hardware.md` records these as
  marked `N4XX`, 4 MB flash) and the RTD sketch's pins (CS 2/15, DI 13, DO 12, CLK 14)
  do not touch it. **It is NOT free on a WROVER**, where GPIO16/17 serve PSRAM — do not
  port this pinout to one.
- **WHY THREE PINS GO TO THE SHIFTER — settled 2026-09-21 from photos of the board and
  of the ADS1115 module.** The module is the generic blue "16Bit I2C ADC+PGA" board (NOT
  Adafruit), carrying 10 kΩ (`103`) resistors on SCL, SDA, ADDR and **ALRT**. The
  ADS1115's ALERT/RDY is **open-drain**, so it needs that pull-up to function — and the
  pull-up goes to **VDD**. With the ADS1115 at 5 V, ALRT therefore idles at 5 V, which
  must not be fed to a 3.3 V ESP32 input. So the three shifted lines are **SDA (5),
  SCL (4) and ALRT (16)** — three channels of the four-channel BSS138 board. The design
  is coherent, and it confirms the intent of a **5 V** ADS1115: at 3.3 V none of the
  three would need shifting. ALERT/RDY being open-drain like I²C is also why a BSS138
  shifter suits all three lines.
- **Pull-up stacking, check when wiring.** The Adafruit shifter carries 10 kΩ on both
  sides, so the 5 V segment sees 10 k ∥ 10 k ≈ 5 kΩ — healthy. The 3.3 V segment is the
  one to watch: shifter, OLED module and ESP32 board pull-ups all land in parallel.
  Measure bus-to-3.3 V once assembled; a few kΩ is fine, near 1 kΩ and the bus cannot be
  pulled low cleanly.
- **Address: expect `0x48`** (ADDR through 10 kΩ, almost certainly to GND) — but confirm
  rather than assume. `i2c_scanner` (2024-12-16, `docs/prior_art_sketches.md`) reports
  the real address alongside the OLED's `0x3c`.
- **One I²C bus, two voltage domains:** OLED on the 3.3 V segment, ADS1115 on the 5 V
  segment, shifter bridging them. No address clash — SSD1306 `0x3c`, ADS1115 `0x48`
  by default.
- The shifter is the **Adafruit BSS138** 4-channel part, which is the I²C-appropriate
  kind: open-drain with pull-ups on both sides. A push-pull auto-direction shifter
  (TXB0104 class) would NOT be, on a bus that has its own pull-ups.

### What it means for the decisions above

- **§4 does not apply to it.** That rejection is about a fixed divider on the ACS712
  output. This board has no divider; the ADS1115 reads the sensor directly, which is
  the §5 differential-against-Vcc/2 arrangement — electrically better than what the rig
  does.
- **Powering the ADS1115 at 5 V is required, and is what the shifter exists for.** It
  also buys headroom: at 100 mV/A the ACS712 rides at 2.5 V and swings up, so a 5 V rail
  can follow a surge to ~25 A. Lesson #10 — the chest freezer's true inrush is
  UNMEASURED and likely well above the method-limited ~3.5 A figure — is exactly why
  that headroom should not be given away.
- **§5's two limits stand unchanged:** the 860 SPS ceiling (~14 samples per 60 Hz cycle;
  anything above ~430 Hz aliases into the RMS, and the fridge's current is not a clean
  sine at PF ~0.55), and **no power factor** (the ADS1115 multiplexes, ~1.2 ms apart,
  ~25° of phase error at 60 Hz). It is also a NEW chain and needs a cross-check against
  ACS712 + Arduino before its numbers can join the existing dataset.

### The supply is the weak point — fix before any capture

9 V → 7805 → 5 V drops 4 V across the regulator, so it dissipates roughly as much as it
delivers, and a 9 V alkaline holds only ~500 mAh. Against an ESP32 averaging well over
100 mA with WiFi up, that is a couple of hours and a warm regulator.

`docs/hardware.md` requires a **solid 1–2 A** supply for these nodes and records a
CONFIRMED case of a weak one corrupting MAX31865 reads, because WiFi-TX current spikes
brown out a marginal supply. Treat the 9 V battery as bench bring-up only; re-power from
a proper USB supply before trusting any measurement off this board.

### Bring-up checklist for this board

Staged deliberately: the digital path (VDD, GND, SCL, SDA, ADDR, ALRT) is wired before
the analog inputs, so a failure at this stage has exactly one place to be — the shifter,
its references, or a pull-up. Wire the analog side afterwards and a fault could be either
half.

**Arduino IDE: board `WEMOS LOLIN32`, upload speed 921600** (`docs/hardware.md`;
confirmed on a module with these exact markings). Lower the speed only as a fallback if
an upload fails.

Unlike the RTD node, this ESP32 probably does NOT need unseating to flash. That node is
pulled because GPIO 2/12/15 are strapping pins driven by its MAX31865 SPI. Here the bus
is GPIO 4 and 5 — also strapping pins, but held HIGH by the I²C pull-ups, the benign
state — and GPIO16 is not one. If an upload ever fails with a boot-mode error, suspect a
device holding SDA low at reset.

**Throughout: power down before seating or unseating anything.** `docs/hardware.md`
records that seating live once produced an ambiguous both-channels-zero fault on the RTD
node that cost an hour.

#### Phase A — power off, both modules out

- [ ] Common ground across both boards and all three sockets.
- [ ] 5 V rail → GND and 3V3 → GND read hundreds of ohms to kΩ. Near zero is a short.
- [ ] No continuity between 5 V and 3V3.
- [ ] **7805 orientation:** pin 1 = IN from the 9 V JST, pin 2 = GND, pin 3 = OUT to the
      5 V rail. Reversed in/out puts 9 V on everything.
- [ ] **THE CRITICAL ONE — shifter socket.** The socket pin meeting `LV` must trace to
      the ESP32's **3V3**; the one meeting `HV` to **5 V**. Transposed, the "3.3 V side"
      carries 5 V straight into GPIO 16/5/4. This is the only mistake on this board that
      kills the ESP32 instantly.
- [ ] **ADS1115 socket:** VDD pin → 5 V rail, GND pin → ground, socket order matching the
      module's `VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3`. Mark pin 1 on the board — a
      module seated backwards is the classic one-second kill.

#### Phase B — power on, modules still out

Use a bench or USB supply, **not the 9 V battery**.

- [ ] 5 V at the ADS1115's VDD position, 0 V at its GND position.
- [ ] **5 V at the shifter's HV position, 3.3 V at its LV position** — verified before the
      shifter goes near the socket.

#### Phase C — shifter in, ADC still out

- [ ] Power off, seat, power on.
- [ ] **GPIO 16, 5 and 4 read ~3.3 V**, pulled up through the shifter. **Reading 5 V on
      any of them → power off immediately**, HV and LV are transposed.
- [ ] HV-side channel pins read ~5 V.

#### Phase D — ADC in

- [ ] Power off, seat, power on.
- [ ] **Measure VDD right at the ADS1115, idle and with WiFi transmitting.** This is also
      the measurement that speaks to the 2.27 V zero (`docs/prior_art_sketches.md`): a
      sagging rail is the leading explanation, and catching it here is before it can
      contaminate anything.
- [ ] `i2c_scanner` (2024-12-16) reports **`0x3c` and `0x48`**. Both present means the two
      voltage domains share one working bus.
- [ ] `ads.begin()` succeeds.
- [ ] Tie **A0 to GND** temporarily and confirm a ~0 V reading — validates the conversion
      chain against a known input rather than floating noise.
- [ ] Flash `continuous_ADS1115` and confirm the ISR fires. ALERT/RDY only pulses on
      conversion-ready if the comparator threshold registers are set for it, which that
      sketch already does. This is the only way to verify the shifter's third channel.

**Failure signature worth knowing:** if SDA and SCL are crossed at the ESP32, the scan
finds NOTHING — not even the OLED at `0x3c` — because both devices share those pins. Fix
a crossed pair in the WIRING, not in `Wire.begin()`: a per-board software exception would
leave this node disagreeing with `docs/hardware.md` and every other node in the project.

#### Bring-up RESULTS — 2026-09-23

All digital checks passed; the analog inputs are still unwired.

| Check | Result |
|---|---|
| `i2c_scanner` | `0x3C` (OLED) **and** `0x48` (ADS1115) |
| ALRT → GPIO16 | interrupt fires; `continuous_ADS1115` prints |
| A0 tied to GND | 0.00 V |
| A0 tied to VDD, `GAIN_ONE` | 4.10 V — saturation, as expected |
| A0 tied to VDD, `GAIN_TWOTHIRDS` | **4.8 V** |
| Same point, meter | **4.81 V** |

**The I²C scan finding both addresses proves more than connectivity.** An ACK requires
the SLAVE to pull SDA low and that pull to return through the shifter, so channels 2 and
3 are verified **bidirectional**, not merely outbound. And `continuous_ADS1115` prints
only when its ISR sets `new_data`, so output at all is proof that channel 1 (ALRT) works.

**The ADS1115's internal reference is trustworthy** — 4.8 V measured against 4.81 V on
the meter, ~0.2%. That could not be assumed: this part is NOT ratiometric, so unlike the
rig's Arduino chain its accuracy rests entirely on that reference.

Note what the saturation test did NOT prove. An over-range input pins the code at full
scale and `computeVolts()` multiplies by the FSR constant, so 4.10 V appears whether or
not the reference is accurate. It confirmed the FSR constant only. The meter did the rest.

#### CONSEQUENCE: the rail is 4.81 V, so the zero is 2.405 V

- **Expected ACS712 zero = Vcc/2 = 2.405 V**, not 2.5 V.
- **Hard-coding 2.5 V costs ~0.95 A of systematic offset** — larger than the ~0.7 A
  running current it would be measuring. Every prior sketch does exactly this.
- **2.405 V passes** the 2.3–2.7 V auto-zero window in `firmware/shared/current_sense.h`.
  The 2.27 V implied by the 2025 capture would have been rejected.
- This CORROBORATES rather than contradicts that old capture: 2.27 V implied a ~4.54 V
  rail on the breadboard build, this one measures 4.81 V. Different build, different
  drop, same underlying fact — **the rail is not 5.00 V and 2.5 V is the wrong
  constant on this hardware.** Take the zero from a live measurement; `RunningStatistics`
  `mean()` already computes it.

**OPEN: which supply was this measured on** — the 7805, or the ESP32 board's `5V` pin fed
from USB? Both land near 4.8 V for different reasons (7805 tolerance is ~±4–5%; the dev
board's USB rail loses ~0.2 V across a series diode). They will NOT match in service,
since the deployed board runs on the 7805. Another argument for measuring the zero at
runtime rather than trusting any constant.
