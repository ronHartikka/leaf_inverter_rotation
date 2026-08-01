/*
 * esp32_rtd_serial_check.ino -- STEP 1 of the WiFi sensor-node migration.
 *
 * Simplest useful thing: read the MAX31865 PT1000 RTDs on the NEW ESP32 board and
 * print them over USB serial, so we can confirm the sensors read sane values BEFORE
 * adding the current sensors ("amps") or WiFi. No display, no WiFi -- just read,
 * print, fault-check, repeat.
 *
 * Output format matches firmware/esp32_rtd_display so tools/dual_logger.py parses it
 * UNCHANGED (it keys on "Resistance{1,2} = "): plug the board into the laptop, point
 * dual_logger at the port, and it logs immediately.
 *
 * ================= SET THIS CONFIG TO MATCH THE NEW BOARD'S WIRING =================
 * These defaults are the OLD board's pins (software SPI: CS=15 & 2, DI=13, DO=12,
 * CLK=14). I do NOT know how the new board is wired -- confirm each line and edit:
 *   - NUM_RTDS + CS_PINS[]  : one chip-select GPIO per MAX31865 (list length == NUM_RTDS)
 *   - SPI_DI / SPI_DO / SPI_CLK : shared SDI(MOSI) / SDO(MISO) / SCK (software SPI)
 *   - RREF / RNOMINAL / WIRES  : 4300 / 1000 / 3-wire for our PT1000s
 * (GPIO 2 and 15 are ESP32 boot-strap pins; they work as CS on the WROOM-32 we use,
 *  but verify if this is a different ESP32 variant.)
 */
#include <Adafruit_MAX31865.h>

// ---- CONFIG: edit to match the new board ----
#define NUM_RTDS   2
const int CS_PINS[NUM_RTDS] = {15, 2};   // one CS GPIO per chip; length must == NUM_RTDS
#define SPI_DI     13                     // SDI / MOSI (shared across chips)
#define SPI_DO     12                     // SDO / MISO (shared)
#define SPI_CLK    14                     // SCK        (shared)
#define RREF       4300.0                 // 4300 for PT1000
#define RNOMINAL   1000.0                 // 1000 for PT1000
#define WIRES      MAX31865_3WIRE         // our RTDs are 3-wire
#define SAMPLE_MS  1000

Adafruit_MAX31865* rtd[NUM_RTDS];

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("# esp32_rtd_serial_check -- PT1000, software SPI, no wifi");
  for (int i = 0; i < NUM_RTDS; i++) {
    rtd[i] = new Adafruit_MAX31865(CS_PINS[i], SPI_DI, SPI_DO, SPI_CLK);
    rtd[i]->begin(WIRES);
  }
}

void loop() {
  for (int i = 0; i < NUM_RTDS; i++) {
    int ch = i + 1;                                    // 1-indexed to match our format
    uint16_t raw = rtd[i]->readRTD();
    float ratio = raw / 32768.0;
    float ohms  = RREF * ratio;
    float tF    = rtd[i]->temperature(RNOMINAL, RREF) * 1.8 + 32.0;

    Serial.print("RTD");         Serial.print(ch); Serial.print(" value: "); Serial.println(raw);
    Serial.print("Ratio");       Serial.print(ch); Serial.print(" = ");      Serial.println(ratio, 8);
    Serial.print("Resistance");  Serial.print(ch); Serial.print(" = ");      Serial.println(ohms, 8);
    Serial.print("Temperature"); Serial.print(ch); Serial.print(" = ");      Serial.println(tF, 4);

    uint8_t fault = rtd[i]->readFault();
    if (fault) {
      Serial.print("Fault"); Serial.print(ch); Serial.print(" 0x"); Serial.println(fault, HEX);
      if (fault & MAX31865_FAULT_HIGHTHRESH) Serial.println("  RTD High Threshold");
      if (fault & MAX31865_FAULT_LOWTHRESH)  Serial.println("  RTD Low Threshold");
      if (fault & MAX31865_FAULT_REFINLOW)   Serial.println("  REFIN- > 0.85 x Bias");
      if (fault & MAX31865_FAULT_REFINHIGH)  Serial.println("  REFIN- < 0.85 x Bias - FORCE- open");
      if (fault & MAX31865_FAULT_RTDINLOW)   Serial.println("  RTDIN- < 0.85 x Bias - FORCE- open");
      if (fault & MAX31865_FAULT_OVUV)       Serial.println("  Under/Over voltage");
      rtd[i]->clearFault();
    }
  }
  Serial.println();
  delay(SAMPLE_MS);
}
