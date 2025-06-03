#include <Arduino.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <HTTPClient.h>
#include "env.h"

OneWire oneWire(temp_Sensor);
DallasTemperature Temp(&oneWire);

void post_sensor_data(float temperature, bool presence) {
  HTTPClient http;
  String requestBody;

  http.begin(ENDPOINT);
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["temperature"] = temperature;
  doc["presence"] = presence;

  doc.shrinkToFit();
  serializeJson(doc, requestBody);

  int httpResponseCode = http.PUT(requestBody);

  Serial.print("HERE IS THE RESPONSE: ");
  Serial.println(requestBody);
  Serial.println(http.getString());
  Serial.println();

  http.end();
}

void get_control_data() {
  HTTPClient http;
  
  String path = String(ENDPOINT) + "/control";
  http.begin(path.c_str());

  int httpResponseCode = http.GET();

  if(httpResponseCode > 0) {
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);

    String responseBody = http.getString();
    Serial.println(responseBody);

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, responseBody);

    if (error) {
      Serial.print("deserializeJson() failed: ");
      Serial.println(error.c_str());
      return;
    }

    bool fanStat = doc["fan"];
    bool lightStat = doc["light"];
    digitalWrite(FAN_Pin, fanStat);
    digitalWrite(LIGHT_Pin, lightStat);
  }
  else {
    Serial.print("Error code: ");
    Serial.println(httpResponseCode);
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIR_Pin, INPUT);
  pinMode(FAN_Pin, OUTPUT);
  pinMode(LIGHT_Pin, OUTPUT);
  pinMode(temp_Sensor, INPUT);

  Temp.begin();

  if (IS_WOKWI)
    WiFi.begin(SSID, PASS, CHANNEL);
  else 
    WiFi.begin(SSID, PASS);

  Serial.println("Connecting");
  while(WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if(WiFi.status()== WL_CONNECTED) {
    Temp.requestTemperatures();
    float currentTemp = Temp.getTempCByIndex(0);
    bool currentPresence = digitalRead(PIR_Pin) == HIGH;

    post_sensor_data(currentTemp, currentPresence);
    get_control_data();
    
    delay(5000);
  }
  else {
    Serial.println("WiFi Disconnected");
  }
}