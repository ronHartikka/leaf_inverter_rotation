#ifndef CURRENT_SENSE_H
#define CURRENT_SENSE_H
#include "pins.h"
// ACS712-20A helpers: auto-zero with sanity guard (lesson #4), RMS read.
//
// PLACEHOLDER: paste the validated RMS-window read + auto-zero routine from
// characterize_load.ino here so all sketches share ONE implementation.
// Keep the sanity guard below -- it catches an unpowered/miswired sensor.

// Reject auto-zero offsets outside this window (volts). A stale/bad zero
// silently corrupts every current reading downstream.
const float ZERO_OFFSET_MIN_V = 2.3;
const float ZERO_OFFSET_MAX_V = 2.7;

inline bool zeroOffsetSane(float offset_v) {
  return offset_v >= ZERO_OFFSET_MIN_V && offset_v <= ZERO_OFFSET_MAX_V;
}

// TODO: float readOffsetVolts(uint8_t ch);
// TODO: float readRmsAmps(uint8_t ch, uint16_t window_ms);

#endif // CURRENT_SENSE_H
