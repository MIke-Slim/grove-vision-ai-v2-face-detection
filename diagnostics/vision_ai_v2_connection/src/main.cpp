#include <Arduino.h>
#include <Wire.h>

void setup() {
    Serial.begin(115200);
    Wire.begin();
    Wire.setClock(100000);
#ifdef WIRE_HAS_TIMEOUT
    Wire.setWireTimeout(25000, true);
#endif
    delay(2000);
    Serial.println(F("UNO_VISION_V2_CONNECTION_CHECK"));
}

void loop() {
    Serial.print(F("BUS_IDLE SDA="));
    Serial.print(digitalRead(A4));
    Serial.print(F(" SCL="));
    Serial.println(digitalRead(A5));
    uint8_t found = 0;
    bool visionAck = false;
    for (uint8_t address = 1; address < 127; ++address) {
        Wire.beginTransmission(address);
        uint8_t status = Wire.endTransmission();
        if (status == 0) {
            ++found;
            Serial.print(F("I2C_ACK 0x"));
            if (address < 16) Serial.print('0');
            Serial.println(address, HEX);
            if (address == 0x62) visionAck = true;
        }
#ifdef WIRE_HAS_TIMEOUT
        if (Wire.getWireTimeoutFlag()) {
            Serial.println(F("I2C_TIMEOUT"));
            Wire.clearWireTimeoutFlag();
            break;
        }
#endif
    }
    Serial.print(F("DEVICES="));
    Serial.println(found);
    Serial.println(visionAck ? F("VISION_V2_0x62_ACK") : F("VISION_V2_0x62_NO_ACK"));
    delay(2000);
}
