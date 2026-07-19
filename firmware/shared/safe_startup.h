#ifndef SAFE_STARTUP_H
#define SAFE_STARTUP_H
#include "pins.h"
// megaAVR pinMode trap (lesson #1): on ATmega4809, digitalWrite BEFORE pinMode
// does NOT pre-set the output latch (unlike classic AVR). The latch powers up 0,
// so pinMode(OUTPUT) alone drives the pin LOW = relay CLOSED = all relays energized
// at boot. FIX: pinMode first, then IMMEDIATE digitalWrite HIGH, per pin.
//
// Call relaysSafeStartup() at the very top of setup(), before anything else.
// Lands every reset in all-relays-open, which composes with pull-ups (float-safe
// during the reset/bootloader window) and the watchdog (hangs -> resets -> safe).

inline void relaysSafeStartup() {
  for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
    pinMode(RELAY_PIN[i], OUTPUT);          // drives LOW on megaAVR -- danger window
    digitalWrite(RELAY_PIN[i], RELAY_OPEN); // immediately force open (HIGH)
  }
}

#endif // SAFE_STARTUP_H
