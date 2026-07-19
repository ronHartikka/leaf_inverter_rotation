
#include <Adafruit_MAX31865.h>

//integrating display
#include "SSD1306.h" // alias for `#include "SSD1306Wire.h"'
//integrating display

// Use software SPI: CS, DI, DO, CLK
Adafruit_MAX31865 thermo1 = Adafruit_MAX31865(15, 13, 12, 14);
Adafruit_MAX31865 thermo2 = Adafruit_MAX31865(2, 13, 12, 14);
// use hardware SPI, just pass in the CS pin
//Adafruit_MAX31865 thermo = Adafruit_MAX31865(10);

// The value of the Rref resistor. Use 430.0 for PT100 and 4300.0 for PT1000
#define RREF      4300.0
// The 'nominal' 0-degrees-C resistance of the sensor
// 100.0 for PT100, 1000.0 for PT1000
#define RNOMINAL  1000.0

//integrating display
SSD1306  display(0x3c, 5, 4);
//integrating display

void setup() {
  Serial.begin(115200);
  Serial.println("Adafruit MAX31865 PT100 Sensor Test!");

  thermo1.begin(MAX31865_3WIRE);  // set to 2WIRE or 4WIRE as necessary
  thermo2.begin(MAX31865_3WIRE);  // set to 2WIRE or 4WIRE as necessary
  //integrating display
  display.init();
  display.flipScreenVertically();
  display.setFont(ArialMT_Plain_24);
  //integrating display
}


void loop() {
  uint16_t rtd1 = thermo1.readRTD();
  uint16_t rtd2 = thermo2.readRTD();

  //integrating display
  //delay(1000);
  display.clear();
  //integrating display

  Serial.print("RTD1 value: "); Serial.println(rtd1);
  Serial.print("RTD2 value: "); Serial.println(rtd2);

  float ratio1 = rtd1;
  float ratio2 = rtd2;

  ratio1 /= 32768;
  ratio2 /= 32768;

  Serial.print("Ratio1 = "); Serial.println(ratio1,8);
  Serial.print("Ratio2 = "); Serial.println(ratio2,8);

  Serial.print("Resistance1 = "); Serial.println(RREF*ratio1,8);
  Serial.print("Resistance2 = "); Serial.println(RREF*ratio2,8);

  float temperature1 = thermo1.temperature(RNOMINAL, RREF);
  float temperature2 = thermo2.temperature(RNOMINAL, RREF);

  temperature1 = (temperature1 * 1.8) + 32;
  temperature2 = (temperature2 * 1.8) + 32;

  //Serial.print("Temperature = "); Serial.println(thermo.temperature(RNOMINAL, RREF));
  Serial.print("Temperature1 = "); Serial.println(temperature1);
  Serial.print("Temperature2 = "); Serial.println(temperature2);

  display.setColor(WHITE);
  display.setTextAlignment(TEXT_ALIGN_CENTER);
  //display.drawString(64, 15, String(temperature1));
  display.drawString(60, 0, String(temperature1) + " F"); // " \xB0""C. Humidity: "
  display.drawString(60, 35, String(temperature2) + " F");
  display.setFont(ArialMT_Plain_24);

  display.display();

  delay(10);

  // Check and print any faults
  uint8_t fault1 = thermo1.readFault();
  if (fault1) {
    Serial.print("Fault 0x"); Serial.println(fault1, HEX);
    if (fault1 & MAX31865_FAULT_HIGHTHRESH) {
      Serial.println("1RTD High Threshold"); 
    }
    if (fault1 & MAX31865_FAULT_LOWTHRESH) {
      Serial.println("1RTD Low Threshold"); 
    }
    if (fault1 & MAX31865_FAULT_REFINLOW) {
      Serial.println("1REFIN- > 0.85 x Bias"); 
    }
    if (fault1 & MAX31865_FAULT_REFINHIGH) {
      Serial.println("1REFIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault1 & MAX31865_FAULT_RTDINLOW) {
      Serial.println("1RTDIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault1 & MAX31865_FAULT_OVUV) {
      Serial.println("1Under/Over voltage"); 
    }
    thermo1.clearFault();
  }

    uint8_t fault2 = thermo2.readFault();
  if (fault2) {
    Serial.print("Fault 0x"); Serial.println(fault2, HEX);
    if (fault2 & MAX31865_FAULT_HIGHTHRESH) {
      Serial.println("2RTD High Threshold"); 
    }
    if (fault2 & MAX31865_FAULT_LOWTHRESH) {
      Serial.println("2RTD Low Threshold"); 
    }
    if (fault2 & MAX31865_FAULT_REFINLOW) {
      Serial.println("2REFIN- > 0.85 x Bias"); 
    }
    if (fault2 & MAX31865_FAULT_REFINHIGH) {
      Serial.println("2REFIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault2 & MAX31865_FAULT_RTDINLOW) {
      Serial.println("2RTDIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault2 & MAX31865_FAULT_OVUV) {
      Serial.println("2Under/Over voltage"); 
    }
    thermo2.clearFault();
  }
  Serial.println();
  delay(1000);
}