# ESP32 WiFi — production firmware notes

Source: app-project conversation 2026-07-28 ("Buffalo router as AP, RTDs on WiFi").
Recovered into the repo 2026-07-30 after an audit found it had never crossed from
chat into version control. Empirically validated where noted.

These items belong in the ONE shared connect routine that all ESP32 nodes run.

---

## 1. Best-AP selection (validated)

`WiFi.begin()` defaults to a **fast scan**: it associates with the first matching
SSID it finds, not the strongest. With two APs sharing an SSID on different
channels, a basement node will happily attach to the distant gateway.

```cpp
WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);
WiFi.setSortMethod(WIFI_CONNECT_AP_BY_SIGNAL);
// ...then WiFi.begin(ssid, pass);
```

**Measured result:** with these two lines, a basement node independently chose the
Buffalo (BSSID `REDACTED-BSSID`) at −42 dBm over the AT&T gateway at −61 dBm.

Trade-off: the all-channel scan costs a second or two at boot. Correct call for
fixed sensor nodes.

## 2. Disconnect reporting via WiFi event handler

Register an event handler that emits timestamped disconnect/reconnect records into
the same stream the node already sends to the logger, so link transients are captured
even when the node reconnects seconds later and looks fine by morning.

```cpp
WiFi.onEvent([](WiFiEvent_t e){
  if (e == ARDUINO_EVENT_WIFI_STA_DISCONNECTED)
    emit("DISCONNECT", millis());
  if (e == ARDUINO_EVENT_WIFI_STA_CONNECTED)
    emit("RECONNECT", millis(), WiFi.BSSIDstr(), WiFi.RSSI());
});
```

`emit()` must write to the node's transport to the laptop, **not just Serial** — a
3 AM drop has to survive in the persisted log, not scroll away.

## 3. The no-roam caveat

`WIFI_CONNECT_AP_BY_SIGNAL` chooses the strongest AP **at connect time only**. Once
associated, the ESP32 does not roam — it holds its chosen AP until the link actually
drops, even if the other AP becomes much stronger.

Consequence: if a node's closer AP blips, the node fails over to the weaker AP and
**stays there** after the closer one recovers, until it disconnects again. Over a
long unattended run, nodes can migrate to the wrong AP.

- **Passive (default):** accept it. "Wrong AP" means weaker-but-working, and the
  disconnect log shows the failover. Fine wherever fallback-AP RSSI margin is adequate.
- **Active (only if margin is tight somewhere):** periodically check `WiFi.RSSI()`;
  if worse than ~−75 dBm for N consecutive minutes, force
  `WiFi.disconnect(); WiFi.begin(...)` to re-run best-AP selection. Crude roaming
  without 802.11r.

Decide **per node** by measuring its RSSI to both APs at its install spot — boot the
node once near each AP during install; the boot banner (§5) reports what it saw.

## 4. Heartbeat — complements the disconnect log, does not replace it

The node emits a periodic heartbeat even when readings are unchanged, so a gap in the
CSV is unambiguous: node silent.

The two mechanisms cover different failures and production wants both. The disconnect
handler catches link drops the node can self-report. It **cannot** catch a brownout
reset or a hang — those appear only as a heartbeat gap seen at the laptop.

## 5. Boot banner with identity

Each node emits its BSSID and RSSI at boot (and to the OLED). Makes install-time
verification a number you read rather than a guess, and leaves a visible marker in
the log at every reboot.

## 6. Node identity via strapping pins

Tie a unique GPIO combination to GND, read at boot with `INPUT_PULLUP`.

- **Good candidates:** GPIO 25 / 26 / 27 / 32 / 33, if free.
- **Avoid:** 0 / 2 / 12 / 15 (boot straps), 6–11 (flash), 34–39 (no internal pullups).

The same ID can select OLED rotation for upside-down mounting.

## 7. Timestamps

`millis()` is per-boot and resets on reboot — fine for spotting transients within a
session, and a reboot is *visible* precisely because `millis()` jumps back to near
zero. For cross-node sample alignment, use the NTP-synced per-sample timestamps
already on the backlog.

---

## Hardware note — basement Buffalo

Buffalo WZR-600DHP, DD-WRT, Router switch OFF (AP/bridge mode), LAN-to-LAN to the
AT&T gateway. Same SSID and password as the gateway, different channel (gateway on
2.4 GHz ch 6, Buffalo on ch 11).

The power jack had a **corroded flat-spring outer contact** — filed clean. The cable
is now strain-relieved via adhesive zip-tie mounts plus the jack's built-in
strain-relief clip (the plug must seat fully to engage it). Center pin measured
2.0 mm and matches the plug: the flakiness was the corroded spring, **not** a size
mismatch. If flakiness returns, suspect the spring re-oxidizing.

This Buffalo is load-bearing for basement nodes during outages. Validate with an
overnight soak — an empty disconnect log (§2) means the jack fix held.