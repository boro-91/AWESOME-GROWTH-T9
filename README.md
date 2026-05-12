# Greenhouse Monitoring & Control System

This repository contains the software for a school greenhouse project using a Raspberry Pi.  
The system reads sensor data, controls greenhouse components such as heating, ventilation and misting, stores historical data, and displays the data in a dashboard.

> This README gives a high-level technical overview of the project.  
> Detailed project documentation, construction notes, diagrams and testing results should be kept in a separate documentation file.

---

## 1. Project Goal

The goal of this project is to build a small automated greenhouse system that can:

- read temperature and humidity values
- detect whether the soil/ground is dry
- control heating, ventilation and misting
- show local status information on a display / LED matrix
- send measurements to a backend
- store historical data
- display live and historical values in a dashboard
- optionally receive remote control commands from the dashboard

The Raspberry Pi remains responsible for the local control logic and safety rules.

---

## 2. High-Level Architecture

```text
Raspberry Pi
  ├── reads sensors
  ├── controls GPIO outputs
  ├── updates local display / LED matrix
  ├── sends measurement data to backend
  └── checks for remote commands

Firebase Cloud Functions
  ├── receives measurements from the Raspberry Pi
  ├── validates incoming data
  ├── writes data to Firestore
  ├── creates remote commands from dashboard actions
  └── returns pending commands to the Raspberry Pi

Cloud Firestore
  ├── stores historical measurements
  ├── stores latest device status
  ├── stores commands
  └── stores optional settings

Vue Dashboard
  ├── login with Firebase Authentication
  ├── shows current greenhouse status
  ├── shows historical charts
  └── allows manual control commands
```

The dashboard does **not** directly control the GPIO pins.  
Instead, dashboard actions are stored as commands. The Raspberry Pi fetches these commands and decides locally whether they are safe to execute.

---

## 3. Hardware Overview

### Main Components

| Component | Purpose |
|---|---|
| Raspberry Pi | Main controller |
| DHT22 sensor | Measures temperature and humidity |
| Soil / ground sensor | Detects dry or wet soil |
| Heating output | Warms the greenhouse |
| Fan output | Cools / ventilates the greenhouse |
| Misting outputs | Controls air/soil misting |
| LCD display | Shows local status information |
| LED matrix | Shows simple visual status animations |

### Greenhouse Structure

The physical greenhouse structure was built separately from the software.

Construction notes can be added here:

```text
TODO:
- describe greenhouse frame/material
- describe sensor placement
- describe heater placement
- describe fan placement
- describe misting system placement
- add photos or diagram if useful
```

---

## 4. Raspberry Pi Pin Configuration

The current implementation uses BCM GPIO numbering.

| Function | GPIO Pin | Notes |
|---|---:|---|
| Soil / ground sensor | GPIO 17 | Input |
| Misting output 1 | GPIO 27 | Output |
| Misting output 2 | GPIO 23 | Output |
| Heating | GPIO 16 | Output |
| Fan | GPIO 18 | Output |
| DHT22 sensor | Board D4 | Temperature and humidity |
| LED matrix SPI SCLK | GPIO 11 | SPI |
| LED matrix SPI MOSI | GPIO 10 | SPI |
| LED matrix SPI CS | GPIO 8 | SPI |
| LCD I2C address | `0x27` | PCF8574 I2C LCD |

> Important: verify the actual wiring before running the code.  
> Incorrect wiring can damage components or the Raspberry Pi.

---

## 5. Current Local Control Logic

The Raspberry Pi currently uses this basic automatic logic:

### Temperature

```text
If temperature < TEMP_MIN:
  heater ON
  fan OFF

If temperature > TEMP_MAX:
  heater OFF
  fan ON

Otherwise:
  heater OFF
  fan OFF
```

Default thresholds:

```text
TEMP_MIN = 18.0 °C
TEMP_MAX = 28.0 °C
```

### Humidity / Soil

```text
If soil is dry:
  misting output 1 ON
  misting output 2 ON

Else if humidity < HUM_TARGET:
  misting output 1 ON
  misting output 2 OFF

Otherwise:
  misting output 1 OFF
  misting output 2 OFF
```

Default threshold:

