**Simple Smart Hub - ECSE_Project**

This project is a simple IoT-based smart home system that uses an ESP32 to control a fan and a light based on temperature, presence detection, and time. It connects to a FastAPI backend that handles decision-making and stores sensor data in a MongoDB database.

The Simple Smart Hub system comprises three main components:

**FastAPI Backend**

Receives sensor readings (temperature and presence) from the ESP32.

Accepts user-defined settings (target temperature, light time, duration).

Calculates light off time based on set duration and on-time or local sunset.

Determines whether fan and light should be activated and returns decisions to the ESP32.

Exposes RESTful API endpoints for interaction with the ESP32 and frontend interface.

**ESP32 Microcontroller**

Equipped with a DS18B20 temperature sensor and PIR motion sensor.

Sends readings to the backend every 10 seconds over HTTPS.

Receives control commands (fan/light ON/OFF) from backend.

Written in C++ using the Arduino framework.

**Web Dashboard**

Hosted on Netlify.

Allows users to configure automation settings.

Displays real-time sensor data via graphs.

Communicates with backend API to fetch data and push configuration updates.
