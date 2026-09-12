/*
 * esp32_rtd_wifi_node.ino -- production RTD node: TCP push + phone-viewable page + local backup.
 *
 * ONE sketch, both nodes. They differ ONLY in the CONFIG block below (NODE_ID and the
 * two channel labels) -- same reasoning as the multi-load characterizer decision in
 * docs/todo.md: one config-driven sketch, not N copies that drift apart.
 *
 *   node "cf"     -> the two chest-freezer probes
 *   node "fridge" -> kitchen fridge FC (freezer compartment) + FFC (fresh food)
 *
 * Four outputs, so no single failure blinds you:
 *   1. USB SERIAL, 1 Hz, in the EXACT legacy wire format. THIS is what dual_logger.py
 *      consumes -- it opens serial ports only (serial.Serial, auto-detected by USB
 *      vendor id); it has NO socket input. So while the node is tethered, logging works
 *      exactly as before and lessons.md #8 holds (one logger, one machine, one clock).
 *   2. TCP push of the same lines, 1 Hz, to HOST:PORT. NOTE: NOTHING CONSUMES THIS YET.
 *      dual_logger cannot ingest it. To log wirelessly, one of these must happen first:
 *        (a) add a TCP input mode to dual_logger.py  <- cleanest; keeps one logger
 *        (b) bridge the socket to a pty (socat) so dual_logger sees a "serial port"
 *        (c) stay tethered for logging and treat WiFi as view-only
 *      Kept in place because it is the wire half of (a)/(b) and costs nothing idle.
 *   3. HTTP on port 80 -- phone-viewable live numbers with no laptop running. In an
 *      outage the laptop is a 20-45 W load you may not want on just to read temps.
 *        /          phone page, auto-refreshing
 *        /json      machine-readable current values
 *        /log       download the local CSV backup
 *        /log/clear erase it (confirm-guarded)
 *   4. LittleFS CSV at 1/min, rotating -- the backup. Survives router, laptop, and
 *      logger outages. ~2 weeks retention at the sizes below.
 *
 * (3) and (4) work today with no changes anywhere else. (2) is the open integration.
 *
 * WiFi reconnect is NON-BLOCKING, deliberately. The older sketches spin in
 * `while (WiFi.status() != WL_CONNECTED) delay(300)`, which wedges the whole loop when
 * the AP is down -- exactly when local logging and the phone page matter most.
 *
 * ===== HARDWARE QUIRK -- READ BEFORE FLASHING =====
 * RTDs are on software SPI: CS 15 & 2, DI 13, DO 12, CLK 14.
 * GPIO 2/12/15 are ESP32 boot-strap pins. The module is SOCKETED: PULL THE ESP32 to
 * flash it (disconnected from the RTD lines), then plug it back in to run. That
 * sidesteps the strapping conflict without moving these soldered pins.
 *
 * *** POWER DOWN BEFORE UNSEATING OR SEATING THE MODULE. ***
 * Unplug USB first, every time. Seating it live risks damage, because pins make contact
 * in an arbitrary order and IO lines can be driven before VCC/GND are established.
 * (2026-09-04: seated live during an outage; symptom was BOTH channels reading exactly
 * 0.0000 ohm / -403.6 F. That turned out to be a seating fault, not damage -- a full
 * power-down and careful reseat restored it -- but the risk is real and the failure is
 * ambiguous enough to cost an hour of diagnosis.)
 *
 * WHY BOTH CHANNELS ZERO = SPI, NOT PROBES: the CS lines are separate (2 and 15), so a
 * single failed MAX31865 loses ONE channel. Losing BOTH points at something shared --
 * DI 13, DO 12, CLK 14, or the 3.3 V / GND feeding both boards. Check seating first;
 * a pin folded under instead of entering its hole is the classic cause. If a reseat does
 * not fix it, suspect GPIO 12: it is both the shared DO/MISO line AND the flash-voltage
 * strapping pin, so damage there still boots cleanly but returns zeros forever. Software
 * SPI means DO can simply be moved to a free pin (25/26/27/32/33) to test that.
 *
 * ===== ALSO ON THIS BOARD =====
 * SSD1306 OLED on I2C: addr 0x3c, SDA 5, SCL 4. Independent of the RTD SPI pins.
 */