```text
HUM_TARGET = 35.0 %
```

---

## 6. Recommended Software Structure

The original prototype can work as a single Python file, but the final version should be split into modules.

Recommended Raspberry Pi folder structure:

```text
greenhouse/
  main.py
  config.py
  sensors.py
  controller.py
  actuators.py
  display.py
  api_client.py
  command_handler.py
  logger.py
  requirements.txt
```

### File Responsibilities

| File | Responsibility |
|---|---|
| `main.py` | Main program loop |
| `config.py` | Pins, thresholds, API URLs, device ID |
| `sensors.py` | Reads DHT22 and soil sensor |
| `controller.py` | Decides automatic actions |
| `actuators.py` | Applies GPIO output states |
| `display.py` | Updates LCD and LED matrix |
| `api_client.py` | Sends data and fetches commands |
| `command_handler.py` | Handles remote commands safely |
| `logger.py` | Optional logging helper |

---

## 7. Backend / Firebase Architecture

The project uses Firebase as the backend platform.

### Firebase Services

| Service | Purpose |
|---|---|
| Firebase Authentication | Login for the dashboard |
| Cloud Firestore | Stores measurements, commands and status data |
| Cloud Functions | Backend layer / API between Pi, dashboard and Firestore |

### Firestore Collections

Recommended collections:

```text
devices/
measurements/
commands/
settings/
```

### `devices`

Stores the latest known state of a greenhouse device.

Example:

```json
{
  "name": "School Greenhouse",
  "lastSeen": "server timestamp",
  "online": true,
  "currentTemperature": 22.4,
  "currentHumidity": 48.2,
  "soilDry": false,
  "heaterOn": false,
  "fanOn": false,
  "mist1On": false,
  "mist2On": false,
  "mode": "automatic"
}
```

### `measurements`

Stores historical sensor and actuator data.

Example:

```json
{
  "deviceId": "greenhouse-01",
  "timestamp": "server timestamp",
  "temperature": 22.4,
  "humidity": 48.2,
  "soilDry": false,
  "heaterOn": false,
  "fanOn": false,
  "mist1On": false,
  "mist2On": false,
  "mode": "automatic",
  "temperatureStatus": "OK",
  "humidityStatus": "AUS"
}
```

### `commands`

Stores remote commands created by the dashboard.

Example:

```json
{
  "deviceId": "greenhouse-01",
  "type": "heater_override",
  "value": "on",
  "status": "pending",
  "createdAt": "server timestamp",
  "createdBy": "firebase-user-id",
  "executedAt": null,
  "rejectedReason": null
}
```

### `settings`

Stores optional greenhouse configuration.

Example:

```json
{
  "tempMin": 18,
  "tempMax": 28,
  "humTarget": 35,
  "safetyTempMax": 30,
  "measurementIntervalSeconds": 60
}
```

---

## 8. Cloud Function Endpoints

Recommended Cloud Functions:

| Function | Used By | Purpose |
|---|---|---|
| `submitMeasurement` | Raspberry Pi | Sends new sensor/actuator measurement |
| `getPendingCommands` | Raspberry Pi | Fetches pending dashboard commands |
| `updateCommandStatus` | Raspberry Pi | Marks command as executed or rejected |
| `createCommand` | Dashboard | Creates command after user button click |

### Measurement Flow

```text
Raspberry Pi
  → POST submitMeasurement
  → Cloud Function validates data and API key
  → Firestore stores measurement
  → Dashboard displays data
```

### Command Flow

```text
Dashboard user clicks button
  → createCommand Cloud Function
  → command stored in Firestore as pending
  → Raspberry Pi fetches pending command
  → Raspberry Pi checks safety rules
  → Raspberry Pi executes or rejects command
  → command status is updated
```

---

## 9. Dashboard Overview

The dashboard should include:

### Login

- email/password login
- Firebase Authentication
- protected dashboard route

### Current Status

- temperature
- humidity
- soil status
- heater status
- fan status
- misting status
- current mode
- last update

### Historical Data

- temperature chart
- humidity chart
- soil dry/wet events
- actuator activity over time

### Manual Controls

