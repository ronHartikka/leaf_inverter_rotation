// PLACEHOLDER for the FINAL load-rotation firmware -- to be built here in Claude Code.
// Foundation is ready (see ../../README.md and docs/): confirmed pin map, active-LOW,
// megaAVR safe-startup, per-channel min-off surviving resets, overcurrent latch-off,
// auto-zero sanity, NUM_CHANNELS bounds, watchdog + non-blocking millis(), WiFiNINA
// telemetry, per-load control constants from loads/*.json.
//
// Build only after the kitchen fridge (and a replacement freezer) are characterized,
// since the control constants come from those JSONs.
#include "../shared/pins.h"
#include "../shared/safe_startup.h"
#include "../shared/current_sense.h"

void setup() {
  relaysSafeStartup();   // lesson #1: first thing, always
  // TODO: watchdog enable, WiFiNINA, load config from per-load constants
}

void loop() {
  // TODO: non-blocking millis() rotation state machine; one wdt_reset at top
}
