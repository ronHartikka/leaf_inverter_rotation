/*
 * esp32_rtd_node.ino -- fridge temperature node for the FC 1->3 board substitution.
 *
 * One sketch that does everything the substitution needs:
 *   - reads 2x PT1000 (MAX31865, software SPI) and prints them over USB serial in the
 *     format tools/dual_logger.py ALREADY parses (keys on "Resistance{1,2} = ") -- so
 *     the logging chain is UNCHANGED; data path stays USB for now.
 *   - shows both temps on the OLED.
 *   - brings up WiFi with best-AP selection and reports the chosen AP (the "right AP?"
 *     check) + logs disconnects. WiFi here is connectivity-proving ONLY -- no TCP data
 *     send yet (that arrives with the dual_logger socket cutover later).
 *   - reads hardwired ID pins at boot. Only module now => ID 0; ready for the next one.
 *
 * WiFi is NON-BLOCKING: if it never associates, RTD-over-USB keeps working regardless.
 *
 * Wiring (perfboard; ESP32 is SOCKETED -- pull module to flash, replug to run, which
 * sidesteps the GPIO 2/12/15 boot-strap conflict):
 *   RTD SPI (software): CS1=15 CS2=2  DI/MOSI=13  DO/MISO=12  CLK=14   (PT1000, 3-wire)
 *   OLED (I2C):         addr 0x3c  SDA=5  SCL=4
 *   ID pins:            25,26,27  INPUT_PULLUP -- tie a pin to GND = 0, leave open = 1
 *                       (this first node: all open = ID 0)
 */
#include <WiFi.h>
#include <Adafruit_MAX31865.h>
#include "SSD1306.h"   // ThingPulse ESP8266/ESP32 OLED driver (as in esp32_rtd_display)

// ---- CONFIG: fill creds before upload; scrub back to placeholders before any commit ----
const char*   WIFI_SSID  = "YOUR_SSID";
const char*   WIFI_PASS  = "YOUR_PASSWORD";
const uint8_t ID_PINS[]  = {25, 26, 27};     // node ID: GND=0, open=1 (bit i = ID_PINS[i])
#define RREF      4300.0                       // 4300 = PT1000
#define RNOMINAL  1000.0                       // 1000 = PT1000
#define SAMPLE_MS 1000

// RTDs: software SPI on the perfboard pins (CS 15 & 2, shared DI13 / DO12 / CLK14)
// Co-located comparison 2026-08-02 showed the probes reversed vs the CSV convention:
// the FREEZER probe is on the CS-2 board, the FRESH probe on the CS-15 board. So map
// thermo1 (channel 1 = "Resistance1" -> dual_logger t1_freezer) to CS 2 = freezer, and
// thermo2 (channel 2 -> t2_fridge) to CS 15 = fresh. Keeps the logged columns correct.
Adafruit_MAX31865 thermo1 = Adafruit_MAX31865(2, 13, 12, 14);   // CS 2  -> FREEZER (ch 1)
Adafruit_MAX31865 thermo2 = Adafruit_MAX31865(15, 13, 12, 14);  // CS 15 -> FRESH   (ch 2)
SSD1306 display(0x3c, 5, 4);                   // OLED: addr, SDA, SCL

int nodeId = 0;
float lastT[2] = {0, 0};
unsigned long lastSample = 0;

int readNodeId() {
  int id = 0;
  for (unsigned i = 0; i < sizeof(ID_PINS); i++) pinMode(ID_PINS[i], INPUT_PULLUP);
  delay(5);
  for (unsigned i = 0; i < sizeof(ID_PINS); i++)
    id |= (digitalRead(ID_PINS[i]) ? 1 : 0) << i;   // open->pull-up->1, tied-to-GND->0
  return id;
}

void onWiFi(WiFiEvent_t e) {
  if (e == ARDUINO_EVENT_WIFI_STA_GOT_IP) {          // IP + BSSID + RSSI all valid now
    Serial.print("# WiFi up: node="); Serial.print(nodeId);
    Serial.print(" IP=");    Serial.print(WiFi.localIP());
    Serial.print(" BSSID="); Serial.print(WiFi.BSSIDstr());   // <-- confirm the RIGHT AP
    Serial.print(" RSSI=");  Serial.println(WiFi.RSSI());
  } else if (e == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    Serial.print("# WiFi DISCONNECT node="); Serial.print(nodeId);
    Serial.print(" ms="); Serial.println(millis());
    WiFi.reconnect();
  }
}

void reportChannel(int ch, Adafruit_MAX31865& t) {
  uint16_t raw = t.readRTD();
  float ratio  = raw / 32768.0;
  float ohms   = RREF * ratio;
  float tF     = t.temperature(RNOMINAL, RREF) * 1.8 + 32.0;
  lastT[ch - 1] = tF;
  Serial.print("RTD");         Serial.print(ch); Serial.print(" value: "); Serial.println(raw);
  Serial.print("Ratio");       Serial.print(ch); Serial.print(" = ");      Serial.println(ratio, 8);
  Serial.print("Resistance");  Serial.print(ch); Serial.print(" = ");      Serial.println(ohms, 8);
  Serial.print("Temperature"); Serial.print(ch); Serial.print(" = ");      Serial.println(tF, 4);
  uint8_t fault = t.readFault();
  if (fault) {
    Serial.print("Fault"); Serial.print(ch); Serial.print(" 0x"); Serial.println(fault, HEX);
    t.clearFault();
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  nodeId = readNodeId();

  thermo1.begin(MAX31865_3WIRE);
  thermo2.begin(MAX31865_3WIRE);

  display.init();
  display.setFont(ArialMT_Plain_24);   // (removed flipScreenVertically -- it was upside down)

  Serial.print("# esp32_rtd_node boot -- node ID="); Serial.println(nodeId);
  WiFi.onEvent(onWiFi);
  WiFi.mode(WIFI_STA);
  WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);          // strongest AP, not first (docs §1)
  WiFi.setSortMethod(WIFI_CONNECT_AP_BY_SIGNAL);
  WiFi.begin(WIFI_SSID, WIFI_PASS);                   // non-blocking; RTDs work regardless
}

// Draw one channel like "L -2.1 °F": a space where a minus would be (so + and -
// values line up in the sign column), and the degree symbol as a small ring (the
// stock ThingPulse font has no ° glyph, so we draw one).
void drawTemp(int y, const char* label, float t) {
  String num = (t < 0.0 ? String("") : String(" ")) + String(t, 1);  // space-for-minus
  String s = String(label) + " " + num + " ";
  display.drawString(0, y, s);
  int w = display.getStringWidth(s);
  display.drawCircle(w + 3, y + 4, 2);        // degree symbol
  display.drawString(w + 8, y, "F");
}

void loop() {
  if (millis() - lastSample < SAMPLE_MS) return;
  lastSample = millis();

  reportChannel(1, thermo1);
  reportChannel(2, thermo2);
  Serial.println();

  display.clear();
  display.setColor(WHITE);
  display.setFont(ArialMT_Plain_24);
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  drawTemp(0,  "R", lastT[0]);   // top: freezer (thermo1 = CS 2)  -- R = right amp
  drawTemp(34, "L", lastT[1]);   // bottom: fresh  (thermo2 = CS 15) -- L = left amp
  display.display();
}
