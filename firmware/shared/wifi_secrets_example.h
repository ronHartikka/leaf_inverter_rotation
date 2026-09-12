// wifi_secrets_example.h -- TEMPLATE, committed. Safe: contains no real credentials.
//
// Setup: copy this file to firmware/shared/wifi_secrets.h and fill in the two values.
// wifi_secrets.h is git-ignored, so the real SSID and password stay off GitHub.
// Sketches include it the same way rotation_production.ino includes the other shared
// headers:  #include "../shared/wifi_secrets.h"
#pragma once

const char* WIFI_SSID = "YOUR_SSID";        // 2.4 GHz net
const char* WIFI_PASS = "YOUR_PASSWORD";
