/*
 * esp32_rtd_wifi_test.ino -- TEMPORARY networking test (throwaway, not the prod node).
 *
 * Same 2x PT1000 read as esp32_rtd_serial_check, but instead of only USB serial it
 * opens a TCP socket to a host and streams the same "Resistance{n} = " lines. For a
 * quick test we point it at THIS MAC (192.168.1.243), not ubuntu. It also echoes
 * everything to USB serial, so you can watch progress on the Serial Monitor @115200.
 *
 * ===== SET BEFORE UPLOAD =====
 *   WIFI_SSID / WIFI_PASS : your 2.4 GHz network (same one the Mac is on)
 *   HOST                  : the Mac's LAN IP (prefilled; re-check if it changes)
 * The ESP32 and the Mac must be on the same 192.168.1.x network.
 */
#include <WiFi.h>
#include <Adafruit_MAX31865.h>

#include "../shared/wifi_secrets.h"   // WIFI_SSID / WIFI_PASS -- git-ignored, see wifi_secrets_example.h

// ---- CONFIG ----
const char*    HOST      = "192.168.1.243";    // the listener host's LAN IP (re-check if it changes)
const uint16_t PORT      = 9000;

// RTDs wired on the perfboard to software SPI: CS 15 & 2, DI 13, DO 12, CLK 14.
// GPIO 2/12/15 are boot-strap pins, but the ESP32 is SOCKETED -- pull the module to
// flash it (disconnected from the RTD lines), plug it back in to run. That sidesteps
// the strapping conflict without moving these soldered pins.
Adafruit_MAX31865 thermo1 = Adafruit_MAX31865(15, 13, 12, 14);
Adafruit_MAX31865 thermo2 = Adafruit_MAX31865(2, 13, 12, 14);
#define RREF      4300.0
#define RNOMINAL  1000.0

WiFiClient client;
unsigned long lastSend = 0, lastTry = 0;

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);        // strongest AP, not first seen (docs §1)
  WiFi.setSortMethod(WIFI_CONNECT_AP_BY_SIGNAL);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("# WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.print("\n# WiFi up: IP="); Serial.print(WiFi.localIP());
  Serial.print(" BSSID=");          Serial.print(WiFi.BSSIDstr());
  Serial.print(" RSSI=");           Serial.println(WiFi.RSSI());
}

void emit(const String& s) {
  Serial.print(s);                          // echo to USB for debugging
  if (client.connected()) client.print(s);  // and out the socket
}

void setup() {
  Serial.begin(115200); delay(200);
  thermo1.begin(MAX31865_3WIRE);
  thermo2.begin(MAX31865_3WIRE);
  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();

  if (!client.connected() && millis() - lastTry > 3000) {   // (re)connect the socket
    lastTry = millis();
    Serial.print("# TCP connect "); Serial.print(HOST); Serial.print(":"); Serial.println(PORT);
    if (client.connect(HOST, PORT)) Serial.println("# TCP connected");
  }

  if (millis() - lastSend >= 1000) {                        // one reading/sec (= heartbeat)
    lastSend = millis();
    float o1 = RREF * (thermo1.readRTD() / 32768.0);
    float o2 = RREF * (thermo2.readRTD() / 32768.0);
    float t1 = thermo1.temperature(RNOMINAL, RREF) * 1.8 + 32.0;
    float t2 = thermo2.temperature(RNOMINAL, RREF) * 1.8 + 32.0;
    emit("Resistance1 = "  + String(o1, 4) + "\n");
    emit("Resistance2 = "  + String(o2, 4) + "\n");
    emit("Temperature1 = " + String(t1, 4) + "\n");
    emit("Temperature2 = " + String(t2, 4) + "\n");
    emit("\n");
  }
}
