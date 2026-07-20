/*
  characterize_load.ino — single-load current profiler
  Board: Arduino Uno WiFi Rev 2 (arduino:megaavr:uno2018)

  Purpose: hold ONE relay closed and stream RMS current as CSV so you
  can see a load's full start -> run -> stop signature and read off the
  control-logic constants:
      START_CONFIRM_A   (running-current threshold)
      MIN_OFFER_MS      (shortest offer that permits a valid decision)
      START_DEBOUNCE_MS (sustained-above time to latch "running")
      STOP_A            (stopped-current threshold)
      STOP_DEBOUNCE_MS  (sustained-below time to latch "done")
  ( MAX_OFFER_MS is a patience policy, set by judgment from the curve. )

  This sketch does NOT rotate. It closes one channel and holds it,
  sampling fast enough to show the PTC-start hump on an induction
  compressor. Open the relay by pressing reset, or set HOLD_MS to auto-stop.

  Relays: SainSmart 4-ch, ACTIVE-LOW (pin LOW = relay closed).
  megaAVR note: digitalWrite before pinMode does NOT pre-set the output
  latch (unlike classic AVR); the latch powers up 0, so pinMode(OUTPUT)
  alone drives LOW = relay closed. Therefore pinMode first, then HIGH.
  10k pull-ups on the IN lines cover the float window before setup runs.

  Sensors: ACS712-20A, ratiometric, ~100 mV/A, auto-zeroed at startup.
*/

// ---------- Configuration ----------
const uint8_t  RELAY_PIN[4] = {2, 3, 4, 5};
const uint8_t  SENSE_PIN[4] = {A1, A2, A3, A4};
const char*    CH_NAME[4]   = {"Freezer", "Furnace", "Fridge", "Spare"};

// Which channel to characterize (0-3). Put the dorm fridge here.
const uint8_t  TARGET_CH    = 3;          // 3 = Spare socket

// Report cadence and optional auto-stop.
const unsigned long REPORT_MS = 250UL;    // CSV row every 250 ms
const unsigned long HOLD_MS   = 0UL;      // 0 = hold until reset; else auto-open after this many ms

// A little extra startup detail: for the first BURST_MS, report every
// BURST_REPORT_MS so the inrush/PTC hump is well sampled.
const unsigned long BURST_MS        = 8000UL;   // first 8 s = high-rate
const unsigned long BURST_REPORT_MS = 100UL;    // 100 ms rows during burst

// Startup hold-off / PTC cooldown: after ANY reset (USB connect, upload,
// power-up, brownout), keep ALL relays open this long before zeroing and
// closing the target. This is the compressor-safety interval, NOT just
// plug-in time: a PTC-start compressor that was running moments ago has a
// HOT PTC, and re-energizing it within ~2-3 min stalls it (observed: a
// sub-second reset blip stalled this fridge to ~1.9 A and 160-170 F).
// 180 s (3 min) lets the PTC fully cool and reset before power is reoffered.
// The production firmware must enforce the same min-off per channel on every
// re-energization, surviving resets.
const unsigned long STARTUP_HOLDOFF_MS = 180000UL;  // 180 s = 3 min PTC cooldown

// Overcurrent cutoff: if current stays above OVERCURRENT_A continuously for
// OVERCURRENT_MS, open the relay (protect the inverter / catch a hard stall).
// The duration must exceed a healthy start's brief inrush (a second or two)
// so it never false-trips on startup; 20 s is well clear.
//
// THRESHOLD RESCALE [2026-07-20, kitchen fridge LG LTCS20020].
// The old 1.5 A value was scaled for the ~0.67 A dorm-fridge/chest-freezer
// class. It FALSE-TRIPPED this fridge overnight: at ~8 h accumulated compressor
// run-time (right at the manual's 7 h defrost floor) the draw stepped from
// ~0.75 A to ~2.4 A and settled to a flat ~1.9 A for >20 s, crossing 1.5 A and
// latching the fridge OFF for ~7 h. That was a NORMAL DEFROST cycle: the fridge's
// interior nameplate reads "Defrosting input: 198 W" (~1.7 A @ 115 V), which
// matches the flat ~1.9 A; the ~2.4 A entry step is the compressor (~0.75 A)
// briefly overlapping the energizing heater. (An earlier note here guessed a
// 52 W / 0.45 A heater from the service manual and mis-read the flat draw as
// inverter-drive current-limiting; the 198 W nameplate corrects that.)
// Defrost is a KNOWN, RECURRING ~1.9 A load (every 7-50 compressor run-hours),
// so the trip MUST sit above it. 3.0 A clears it with margin while still catching
// a genuine hard stall (locked-rotor current is much higher).
// Do NOT reuse 1.5 A for this load. See docs/todo.md P0 (confirmed root cause).
const float         OVERCURRENT_A   = 3.0;      // trip threshold (A) — rescaled
const unsigned long OVERCURRENT_MS  = 20000UL;  // sustained-over time to trip