#include <WiFi.h>
#include <ESPmDNS.h>          // so the node answers to <NODE_ID>.local, not a DHCP lease
#include <WebServer.h>
#include <LittleFS.h>
#include <Adafruit_MAX31865.h>
#include "SSD1306.h"          // alias for SSD1306Wire.h -- same lib the display sketch uses
#include <time.h>

/* ===== L AND R: THE HARDWARE IDENTITY =====
 * The two RTD modules are LEFT and RIGHT -- their physical position on the board with the
 * display upright so it can be read. That is the naming used everywhere in this sketch.
 * L/R is the HARDWARE (which module); the *_LABEL config below is the DEPLOYMENT (what is
 * plugged into it). They are deliberately separate: the cf node uses the same two modules
 * for two chest-freezer probes.
 *
 *     L = CS 15        R = CS 2
 *
 * HOW THAT WAS ESTABLISHED (2026-09-04, no guessing):
 *   1. esp32_rtd_wifi_test was running; it declares thermo1 = CS 15, thermo2 = CS 2.
 *   2. It printed Temperature1 = 40.98 F (warm) and Temperature2 = 0.44 F (cold), while
 *      the kitchen fridge measured FFC 41 / FC 0.4 by hand the same minute.
 *      => CS 15 = FFC (fresh food), CS 2 = FC (freezer compartment).
 *   3. Ron: "the RTD module connected to the RTD in the FC is on the Right."
 *      => CS 2 = R, therefore CS 15 = L.
 *
 * ===== WHERE 1 AND 2 STILL SURVIVE, AND WHY =====
 * Only on the wire and in the logged CSV columns, because those are CONTRACTS, not names
 * we own. dual_logger.py parses Resistance1/Resistance2 POSITIONALLY and at line 355 binds
 *     t_frz, t_frsh = state["t1_f"], state["t2_f"]
 * i.e. WIRE CHANNEL 1 IS THE FREEZER. Its CSV header is
 *     t1_freezer_f,t2_fridge_f,res1_ohm,res2_ohm,fault,
 * and live_chart.py / free_cycle_scan.py / scrub_chart.py / analysis/characterize.py all
 * read those column names, as does every CSV already recorded. Renaming them is an atomic
 * change across all of those plus a decision about historical files -- NOT a side effect.
 *
 * CONSEQUENCE, and it crosses over, so read it twice:
 *     Resistance1 (wire "freezer") carries the R module (CS 2)
 *     Resistance2 (wire "fresh")   carries the L module (CS 15)
 * On the fridge node that is correct: the freezer probe really is on R. On the cf node both
 * probes are in one box, so the freezer/fresh sense of the wire names is meaningless there
 * and only the position matters -- L goes out as 2, R as 1, consistently.
 *
 * The three older sketches disagree with each other on this and two are swapped relative to
 * dual_logger: esp32_rtd_node has it right (its thermo1 = CS 2); esp32_rtd_wifi_test and
 * esp32_rtd_display both send the fresh probe as channel 1.
 */

// ================= CONFIG -- the only part that differs between nodes =================

// *** CHANGE ONE DIGIT ON THE NEXT LINE TO SWITCH NODES. Nothing else. ***
//
// Done with the preprocessor rather than by commenting out blocks of declarations. The
// IDE's block-comment toggle also flips the "// ---- heading ----" lines inside a block,
// which turns a comment into a syntax error and then cascades into "NODE_ID was not
// declared" at every use site -- eight errors whose real cause is one missing slash.
// (2026-09-10.) One digit cannot be half-changed, and a typo hits the #error below
// instead of producing a build that silently claims to be the wrong node.
//
// EXPECTED_AP is where this node SHOULD be, given where it physically lives. The page
// shows it green when it matches and red when it does not, so a silent failover to the
// wrong AP surfaces days later instead of never (esp32_wifi_production.md section 3: the
// ESP32 picks an AP at connect time and never roams back).

#define NODE_SELECT  2        // 1 = fridge (upstairs)   2 = cf (basement)