- automatic/manual mode toggle
- heater ON/OFF
- fan ON/OFF
- misting ON/OFF

Manual commands should be treated as requests.  
The Raspberry Pi must still check whether a command is safe before applying it.

---

## 10. Safety Concept

The Raspberry Pi is the local safety controller.

Minimum safety rules:

```text
If temperature is too high:
  heater must stay OFF

If temperature is above the cooling threshold:
  fan should turn ON

If sensor data is invalid:
  avoid unsafe actuator behavior

If a command is unknown:
  reject the command

If a command is unsafe:
  reject the command and store the reason
```

Example:

```text
Dashboard requests heater ON
→ Raspberry Pi checks current temperature
→ if temperature >= safetyTempMax, command is rejected
```

This prevents the dashboard from blindly controlling hardware.

---

## 11. Running the Raspberry Pi Program

During development:

```bash
python3 main.py
```

For a more professional setup, run the program as a `systemd` service so that it starts automatically after boot.

Example commands:

```bash
sudo systemctl start greenhouse
sudo systemctl stop greenhouse
sudo systemctl restart greenhouse
sudo systemctl status greenhouse
```

Enable automatic startup:

```bash
sudo systemctl enable greenhouse
```

View logs:

```bash
journalctl -u greenhouse -f
```

---

## 12. Environment Variables

The Raspberry Pi should use an API key when sending data to the Cloud Function.

Example:

```text
GREENHOUSE_API_KEY=replace-with-real-key
```

This key should **not** be stored in the frontend dashboard code.

Recommended places:

```text
- systemd service environment variable
- local .env file
- shell environment variable
```

---

## 13. Development Phases

### Phase 1: Hardware and Local Prototype

- build greenhouse structure
- connect sensors and actuators
- verify GPIO pin mapping
- test DHT22 sensor
- test soil sensor
- test heater/fan/misting outputs
- test LCD and LED matrix
- confirm local automatic control works

### Phase 2: Raspberry Pi Refactoring

- remove test/debug code
- split Python code into modules
- add config file
- add measurement payload creation
- add safe error handling
- add logging

### Phase 3: Firebase Backend

- create Firebase project
- enable Authentication
- enable Firestore
- create Cloud Functions
- implement measurement endpoint
- implement command endpoints
- configure Firestore security rules

### Phase 4: Dashboard

- implement login screen
- connect Vue dashboard to Firebase
- show current status
- show historical charts
- add manual control buttons
- add command history

### Phase 5: Final Integration

- Raspberry Pi sends data to backend
- dashboard reads live and historical data
- dashboard creates commands
- Raspberry Pi executes or rejects commands
- run Pi program as systemd service
- test complete data flow

---

## 14. Suggested Measurement Frequency

Recommended default:

```text
1 measurement per minute
```

This gives:

```text
60 measurements per hour
1,440 measurements per day
10,080 measurements per week
```

For testing/demo purposes, the interval can temporarily be reduced.

---

## 15. Repository Notes

Suggested repository structure:

```text
greenhouse-project/
  README.md
  raspberry-pi/
    main.py
    config.py
    sensors.py
    controller.py
    actuators.py
    display.py
    api_client.py
    command_handler.py
    requirements.txt

  firebase/
    functions/
      index.js
      package.json
    firestore.rules

  dashboard/
    src/
      views/
      components/
      services/
      firebase.js

  docs/
    architecture.md
    wiring.md
    testing.md
```

---

## 16. Open TODOs

```text
TODO:
- add final wiring diagram
- document exact greenhouse structure
- document exact sensor placement
- document exact actuator placement
- add screenshots of dashboard
- add Firebase setup screenshots
- add deployment instructions
- add test cases
- add final presentation diagram
```

---

## 17. Summary

This project uses a Raspberry Pi as a local greenhouse controller and Firebase as the backend platform.

The Raspberry Pi reads sensor data, controls the greenhouse locally, and sends measurements to Firebase Cloud Functions.  
Cloud Firestore stores historical data and command information.  
The Vue dashboard uses Firebase Authentication for login and displays current and historical greenhouse data.

Remote control is implemented through commands, not direct GPIO access.  
The Raspberry Pi remains responsible for checking safety rules before executing any command.
