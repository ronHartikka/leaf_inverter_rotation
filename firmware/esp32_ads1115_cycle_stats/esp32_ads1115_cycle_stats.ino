/*
 * esp32_ads1115_cycle_stats.ino
 *
 * One line of statistics per POWER-LINE CYCLE, from the ESP32 + ADS1115 + ACS712
 * perfboard node. Built to BOUND SURGES -- the chest freezer's inrush (lesson #10 says
 * it is unmeasured) and the furnace blower (every electrical value in
 * loads/furnace.json is estimated). See docs/mcu_inventory.md section 7.
 *
 * This is the architecture Ron's own Dec-2024/Jan-2025 notes set as the goal and that
 * the 2024-25 sketches never reached: "If 60 Hz sample, output stats for this 60 Hz
 * cycle, reset stats". The sketches that shipped instead averaged ~10 cycles into a
 * 167 ms window, which is exactly what HIDES a start transient. Per-cycle numbers give
 * the ENVELOPE of a surge, cycle by cycle.
 *
 * NOT production firmware. The CLAUDE.md watchdog/safe-startup rules govern
 * firmware/rotation_production/ and do not apply here. There are no relays on this
 * board. The loop is non-blocking anyway.
 *
 * NO WiFi, by decision (2026-09-25). This is a bench instrument used a few times, on a
 * lab supply, with a laptop present. Leaving the radio out also removes the one
 * untested risk on the board: burst-correlated supply movement, estimated at ~75 mA.
 * If WiFi is ever added, that estimate must be MEASURED before the numbers are trusted.
 *
 * HARDWARE (docs/mcu_inventory.md section 7)
 *   ESP32-WROOM-32 (board selection: WEMOS LOLIN32), OLED at I2C 0x3c.
 *   ADS1115 at 0x48, powered at 5 V, reached through a BSS138 level shifter:
 *     SDA -> GPIO 5, SCL -> GPIO 4, ALERT/RDY -> GPIO 16.
 *   ALERT/RDY is OPEN-DRAIN and needs the module's own pull-up -- which goes to VDD,
 *   so at 5 V it idles at 5 V and MUST pass through the shifter. That is why three
 *   lines are shifted, not two.
 *   ACS712-20A output -> AIN2; 1k/1k divider from the 7805's output -> AIN3 (0.1 uF to
 *   ground at the tap).
 */

#include <Adafruit_ADS1X15.h>

// ---------------------------------------------------------------- configuration ----

// US line frequency. Stated explicitly because it is a known trap: ACS712_Code_3.ino
// ships testFrequency = 50 (a European default) and Ron's notes flag it -- "Power line
// frequency (not in USA, though)". Any window computed off the wrong value is wrong.
static const float    LINE_HZ   = 60.0f;
static const uint32_t WINDOW_US = (uint32_t)(1000000.0f / LINE_HZ + 0.5f);   // 16667 us

// Pin carrying the ADS1115's ALERT/RDY conversion-ready signal.
constexpr int READY_PIN = 16;

// GAIN_TWO: +/-2.048 V full scale. Chosen because at the ACS712-20A's 100 mV/A that is
// +/-20.5 A -- matching the sensor's OWN span almost exactly, with no range wasted.
// Resolution 62.5 uV = 0.625 mA per bit.
//
// NOTE this only holds in DIFFERENTIAL mode, where the PGA sees just the difference. In
// SINGLE-ENDED mode the reading rides on the ~2.4 V zero, so GAIN_ONE would clip at
// about 16 A -- measured and confirmed on this board 2026-09-23.
static const float LSB_V = 2.048f / 32768.0f;

// ---- Calibration: reversal method, 2026-09-25, Vcc = 4.805 V --------------------
// Same current measured in BOTH directions at 2.00 A, which separates offset from
// sensitivity without relying on a separate zero reading:
//     offset      = (V+ + V-) / 2      = (214.17 - 188.02) / 2    = +13.08 mV
//     sensitivity = (V+ - V-) / (2*I)  = (214.17 + 188.02) / 4.00 = 100.55 mV/A
//
// CALIBRATED AT 2 A. Do not trust it far outside that: on a +/-20 A part, offset and
// nonlinearity are referred to FULL SCALE, so a fit anchored near zero mispredicted
// 2.00 A by 5.6%. Re-calibrate over the range actually used -- for surge work that is
// amps to tens of amps, not fractions.
static const float V_OFFSET_CAL = 0.01308f;   // volts, differential, at VCC_CAL
static const float SENS_CAL     = 0.10055f;   // volts per amp, at VCC_CAL
static const float VCC_CAL      = 4.805f;     // rail when the above were measured

// Measure the 7805's output and put it here. BOTH the offset and the sensitivity are
// RATIOMETRIC to Vcc -- the ACS712's zero is Vcc/2 and its volts-per-amp scales with
// the same rail. Differential-against-Vcc/2 cancels the ZERO's supply dependence but
// NOT the scale, which was confirmed by prediction: two identical 2.00 A runs differed
// by 0.76 mV, a rise to 4.83 V was predicted from that, and the meter then read 4.83.
// Correcting for it collapsed the difference to 0.13 mV.
static const float VCC_NOW = 4.805f;

Adafruit_ADS1115 ads;

// ---------------------------------------------------------------------- sampling ----

#ifndef IRAM_ATTR
#define IRAM_ATTR
#endif

volatile bool new_data = false;
void IRAM_ATTR NewDataReadyISR() { new_data = true; }

// Per-window accumulators. Kept in raw ADC counts and converted once per window: 14
// samples of 32767^2 overflows int32, hence int64 for the sum of squares.
static int32_t  n_samp  = 0;
static int32_t  sum_c   = 0;
static int64_t  sumsq_c = 0;
static int16_t  min_c   = 32767;
static int16_t  max_c   = -32768;
static uint32_t window_start_us = 0;

