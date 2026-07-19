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
ESP32 + 2× Adafruit MAX31865 + **PT1000** RTDs, on a breadboard (intermittent —
needs eventual rebuild onto soldered protoboard, but usable; ~1–2 faults per
thousands of samples). Both this and the Arduino plug into one Ubuntu laptop.

## Power source / policy
Nissan Leaf 12V → Renogy 1000W inverter. Leaf DC-DC converter ceils ~1.0–1.2 kW,
so the system enforces **one-load-at-a-time** rotation: only one compressor can
draw a start surge at a time.