#if   NODE_SELECT == 1
  // ---- fridge node -- upstairs, kitchen fridge ----
  const char* NODE_ID     = "fridge";
  const char* L_LABEL     = "ffc";        // LEFT module  (CS 15) -> fresh food
  const char* R_LABEL     = "fc";         // RIGHT module (CS 2)  -> freezer compartment
  const char* EXPECTED_AP = "gateway";

#elif NODE_SELECT == 2
  // ---- cf node -- basement, chest freezer ----
  // L/R -> top/bottom established 2026-09-10 from two independent readings, R warmer both
  // times (-1.06/+0.68 and -1.18/+1.47). The top probe has read warmer in EVERY reading
  // since the probes were repositioned on 2026-09-04, with a ~2 F gap at this box
  // temperature. Gap widens when the box is warm, narrows when cold -- see
  // loads/chest_freezer.json identity.heat_rejection and docs/outage_procedures.md 4.2.
  const char* NODE_ID     = "cf";
  const char* L_LABEL     = "cf_bottom";  // LEFT module  (CS 15) -> low in the food mass
  const char* R_LABEL     = "cf_top";     // RIGHT module (CS 2)  -> near the lid
  const char* EXPECTED_AP = "buffalo";

#else
  #error "NODE_SELECT must be 1 (fridge) or 2 (cf)"
#endif

// Screen orientation. This is not cosmetic: L and R are DEFINED as the module positions
// seen with the display right side up, so if the screen is inverted the labels read
// backwards relative to the board. esp32_rtd_display.ino called flipScreenVertically()
// unconditionally; on this build that comes out upside down, so it is off by default.
// Flip this one flag if the board is ever remounted -- do not swap L/R to compensate.
const bool     DISPLAY_FLIP = false;

// TCP push to dual_logger: OFF, because nothing consumes it yet (header note 2) and it is
// not free to leave running. WiFiClient::connect() BLOCKS for the full TCP timeout, and
// with no listener the 3 s retry starved the main loop to about a THIRD of its rate --
// measured 2026-09-10 on the cf node: 41 samples and 1 persisted row in 122 s of uptime,
// where 1 Hz should give ~122 and 2. Turn this back on only together with a listener, and
// give connect() an explicit short timeout when you do.
const bool     TCP_PUSH  = false;

#include "../shared/wifi_secrets.h"   // WIFI_SSID / WIFI_PASS -- git-ignored, see wifi_secrets_example.h
const char*    HOST      = "192.168.1.243";    // dual_logger.py listener LAN IP
const uint16_t PORT      = 9000;
// ======================================================================================

#define RREF      4300.0        // 4300 = PT1000
#define RNOMINAL  1000.0        // 1000 = PT1000

const unsigned long SEND_MS    = 1000;      // TCP push + sample cadence (1 Hz)
const unsigned long PERSIST_MS = 60000;     // local CSV cadence (1/min)
const unsigned long WIFI_RETRY_MS = 10000;  // non-blocking reconnect interval

// The screen periodically shows the node's own address. This is the ONLY discovery method
// that needs no network at all -- it works when mDNS does not resolve, when the router's
// client list is a nuisance, and when you cannot remember which node is which. For a node
// living in the basement with no laptop attached, that matters more than it sounds.
const unsigned long IP_SHOW_EVERY_MS = 60000;   // how often to interrupt the temperatures
const unsigned long IP_SHOW_FOR_MS   = 4000;    // how long to hold the address on screen
const size_t  MAX_LOG_BYTES = 500000;       // rotate at 500 KB (~7.7 days at 1/min)
const char*   LOG_PATH = "/temps.csv";
const char*   LOG_OLD  = "/temps_old.csv";

// Software SPI: CS, DI, DO, CLK. Named by board position -- see the L/R block above.
Adafruit_MAX31865 thermoL = Adafruit_MAX31865(15, 13, 12, 14);   // LEFT  module, CS 15
Adafruit_MAX31865 thermoR = Adafruit_MAX31865(2,  13, 12, 14);   // RIGHT module, CS 2