static void reset_window() {
  n_samp = 0; sum_c = 0; sumsq_c = 0;
  min_c = 32767; max_c = -32768;
}

void setup() {
  Wire.begin(5, 4);
  pinMode(READY_PIN, INPUT);
  Serial.begin(115200);
  delay(50);

  ads.setGain(GAIN_TWO);
  ads.setDataRate(RATE_ADS1115_860SPS);

  if (!ads.begin()) {
    Serial.println("# FAILED to initialize ADS1115 at 0x48");
    while (1) { delay(1000); }
  }

  // Falling edge on every completed conversion.
  attachInterrupt(digitalPinToInterrupt(READY_PIN), NewDataReadyISR, FALLING);
  ads.startADCReading(ADS1X15_REG_CONFIG_MUX_DIFF_2_3, /*continuous=*/true);

  // Banner states what the code ACTUALLY does. The Adafruit example this descends from
  // printed "differential reading from AIN0 (P) and AIN1 (N)" while configuring
  // single-ended channel 0, and carried a gain comment describing a different gain than
  // the line it sat on. Both were live traps in this collection.
  Serial.println("# esp32_ads1115_cycle_stats");
  Serial.printf("# ADS1115 differential AIN2-AIN3, GAIN_TWO (+/-2.048V), 860 SPS\n");
  Serial.printf("# window %u us (%.1f Hz), ~%.1f samples/cycle\n",
                WINDOW_US, LINE_HZ, 860.0f / LINE_HZ);
  Serial.printf("# cal: offset %.5f V, sens %.5f V/A at Vcc %.3f; Vcc now %.3f\n",
                V_OFFSET_CAL, SENS_CAL, VCC_CAL, VCC_NOW);
  Serial.println("t_ms,n,mean_v,dc_a,rms_a,pk_a");

  window_start_us = micros();
  reset_window();
}

void loop() {
  // Collect whatever conversions have completed. Non-blocking: never wait here.
  if (new_data) {
    new_data = false;
    int16_t c = ads.getLastConversionResults();
    n_samp++;
    sum_c   += c;
    sumsq_c += (int64_t)c * (int64_t)c;
    if (c < min_c) min_c = c;
    if (c > max_c) max_c = c;
  }

  uint32_t now_us = micros();
  if ((uint32_t)(now_us - window_start_us) < WINDOW_US) return;

  if (n_samp > 0) {
    const double mean_c = (double)sum_c / n_samp;

    // Variance about the MEAN. The mean is the live zero: over a whole cycle of AC the
    // average IS the offset, so nothing is hard-coded and supply drift self-corrects.
    // This is the same quantity RunningStatistics::sigma() computes, and the same one
    // every 2024-25 sketch calculated and then ignored in favour of a constant 2.5 V.
    //
    // For DC (a lab-supply calibration run) the roles swap: dc_a carries the current
    // and rms_a falls to ~0. Both cases are readable from the same three columns.
    double var_c = (double)sumsq_c / n_samp - mean_c * mean_c;
    if (var_c < 0) var_c = 0;                       // rounding can push it slightly negative
    const double rms_c = sqrt(var_c);
    const double pk_c  = fmax((double)max_c - mean_c, mean_c - (double)min_c);

    // Both constants ride on the rail, so one scale factor corrects both.
    const float scale  = VCC_NOW / VCC_CAL;
    const float offset = V_OFFSET_CAL * scale;
    const float sens   = SENS_CAL * scale;

    const float mean_v = (float)(mean_c * LSB_V);
    const float rms_a  = (float)(rms_c  * LSB_V) / sens;
    const float pk_a   = (float)(pk_c   * LSB_V) / sens;
    const float dc_a   = (mean_v - offset) / sens;

    // NOTE: do NOT sanity-check mean_v against the 2.3-2.7 V auto-zero window in
    // firmware/shared/current_sense.h (lesson #4). That window is for a SINGLE-ENDED
    // read of an ACS712 sitting at Vcc/2. Here the differential pair has already
    // subtracted Vcc/2, so a correct mean is near ZERO volts, not 2.4.
    Serial.printf("%lu,%ld,%.5f,%.4f,%.4f,%.4f\n",
                  (unsigned long)millis(), (long)n_samp, mean_v, dc_a, rms_a, pk_a);
  } else {
    Serial.printf("%lu,0,,,,\n", (unsigned long)millis());
  }

  // Advance by exactly one window so the cadence does not drift. If we have fallen
  // behind (a long print, a stall), resync to now and DROP the missed windows rather
  // than emitting a burst of stale ones.
  window_start_us += WINDOW_US;
  if ((uint32_t)(micros() - window_start_us) > WINDOW_US) window_start_us = micros();
  reset_window();
}

/*
 * ACCURACY, both acceptable for bounding an inrush and both worth stating:
 *
 *  - 860 SPS over a 60 Hz cycle is ~14.3 samples, so windows do not land on whole
 *    cycles. Per-cycle RMS therefore carries a few percent of ripple from incoherent
 *    sampling. Averaging several cycles removes it, at the cost of the envelope.
 *
 *  - The sampled peak is biased LOW by up to 2.5% (cos(pi/14.3)), because discrete
 *    samples can miss the true crest. A bound, not an error: the real peak is never
 *    below what pk_a reports.
 *
 *  - Neither of these is the limit lesson #10 describes. 860 SPS resolves the
 *    CYCLE-BY-CYCLE envelope of a start transient, which 10 Hz / 100 ms RMS cannot; it
 *    still cannot give a true instantaneous surge peak. That remains a scope job.
 */
