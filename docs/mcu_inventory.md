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
| ADS1115 | 16-bit I2C ADC | — | — | — | see §5 |

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
data.