// SSD1306 OLED on I2C, addr 0x3c, SDA 5, SCL 4 -- same wiring as esp32_rtd_display.ino.
// I2C pins are independent of the RTD software-SPI pins, so the two coexist.
SSD1306 display(0x3c, 5, 4);
bool displayReady = false;

WebServer server(80);
WiFiClient client;

unsigned long lastSend = 0, lastTry = 0, lastPersist = 0, lastWifiTry = 0;
unsigned long lastIpShow = 0, ipShowStart = 0;
bool   showingIp = false, mdnsUp = false;
uint8_t wifiAttempt = 0;      // pinned-connect attempts since the last successful join
bool   fsReady = false, timeSynced = false;
float  tLF = NAN, tRF = NAN, ohmsL = 0, ohmsR = 0;
uint8_t faultL = 0, faultR = 0;
uint32_t sampleCount = 0, persistCount = 0, disconnectCount = 0;

// ---------- time ----------
// NTP only works while the network is up. Records written before first sync carry
// epoch 0; millis() is always present so unsynced spans stay orderable. NEVER merge an
// unsynced span into the main log without accounting for that -- lessons.md #8.
time_t nowEpoch() {
  time_t t = time(nullptr);
  if (t > 1700000000) { timeSynced = true; return t; }
  return 0;
}

// ---------- wifi ----------
// Both APs share one SSID, so SSID cannot tell you WHICH radio you are on.
//
// IDENTIFY BY BSSID, NOT CHANNEL. An earlier revision keyed off the channel, using the
// "gateway ch 6 / Buffalo ch 11" note in docs/esp32_wifi_production.md. That was wrong:
// consumer gateways run automatic channel selection and re-pick on reboot, and the AT&T
// gateway moved 6 -> 11 when grid power returned after the 2026-09-03 outage. The node
// then cheerfully reported "buffalo" while sitting on the gateway with the Buffalo
// switched off entirely. A BSSID is a MAC and does not drift.
//
// GATEWAY confirmed twice, both times with the Buffalo powered down, so nothing else
// could have answered: 2026-09-04 during the outage, and 2026-09-10 from /json.
const char* AP_GATEWAY_BSSID = "BC:9A:8E:DE:60:54";
// BUFFALO captured 2026-09-10. Identified by elimination, not assumption: the node
// authenticates with OUR SSID and password, so any AP it associates with is one of ours,
// and this is not the gateway. RSSI climbed -73 -> -62 as the node moved toward the
// basement, consistent with the closer radio.
const char* AP_BUFFALO_BSSID = "10:6F:3F:E7:7A:06";

// Never guesses. An unrecognised BSSID reports "unknown", which is information; a wrong
// name is worse than no name -- that is exactly what the channel version produced.
const char* apName() {
  if (WiFi.status() != WL_CONNECTED) return "none";
  String b = WiFi.BSSIDstr();
  if (b.equalsIgnoreCase(AP_GATEWAY_BSSID)) return "gateway";
  if (strlen(AP_BUFFALO_BSSID) && b.equalsIgnoreCase(AP_BUFFALO_BSSID)) return "buffalo";
  return "unknown";
}

void onWifiEvent(WiFiEvent_t e) {
  if (e == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    disconnectCount++;
    Serial.print("# WiFi DISCONNECT node="); Serial.print(NODE_ID);
    Serial.print(" ms="); Serial.println(millis());
  }
  if (e == ARDUINO_EVENT_WIFI_STA_GOT_IP) {
    Serial.print("# WiFi up: node="); Serial.print(NODE_ID);
    Serial.print(" IP=");    Serial.print(WiFi.localIP());
    Serial.print(" BSSID="); Serial.print(WiFi.BSSIDstr());
    Serial.print(" RSSI=");  Serial.print(WiFi.RSSI());
    Serial.print(" ch=");    Serial.print(WiFi.channel());
    Serial.print(" ap=");    Serial.println(apName());
    wifiAttempt = 0;          // joined -- next reconnect starts pinned again
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");   // UTC; logger owns local time

    // Hostname comes from NODE_ID, so it stays per-node automatically: cf.local,
    // fridge.local. Guarded because GOT_IP fires again on every reconnect.
    if (!mdnsUp && MDNS.begin(NODE_ID)) {
      MDNS.addService("http", "tcp", 80);
      mdnsUp = true;
      Serial.print("# mDNS up: http://"); Serial.print(NODE_ID); Serial.println(".local");
    }

    // Put the address on screen as soon as there IS one. setup() runs before the
    // (non-blocking) connect completes, so "at startup" has to mean "on GOT_IP".
    lastIpShow = millis() - IP_SHOW_EVERY_MS;
  }
}

