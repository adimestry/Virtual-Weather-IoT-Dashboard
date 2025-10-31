# Multi-City Virtual IoT Weather Station

A Python application that simulates IoT weather stations across multiple cities, featuring both a rich GUI mode and a headless mode for automated data publishing. The GUI provides a clean table layout and real-time temperature graphs, while headless mode is perfect for testing and automation scenarios.

## Features

- **Two Operation Modes**:
  - GUI mode with live data tables and temperature graphs
  - Headless mode for automated data publishing
- **Rich Data Visualization**:
  - Clean table layout showing all cities' data
  - Weather condition icons (☀️ 🌤️ 🌧️) based on conditions
  - Real-time Matplotlib graph for temperature history
- **MQTT Integration**:
  - Optional publishing to any MQTT broker
  - Safe topic naming (sanitizes city names)
  - Configurable broker connection
- **Data Generation**:
  - Simulated temperature, humidity, and wind speed
  - Automatic updates (configurable interval)
  - Optional JSON logging to file

## Prerequisites

- Python 3.8+
- Required packages (install via `pip install -r requirements.txt`):
  - matplotlib>=3.0
  - paho-mqtt>=1.6

## Quick Start

1. Install dependencies:
```bash
python -m pip install -r requirements.txt
```

2. Run in GUI mode:
```bash
# Basic GUI mode:
python app.py

# GUI with MQTT enabled:
python app.py --mqtt --broker test.mosquitto.org
```

3. Run in headless mode:
```bash
# Basic headless run with MQTT:
python app.py --headless --cities "London,Paris,New York" --mqtt --broker test.mosquitto.org

# With custom interval and logging:
python app.py --headless --cities "Tokyo,Seoul" --interval 5000 --log-file weather.jsonl
```

## Command Line Options

- `--mqtt`: Enable MQTT publishing
- `--broker`: MQTT broker host (default: "localhost")
- `--port`: MQTT broker port (default: 1883)
- `--client-id`: MQTT client ID (default: "virtual-weather-client")
- `--headless`: Run without GUI
- `--cities`: Comma-separated city names (required in headless mode)
- `--interval`: Update interval in milliseconds (default: 2000)
- `--log-file`: Log file to append JSON messages

## MQTT Topics & Messages

Topics follow the format `weather/<city>` where `<city>` is sanitized:
- Lowercase
- Spaces/punctuation replaced with underscores
- Special characters removed

Examples:
- "London" → `weather/london`
- "New York" → `weather/new_york`
- "St. Petersburg" → `weather/st_petersburg`

Messages are JSON objects:
```json
{
  "timestamp": "2025-10-31T12:34:56.789+00:00",
  "city": "London",
  "temperature": 22.5,
  "humidity": 65.0,
  "wind": 12.3,
  "condition": "🌤️"
}
```

Weather conditions:
- ☀️ Sunny (temp > 30°C, humidity < 50%)
- 🌧️ Rainy (humidity > 80%)
- 🌤️ Partly Cloudy (default)

## Files

- `app.py`: Main application (GUI and headless modes)
- `mqtt_client.py`: MQTT client wrapper
- `requirements.txt`: Python package requirements
- `tests/`: Unit tests
## ScreenShort 
<img width="272" height="140" alt="Screenshot 2025-10-31 113843" src="https://github.com/user-attachments/assets/2631e844-681e-4acf-b10b-540a2c825246" />
<img width="1017" height="677" alt="Screenshot 2025-10-31 112647" src="https://github.com/user-attachments/assets/fff71db3-9385-4d11-bd2e-3614e0ddabca" />



## Notes

- This project simulates sensor data using random numbers — no hardware required
- The MQTT functionality is optional; the app runs without publishing if MQTT is unavailable
- All timestamps are in UTC with proper timezone information

