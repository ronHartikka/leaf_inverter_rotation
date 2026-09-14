# Hardware — authoritative facts

## Board
Arduino Uno WiFi Rev 2 (ATmega4809 / megaAVR core). FQBN `arduino:megaavr:uno2018`.

## Relays
SainSmart 4-ch, **ACTIVE-LOW** (pin LOW = relay closed). Safe state = all pins HIGH
= all relays open.

Pin map (note the +1 shift off D1 to avoid the hardware-TX conflict):
- D2 → IN1 / Ch1
- D3 → IN2 / Ch2
- D4 → IN3 / Ch3
- D5 → IN4 / Ch4 (spare)

(Canonical in code: `firmware/shared/pins.h`.)

## Current sensors
ACS712-20A on A1–A4 (2.5V zero offset, 100 mV/A, ratiometric). A1=Ch1 … A4=Ch4.
Validated against clamp meter + resistive load.

## Pull-ups
10k on each relay IN line to Arduino 5V, on a soldered daughterboard plugged into
the D-1683 breakout header. Beep matrix verified (each D→5V ≈ 10k, D↔D ≈ 20k, no
direct shorts). Covers the reset/bootloader/upload float window.

## Power
USB brick (850 mA) → Arduino → 5V rail feeds relay-module VCC and sensor VCC.
Separate chassis 5V regulator feeds relay-coil JD-VCC only. Grounds common on a
terminal strip (opto-isolation jumper removed but VCC still Arduino-fed, so
isolation is nominal — fine). Chassis 5V-to-Arduino path retired; USB brick is the
deployment supply.

## Temperature rig
ESP32-WROOM-32 + 2× Adafruit MAX31865 + **PT1000** RTDs, on soldered perfboard.
(The original breadboard build was intermittent — ~1–2 faults per thousands of
samples — and was replaced; a second perfboard node was built 2026-09-14.)

**Arduino IDE board selection: `WEMOS LOLIN32`.** Confirmed working by Ron
2026-09-14 — flashed with that selection, node runs and answers to `cf.local`.
Module is an ESP32-WROOM-32 (HiLetGo via Amazon), marked `ESP32D` / `WiFi+BT`
`N4XX` (N4 = 4 MB flash). "ESP32 Dev Module" is the other generic candidate for a
plain WROOM-32, but LOLIN32 is what has actually been used and works — don't change
it without a reason.

**Upload speed: lower it.** 921600 failed with a flash-comm / serial-noise error;
lowering the upload speed and re-plugging USB fixed it (lab notebook 2026-08-01).

**Flashing:** GPIO 2/12/15 are ESP32 strapping pins AND are used by the RTD software
SPI, so the ESP32 is **socketed** — pull the module to flash, replug to run.
**Power down (unplug USB) before unseating or seating.** Seating live risks damage;
it once produced an ambiguous both-channels-zero fault that cost an hour
(2026-09-04).

**Pins:** RTD software SPI — CS **2** and **15**, DI 13, DO 12, CLK 14. (Which CS is
channel 1 differs between sketches — take it from the sketch you are flashing, not
from here.) OLED SSD1306 on I2C, addr `0x3c`, SDA 5, SCL 4 — independent of the SPI
pins.

**Supply must be solid, 1–2 A.** A cheap 500 mA USB adapter was CONFIRMED to corrupt
MAX31865 reads (one channel dead at −403 °F, touch-sensitive, cross-channel
interference) — it cleared instantly on laptop USB, so it was power, not wiring.
WiFi-TX current spikes brown out a marginal supply even though the board peaks under
1 A (lab notebook 2026-08-02).

**Both channels reading zero = a SHARED line, not the probes.** The CS lines are
separate, so one failed MAX31865 loses exactly one channel. Losing both points at
DI 13 / DO 12 / CLK 14 or the 3.3 V / GND feeding both boards. Check seating first —
a pin folded under instead of entering its hole is the classic cause.

The Arduino plugs into the Ubuntu laptop over USB. Temp nodes are moving to WiFi
(they answer to `<NODE_ID>.local`); see `docs/dual_logger_socket_ingest.md`.

## Power source / policy
Nissan Leaf 12V → Renogy 1000W inverter. Leaf DC-DC converter ceils ~1.0–1.2 kW,
so the system enforces **one-load-at-a-time** rotation: only one compressor can
draw a start surge at a time.