// Which radio this node should join, resolved from EXPECTED_AP. "" = no preference.
const char* expectedBssid() {
  if (!strcmp(EXPECTED_AP, "gateway")) return AP_GATEWAY_BSSID;
  if (!strcmp(EXPECTED_AP, "buffalo")) return AP_BUFFALO_BSSID;
  return "";
}

bool parseBssid(const char* s, uint8_t out[6]) {
  unsigned v[6];
  if (sscanf(s, "%x:%x:%x:%x:%x:%x", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]) != 6) return false;
  for (int i = 0; i < 6; i++) out[i] = (uint8_t)v[i];
  return true;
}

/* Kick off a connect attempt and RETURN. Never spins -- see header note.
 *
 * WHY THE BSSID IS PINNED RATHER THAN LEFT TO THE SCAN
 * esp32_wifi_production.md section 1 prescribes ALL_CHANNEL_SCAN + CONNECT_AP_BY_SIGNAL to
 * make a node take the STRONGEST matching AP rather than the first one seen. Both lines are
 * below, and they are NOT reliably honoured. Measured 2026-09-10 on the fridge node
 * upstairs: over 10 restarts it joined the basement Buffalo at -90 dBm 5 TIMES, in
 * preference to the gateway at -50 dBm sitting in the same room. That is a 40 dB gap --
 * ten thousand times the power -- decided by a coin flip.
 *
 * -90 dBm is 4 dB above the measured noise floor of -94. It associates, so everything
 * LOOKS fine, and then drops packets for as long as it stays there. During an outage that
 * is a node quietly not logging the data the outage exists to collect.
 *
 * The scan hints stay because they cost nothing and help the fallback path. But when we
 * know which radio we want, we ask for it by name.
 *
 * FALLBACK: after PINNED_ATTEMPTS failures, connect unpinned and take whatever answers.
 * A weak link beats no link -- and a dead AP must not strand a node offline, which is
 * exactly the situation section 3 of that doc worries about.
 */
const uint8_t PINNED_ATTEMPTS = 3;

void startWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);      // helps the fallback path only
  WiFi.setSortMethod(WIFI_CONNECT_AP_BY_SIGNAL);  // see block above: not reliably honoured

  uint8_t bssid[6];
  const char* want = expectedBssid();
  if (wifiAttempt < PINNED_ATTEMPTS && strlen(want) && parseBssid(want, bssid)) {
    Serial.print("# WiFi: targeting "); Serial.print(EXPECTED_AP);
    Serial.print(" "); Serial.print(want);
    Serial.print(" (attempt "); Serial.print(wifiAttempt + 1); Serial.println(")");
    WiFi.begin(WIFI_SSID, WIFI_PASS, 0, bssid);
  } else {
    Serial.println("# WiFi: unpinned connect -- taking any AP on this SSID");
    WiFi.begin(WIFI_SSID, WIFI_PASS);
  }
  wifiAttempt++;
}

// ---------- local backup ----------
void rotateIfNeeded() {
  File f = LittleFS.open(LOG_PATH, "r");
  if (!f) return;
  size_t sz = f.size();
  f.close();
  if (sz < MAX_LOG_BYTES) return;
  LittleFS.remove(LOG_OLD);
  LittleFS.rename(LOG_PATH, LOG_OLD);
  Serial.println("# log rotated");
}

void persistRow() {
  if (!fsReady) return;
  rotateIfNeeded();
  File f = LittleFS.open(LOG_PATH, "a");
  if (!f) return;
  // This file is OURS -- not the dual_logger contract -- so it is named L/R throughout.
  if (f.size() == 0)
    f.println("epoch,millis,node,L_label,L_f,R_label,R_f,L_fault,R_fault,synced");
  f.printf("%lu,%lu,%s,%s,%.3f,%s,%.3f,0x%02X,0x%02X,%d\n",
           (unsigned long)nowEpoch(), millis(), NODE_ID,
           L_LABEL, tLF, R_LABEL, tRF, faultL, faultR, timeSynced ? 1 : 0);
  f.close();
  persistCount++;
}

