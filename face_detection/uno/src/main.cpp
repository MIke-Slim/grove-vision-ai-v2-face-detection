#include <Arduino.h>
#include <Wire.h>

constexpr uint8_t kAddress = 0x62;
constexpr uint8_t kMaxFaces = 16;
struct Face { uint16_t x,y,w,h; uint8_t score; };
Face faces[kMaxFaces];
uint16_t frame = 0, width = 0, height = 0;
uint8_t count = 0, receivedPages = 0;
bool haveFrame = false;
unsigned long lastReport = 0, lastValid = 0, lastFrameChanged = 0;

uint16_t read16(const uint8_t* p) { return uint16_t(p[0]) | (uint16_t(p[1])<<8); }

void setup() {
    pinMode(LED_BUILTIN,OUTPUT);
    Serial.begin(115200);
    Wire.begin();
    Wire.setClock(100000);
    Wire.setWireTimeout(25000,true);
    Serial.println(F("OPEN_FACE_UNO_V1: V2 I2C=0x62"));
}

void loop() {
    uint8_t packet[32];
    uint8_t length=Wire.requestFrom(kAddress,uint8_t(sizeof(packet)));
    for(uint8_t i=0;i<length && i<sizeof(packet);++i) packet[i]=Wire.read();
    if(length!=sizeof(packet) || packet[0]!='F' || packet[1]!='D' || packet[2]!=1) {
        if(millis()-lastReport>=2000) {
            Serial.println(F("WAIT_V2: check power, A4=SDA, A5=SCL and face firmware"));
            lastReport=millis();
        }
        if(millis()-lastValid>2000) digitalWrite(LED_BUILTIN,LOW);
        delay(10); return;
    }
    lastValid=millis();
    if(packet[3]!=1) {
        digitalWrite(LED_BUILTIN,LOW);
        if(millis()-lastReport>=2000) {
            Serial.print(F("V2_STATE=")); Serial.println(packet[3]); lastReport=millis();
        }
        delay(10); return;
    }
    uint16_t newFrame=read16(packet+4);
    uint8_t newCount=packet[6],page=packet[7];
    if(newCount>kMaxFaces || page>=max(uint8_t(1),uint8_t((newCount+1)/2))) return;
    if(!haveFrame || frame!=newFrame) {
        frame=newFrame; count=newCount; receivedPages=0; haveFrame=true;
        lastFrameChanged=millis();
        width=read16(packet+8); height=read16(packet+10);
    }
    if(millis()-lastFrameChanged>=2000) {
        digitalWrite(LED_BUILTIN,LOW);
        if(millis()-lastReport>=2000) {
            Serial.print(F("WAIT_V2_STALE: frame not advancing, last=")); Serial.println(frame);
            lastReport=millis();
        }
        delay(10); return;
    }
    if(newCount!=count) return;
    for(uint8_t i=0;i<2;++i) {
        uint8_t index=page*2+i;
        if(index>=count) break;
        const uint8_t* p=packet+12+i*10;
        faces[index]={read16(p),read16(p+2),read16(p+4),read16(p+6),p[8]};
    }
    receivedPages |= uint8_t(1<<page);
    uint8_t pages=max(uint8_t(1),uint8_t((count+1)/2));
    uint8_t needed=uint8_t((uint16_t(1)<<pages)-1);
    if(receivedPages==needed && millis()-lastReport>=500) {
        Serial.print(F("FRAME=")); Serial.print(frame);
        Serial.print(F(" COUNT=")); Serial.print(count);
        Serial.print(F(" IMAGE=")); Serial.print(width); Serial.print('x'); Serial.println(height);
        for(uint8_t i=0;i<count;++i) {
            Serial.print(F("FACE ")); Serial.print(i);
            Serial.print(F(" x=")); Serial.print(faces[i].x);
            Serial.print(F(" y=")); Serial.print(faces[i].y);
            Serial.print(F(" w=")); Serial.print(faces[i].w);
            Serial.print(F(" h=")); Serial.print(faces[i].h);
            Serial.print(F(" score=")); Serial.println(faces[i].score);
        }
        digitalWrite(LED_BUILTIN,count?HIGH:LOW);
        lastReport=millis();
    }
    delay(3);
}