// After an overcurrent trip: instead of latching off silently FOREVER (the old
// behavior — it left the fridge dead and unannounced for 7 h overnight), open
// the relay, wait out the compressor min-off (STARTUP_HOLDOFF_MS, so we never
// hot-restart inside the PTC window, lessons.md #2), then AUTO-RETRY. A one-off
// / false trip self-heals. A genuinely persistent fault keeps re-tripping; after
// MAX_TRIPS give up and latch open, but keep printing a LOUD repeating alarm so
// the condition is visible to a human / the logger rather than silent.
const uint8_t       MAX_TRIPS       = 10;       // retries before final latch+alarm
// -----------------------------------

float zeroOffset[4];
uint8_t tripCount = 0;          // overcurrent trips so far this run

float readRmsAmps(uint8_t ch) {
  const unsigned long WINDOW_US = 83333UL;   // ~5 cycles at 60 Hz
  unsigned long t0 = micros();
  double sumSq = 0;
  unsigned long n = 0;
  while (micros() - t0 < WINDOW_US) {
    float v = analogRead(SENSE_PIN[ch]) * (5.0 / 1023.0);
    float a = (v - zeroOffset[ch]) / 0.100;   // 100 mV/A
    sumSq += (double)a * a;
    n++;
  }
  return sqrt(sumSq / n);
}

void allRelaysOpen() {
  for (uint8_t i = 0; i < 4; i++) digitalWrite(RELAY_PIN[i], HIGH);
}

// Blocking min-off cooldown with a once-per-second countdown, logging the
// (now open-relay) current so the decay is captured and the wait looks alive.
// Mirrors the startup hold-off idiom. Relay stays OPEN throughout.
void cooldownHoldoff(unsigned long ms) {
  unsigned long h0 = millis();
  unsigned long lastTick = 0;
  while (millis() - h0 < ms) {
    unsigned long remain = (ms - (millis() - h0)) / 1000UL;
    if (remain != lastTick) {
      lastTick = remain;
      float a = readRmsAmps(TARGET_CH);
      Serial.print(F("# cooldown "));
      Serial.print((remain + 1) / 60);
      Serial.print(F(":"));
      unsigned long secs = (remain + 1) % 60;
      if (secs < 10) Serial.print(F("0"));
      Serial.print(secs);
      Serial.print(F(" remaining, amps="));
      Serial.println(a, 3);
    }
  }
}

void setup() {
  // Safe state FIRST (see megaAVR note above): pinMode, then HIGH.
  for (uint8_t i = 0; i < 4; i++) {
    pinMode(RELAY_PIN[i], OUTPUT);
    digitalWrite(RELAY_PIN[i], HIGH);        // HIGH = open
  }
  Serial.begin(115200);
  delay(500);
  Serial.println(F("\n=== characterize_load: single-load current profiler ==="));
  Serial.print(F("Target channel: "));
  Serial.print(TARGET_CH);
  Serial.print(F(" ("));
  Serial.print(CH_NAME[TARGET_CH]);
  Serial.println(F(")"));

  // Startup hold-off / PTC cooldown: relays stay OPEN the whole time.
  Serial.print(F("All relays OPEN. PTC cooldown / plug-in window: holding "));
  Serial.print(STARTUP_HOLDOFF_MS / 1000);
  Serial.println(F(" s before start (compressor safety — do not shorten for compressor loads)..."));
  {
    unsigned long h0 = millis();
    unsigned long lastTick = 0;
    while (millis() - h0 < STARTUP_HOLDOFF_MS) {
      // print remaining time once per second (mm:ss) so the long wait
      // is visibly alive rather than looking like a hang
      unsigned long remain = (STARTUP_HOLDOFF_MS - (millis() - h0)) / 1000UL;
      if (remain != lastTick) {
        lastTick = remain;
        Serial.print(F("  "));
        Serial.print((remain + 1) / 60);        // minutes
        Serial.print(F(":"));
        unsigned long secs = (remain + 1) % 60;
        if (secs < 10) Serial.print(F("0"));
        Serial.print(secs);
        Serial.println(F(" remaining..."));
      }
    }
  }

  // Auto-zero all sensors with everything open.
  Serial.println(F("Zeroing sensors (all relays open)..."));
  bool zeroOK = true;
  for (uint8_t i = 0; i < 4; i++) {
    long acc = 0;
    for (int k = 0; k < 200; k++) acc += analogRead(SENSE_PIN[i]);
    zeroOffset[i] = (acc / 200.0) * (5.0 / 1023.0);
    Serial.print(F("  "));
    Serial.print(CH_NAME[i]);
    Serial.print(F(" offset = "));
    Serial.print(zeroOffset[i], 3);
    Serial.print(F(" V"));
    if (zeroOffset[i] < 2.3 || zeroOffset[i] > 2.7) {
      Serial.print(F("  <-- OUT OF RANGE (sensor unpowered/miswired?)"));
      zeroOK = false;
    }
    Serial.println();
  }
  if (!zeroOK) {
    Serial.println(F("ABORT: a sensor offset is out of the 2.3-2.7 V window."));
    Serial.println(F("Fix wiring and reset. Relays left open."));
    while (true) { /* halt, relays open */ }
  }

  Serial.println(F("\nClosing target relay. CSV columns:"));
  Serial.println(F("t_ms,amps,note"));

  // Close only the target channel.
  digitalWrite(RELAY_PIN[TARGET_CH], LOW);
}