// ---------- sampling ----------
void sample() {
  ohmsL = RREF * (thermoL.readRTD() / 32768.0);
  ohmsR = RREF * (thermoR.readRTD() / 32768.0);
  tLF   = thermoL.temperature(RNOMINAL, RREF) * 1.8 + 32.0;
  tRF   = thermoR.temperature(RNOMINAL, RREF) * 1.8 + 32.0;
  faultL = thermoL.readFault(); if (faultL) thermoL.clearFault();
  faultR = thermoR.readFault(); if (faultR) thermoR.clearFault();
  sampleCount++;
}

// LEGACY WIRE FORMAT -- dual_logger.py parses these exact strings off USB SERIAL.
// It keys on Resistance1/Resistance2 (regex `Resistance1\s*=\s*([\d.]+)`) and computes
// temperature itself via inverse CVD; it deliberately IGNORES the Temperature lines.
// Any line matching /[Ff]ault/ sets its fault flag. Do not reformat without changing
// every consumer in the same commit (CLAUDE.md: atomic across consumers).
//
// *** THE CROSSOVER. Wire channel 1 = R module, wire channel 2 = L module. ***
// The numbers here are dual_logger's, not ours: it binds channel 1 to the FREEZER, and on
// the fridge node the freezer probe is on the RIGHT module. This is the ONE place in the
// sketch where 1/2 appears, and it is deliberate. See the L/R block at the top.
//
void emitReadings() {
  String s;
  s += "Resistance1 = "  + String(ohmsR, 4) + "\n";   // ch1 <- RIGHT (CS 2)
  s += "Resistance2 = "  + String(ohmsL, 4) + "\n";   // ch2 <- LEFT  (CS 15)
  s += "Temperature1 = " + String(tRF, 4) + "\n";
  s += "Temperature2 = " + String(tLF, 4) + "\n";
  if (faultR) s += "Fault1 0x" + String(faultR, HEX) + "\n";
  if (faultL) s += "Fault2 0x" + String(faultL, HEX) + "\n";
  s += "\n";
  Serial.print(s);
  if (client.connected()) client.print(s);
}

// ---------- oled ----------
// Layout from esp32_rtd_display.ino: ArialMT_Plain_24, centred at x=60, rows at y=0/y=35.
// L on top, R below.
//
// The screen shows the HARDWARE position (L/R), not the deployment label (ffc/fc). It sits
// on the board beside the two modules, so L/R is what you can check by eye -- and it stays
// true no matter what gets plugged in or which node this is. The web page and the logged
// CSV carry the ffc/fc labels instead, where the extra context is useful and the board is
// not in front of you.
void updateDisplay() {
  if (!displayReady) return;
  unsigned long now = millis();

  // Alternate: temperatures normally, address for IP_SHOW_FOR_MS every IP_SHOW_EVERY_MS.
  // Called at 1 Hz from loop(), so the switch is accurate to about a second -- fine.
  if (!showingIp && now - lastIpShow >= IP_SHOW_EVERY_MS) { showingIp = true;  ipShowStart = now; }
  if ( showingIp && now - ipShowStart >= IP_SHOW_FOR_MS)  { showingIp = false; lastIpShow  = now; }

  display.clear();
  display.setColor(WHITE);
  display.setTextAlignment(TEXT_ALIGN_CENTER);

  if (showingIp) {
    // Smaller font: a dotted-quad will not fit at 24 pt across 128 px.
    display.setFont(ArialMT_Plain_16);
    display.drawString(64,  0, String(NODE_ID) + ".local");
    if (WiFi.status() == WL_CONNECTED) {
      display.drawString(64, 22, WiFi.localIP().toString());
      // Which AP + signal, so an install check needs nothing but your eyes.
      display.drawString(64, 44, String(apName()) + "  " + String(WiFi.RSSI()) + "dBm");
    } else {
      display.drawString(64, 22, "no wifi");
    }
  } else {
    display.setFont(ArialMT_Plain_24);
    display.drawString(60,  0, "L " + String(tLF, 1));
    display.drawString(60, 35, "R " + String(tRF, 1));
  }
  display.display();
}

