#ifndef PINS_H
#define PINS_H
// Single source of truth for the relay/sensor pin map and channel count.
// Every sketch #includes this. Do NOT hand-edit channel bounds elsewhere
// (lesson #5: a stray < 4 vs < 5 caused an array overrun).

// Board: Arduino Uno WiFi Rev2 (ATmega4809 / megaAVR). FQBN arduino:megaavr:uno2018.

const uint8_t NUM_CHANNELS = 4;

// Relay INPUT pins. ACTIVE-LOW: pin LOW = relay CLOSED, HIGH = open.
// +1 shift off D1 avoids the hardware TX conflict (lesson #6).
// D2->IN1/Ch1, D3->IN2/Ch2, D4->IN3/Ch3, D5->IN4/Ch4(spare).
const uint8_t RELAY_PIN[NUM_CHANNELS] = {2, 3, 4, 5};

// Current-sense pins (ACS712-20A: 2.5V zero offset, 100mV/A, ratiometric).
// A1=Ch1, A2=Ch2, A3=Ch3, A4=Ch4.
const uint8_t SENSE_PIN[NUM_CHANNELS] = {A1, A2, A3, A4};

// Relay logic levels, named so intent is unambiguous at call sites.
const uint8_t RELAY_CLOSED = LOW;
const uint8_t RELAY_OPEN   = HIGH;

// 0-indexed array position vs 1-indexed physical channel label is a recurring
// snare -- Ch1 is index 0. State both when it matters.

#endif // PINS_H