unsigned long tStart = 0;
unsigned long lastReport = 0;
bool started = false;
unsigned long overStart = 0;   // 0 = not currently over OVERCURRENT_A

void loop() {
  if (tStart == 0) tStart = millis();
  unsigned long now = millis();
  unsigned long elapsed = now - tStart;

  unsigned long interval = (elapsed < BURST_MS) ? BURST_REPORT_MS : REPORT_MS;

  if (now - lastReport >= interval) {
    lastReport = now;
    float a = readRmsAmps(TARGET_CH);
    Serial.print(elapsed);
    Serial.print(F(","));
    Serial.print(a, 3);
    // light annotations to make the curve easy to read by eye
    Serial.print(F(","));
    if (elapsed < BURST_MS) Serial.print(F("burst"));
    Serial.println();

    // --- Overcurrent watchdog (uses the same reading) ---
    // Track continuous time above OVERCURRENT_A; reset the instant it
    // drops back below, so only a sustained stall accumulates the full
    // OVERCURRENT_MS. A healthy start's brief inrush never gets there.
    if (a > OVERCURRENT_A) {
      if (overStart == 0) overStart = now;
      else if (now - overStart >= OVERCURRENT_MS) {
        // TRIP: open the relay immediately (safe), then auto-retry after the
        // compressor min-off rather than latching off silently forever.
        digitalWrite(RELAY_PIN[TARGET_CH], HIGH);   // OPEN — safe
        tripCount++;
        Serial.print(F("# OVERCURRENT: >"));
        Serial.print(OVERCURRENT_A, 1);
        Serial.print(F("A for >"));
        Serial.print(OVERCURRENT_MS / 1000);
        Serial.print(F("s — relay opened (trip "));
        Serial.print(tripCount);
        Serial.print(F(" of "));
        Serial.print(MAX_TRIPS);
        Serial.println(F(")."));

        if (tripCount >= MAX_TRIPS) {
          // Persistent fault: stop re-energizing (don't hammer a real stall),
          // latch open — but ALARM loudly and repeatedly, never silent.
          while (true) {
            digitalWrite(RELAY_PIN[TARGET_CH], HIGH);
            Serial.print(F("# ALARM: overcurrent latched after "));
            Serial.print(tripCount);
            Serial.println(F(" trips — load OFF, needs attention. (reset to clear)"));
            delay(5000);
          }
        }

        // Wait out the compressor min-off (same 3 min PTC window), then retry.
        Serial.print(F("# cooling down "));
        Serial.print(STARTUP_HOLDOFF_MS / 1000);
        Serial.println(F(" s (compressor min-off) before auto-retry..."));
        cooldownHoldoff(STARTUP_HOLDOFF_MS);

        digitalWrite(RELAY_PIN[TARGET_CH], LOW);     // re-close — resume
        overStart = 0;                               // reset the over-timer
        lastReport = millis();                       // avoid an immediate re-report
        Serial.println(F("# retry: relay reclosed, resuming (20 s inrush grace applies)."));
      }
    } else {
      overStart = 0;   // dropped below threshold — reset the timer
    }
  }

  // Optional auto-stop.
  if (HOLD_MS > 0 && elapsed >= HOLD_MS) {
    digitalWrite(RELAY_PIN[TARGET_CH], HIGH);   // open
    Serial.print(F("# HOLD_MS reached ("));
    Serial.print(HOLD_MS);
    Serial.println(F(" ms) — relay opened. Continuing to log decay."));
    // keep logging so you can see the current collapse, but don't re-open logic
    // stay here forever logging at REPORT_MS
    unsigned long decayLast = millis();
    while (true) {
      if (millis() - decayLast >= REPORT_MS) {
        decayLast = millis();
        float a = readRmsAmps(TARGET_CH);
        Serial.print(millis() - tStart);
        Serial.print(F(","));
        Serial.print(a, 3);
        Serial.println(F(",decay"));
      }
    }
  }
}