// ---------- http ----------
// Push one file's bytes into the (chunked) response. Small fixed buffer -- the log can be
// 500 KB and there is nowhere near that much RAM to build a String from.
void streamLogFile(const char* path) {
  File f = LittleFS.open(path, "r");
  if (!f) return;
  uint8_t buf[512];
  while (f.available()) {
    size_t n = f.read(buf, sizeof(buf));
    if (!n) break;
    server.sendContent((const char*)buf, n);
  }
  f.close();
}

String jsonBody() {
  String j = "{";
  j += "\"node\":\""   + String(NODE_ID) + "\",";
  j += "\"uptime_s\":" + String(millis() / 1000) + ",";
  j += "\"epoch\":"    + String((unsigned long)nowEpoch()) + ",";
  j += "\"time_synced\":" + String(timeSynced ? "true" : "false") + ",";
  j += "\"rssi\":"     + String(WiFi.RSSI()) + ",";
  j += "\"channel\":"  + String(WiFi.channel()) + ",";
  j += "\"ap\":\""     + String(apName()) + "\",";
  j += "\"expected_ap\":\"" + String(EXPECTED_AP) + "\",";
  j += "\"bssid\":\""  + WiFi.BSSIDstr() + "\",";
  j += "\"disconnects\":" + String(disconnectCount) + ",";
  j += "\"logger_connected\":" + String(client.connected() ? "true" : "false") + ",";
  j += "\"samples\":"  + String(sampleCount) + ",";
  j += "\"persisted\":" + String(persistCount) + ",";
  j += "\"channels\":[";
  j += "{\"side\":\"L\",\"label\":\"" + String(L_LABEL) + "\",\"f\":" + String(tLF, 2) +
       ",\"ohms\":" + String(ohmsL, 2) + ",\"fault\":" + String(faultL) + "},";
  j += "{\"side\":\"R\",\"label\":\"" + String(R_LABEL) + "\",\"f\":" + String(tRF, 2) +
       ",\"ohms\":" + String(ohmsR, 2) + ",\"fault\":" + String(faultR) + "}";
  j += "]}";
  return j;
}

// Self-contained page -- no CDN, no internet. Big numbers, dark, readable one-handed.
const char PAGE[] PROGMEM = R"HTML(<!doctype html><meta name=viewport
content="width=device-width,initial-scale=1"><title>RTD node</title>
<style>body{background:#111;color:#eee;font:16px system-ui;margin:0;padding:18px}
h1{font-size:15px;color:#8ab;margin:0 0 14px;letter-spacing:.08em;text-transform:uppercase}
.c{background:#1c1c1c;border-radius:12px;padding:16px;margin-bottom:10px}
.l{font-size:13px;color:#9a9a9a;text-transform:uppercase;letter-spacing:.06em}
.v{font-size:44px;font-weight:600;line-height:1.1;font-variant-numeric:tabular-nums}
.u{font-size:20px;color:#888}.f{color:#e66;font-size:13px}
.m{font-size:12px;color:#777;line-height:1.7;margin-top:14px}
.bad{color:#e66}.ok{color:#6d6}a{color:#8ab}</style>
<h1 id=n>node</h1><div id=ch></div><div class=m id=meta></div>
<script>
async function u(){try{const r=await fetch('/json'),d=await r.json();
n.textContent=d.node+' · rtd node';
ch.innerHTML=d.channels.map(c=>`<div class=c><div class=l>${c.label}</div>
<div class=v>${c.f.toFixed(1)}<span class=u>&deg;F</span></div>
${c.fault?`<div class=f>FAULT 0x${c.fault.toString(16)}</div>`:''}</div>`).join('');
meta.innerHTML=`logger: <span class=${d.logger_connected?'ok':'bad'}>
${d.logger_connected?'connected':'OFFLINE'}</span><br>
clock: <span class=${d.time_synced?'ok':'bad'}>${d.time_synced?'NTP synced':'UNSYNCED'}</span><br>
ap: <span class=${d.ap==d.expected_ap?'ok':'bad'}>${d.ap}</span>
${d.ap==d.expected_ap?'':' (expected '+d.expected_ap+')'} &middot; ch ${d.channel}
&middot; ${d.bssid}<br>
rssi ${d.rssi} dBm &middot; ${d.disconnects} drops &middot; up ${Math.floor(d.uptime_s/60)} min<br>
${d.persisted} rows saved &middot; <a href=/log>download backup</a>`;
}catch(e){meta.textContent='node unreachable';}}
u();setInterval(u,2000);
</script>)HTML";

void setupRoutes() {
  // charset MUST be declared: the page contains UTF-8 (e.g. the middot in the heading),
  // and without it browsers decode as Latin-1 and render "FRIDGE Â· RTD NODE".
  server.on("/", []() { server.send_P(200, "text/html; charset=utf-8", PAGE); });
  server.on("/json", []() { server.send(200, "application/json", jsonBody()); });

  // Serve the rotated file first so the download reads oldest -> newest.
  //
  // Do NOT use server.streamFile() here. It emits its own status line and headers, so
  // after server.send() has already sent them you get a second set written into the BODY
  // -- the downloaded CSV starts with "HTTP/1.1 200 OK / Content-Type: text/csv" twice.
  // (Observed 2026-09-05.) Chunked encoding also avoids declaring a Content-Length that
  // persistRow() then invalidates by appending a row mid-download, which truncated the
  // final line of that same capture.
  server.on("/log", []() {
    if (!fsReady) { server.send(503, "text/plain", "no filesystem\n"); return; }
    server.setContentLength(CONTENT_LENGTH_UNKNOWN);      // -> chunked
    server.send(200, "text/csv", "");
    streamLogFile(LOG_OLD);
    streamLogFile(LOG_PATH);
    server.sendContent("");                               // terminate the chunked body
  });

  server.on("/log/clear", []() {
    if (server.arg("confirm") != "yes") {
      server.send(400, "text/plain", "add ?confirm=yes to erase the local backup\n");
      return;
    }
    LittleFS.remove(LOG_PATH);
    LittleFS.remove(LOG_OLD);
    persistCount = 0;
    server.send(200, "text/plain", "erased\n");
  });

  server.onNotFound([]() { server.send(404, "text/plain", "not found\n"); });
}

// ---------- lifecycle ----------
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.print("# esp32_rtd_wifi_node boot -- node="); Serial.println(NODE_ID);

  thermoL.begin(MAX31865_3WIRE);
  thermoR.begin(MAX31865_3WIRE);

  display.init();
  if (DISPLAY_FLIP) display.flipScreenVertically();
  display.setFont(ArialMT_Plain_24);
  displayReady = true;
  Serial.println("# OLED init");

  fsReady = LittleFS.begin(true);      // true = format if unmounted
  Serial.print("# LittleFS "); Serial.println(fsReady ? "ready" : "FAILED");

  WiFi.onEvent(onWifiEvent);
  startWifi();                          // returns immediately; loop() keeps working

  setupRoutes();
  server.begin();
}

void loop() {
  // Non-blocking WiFi retry. Local logging and the phone page keep running regardless.
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiTry > WIFI_RETRY_MS) {
    lastWifiTry = millis();
    startWifi();
  }

  server.handleClient();

  if (TCP_PUSH && WiFi.status() == WL_CONNECTED && !client.connected() && millis() - lastTry > 3000) {
    lastTry = millis();
    if (client.connect(HOST, PORT)) {
      Serial.println("# TCP connected");
      client.print("# node=" + String(NODE_ID) +
                   " L=" + L_LABEL + "(ch2) R=" + R_LABEL + "(ch1)\n");
    }
  }

  if (millis() - lastSend >= SEND_MS) {
    lastSend = millis();
    sample();
    emitReadings();
    updateDisplay();
  }

  if (millis() - lastPersist >= PERSIST_MS) {
    lastPersist = millis();
    persistRow();
  }
}
