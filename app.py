#!/usr/bin/env python3
"""Multi-City Virtual IoT Weather Station - GUI (Tkinter) with live random data and Matplotlib graph.

Features:
- Support for multiple cities with dynamic table layout
- Weather condition icons based on temperature and humidity
- Displays simulated temperature, humidity, wind speed for each city
- Updates every 2-3 seconds
- Real-time temperature graph using Matplotlib embedded in Tkinter
- Optional MQTT publishing (paho-mqtt) via CLI flags
"""
import argparse
import json
import random
import re
import threading
import time
from collections import deque, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import requests  # for API error handling

def sanitize_topic(name: str) -> str:
    """Convert a city name into a safe MQTT topic component.
    
    - Converts to lowercase
    - Replaces spaces and special chars with underscore
    - Removes any remaining non-alphanumeric/underscore chars
    
    Example: "New York City!" -> "new_york_city"
    """
    # Convert to lowercase and replace spaces/punctuation with underscore
    safe = re.sub(r'[\s\-.,!?]+', '_', name.lower())
    # Remove any remaining non-alphanumeric/underscore chars
    safe = re.sub(r'[^a-z0-9_]', '', safe)
    # Remove leading/trailing underscores
    return safe.strip('_')
from tkinter import Tk, StringVar, ttk, simpledialog, messagebox
from typing import Dict, List, Optional

try:
    import matplotlib
    # Use TkAgg backend for Tkinter embedding
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception as e:
    raise RuntimeError("matplotlib is required to run this app: install matplotlib") from e

DEFAULT_HISTORY = 60  # number of points to keep (2s per point -> 2min)


WEATHER_ICONS = {
    'sunny': '☀️',
    'partly_cloudy': '🌤️',
    'rainy': '🌧️'
}

def get_weather_condition(temp: float, humidity: float) -> str:
    """Determine weather condition based on temperature and humidity."""
    if temp > 30 and humidity < 50:
        return WEATHER_ICONS['sunny']
    elif humidity > 80:
        return WEATHER_ICONS['rainy']
    else:
        return WEATHER_ICONS['partly_cloudy']

class WeatherApp:
    def __init__(self, root, mqtt_client=None, update_interval=2000, weather_service=None):
        self.root = root
        self.root.title("Real-Time Weather Station")
        self.mqtt = mqtt_client
        self.update_interval = update_interval  # milliseconds
        print("Weather station starting with update interval:", update_interval, "ms")
        
        # Initialize weather service
        if weather_service is None:
            from weather_service import WeatherService
            try:
                self.weather_service = WeatherService(api_key="TYPZAV86LVECNE9JMXGJYTFNT")
            except ValueError as e:
                messagebox.showerror(
                    "API Key Required",
                    "Visual Crossing Weather API key required."
                )
                raise
        else:
            self.weather_service = weather_service
        
        # Initialize collections
        self.temp_history = deque(maxlen=DEFAULT_HISTORY)
        self.time_history = deque(maxlen=DEFAULT_HISTORY)
        self.city_data: Dict[str, Dict[str, StringVar]] = {}
        
        # Get city names from user
        self.cities = self._get_city_names()
        self.graphed_city = self.cities[0]  # use first city for graph
        
        # Initialize data storage for each city
        for city in self.cities:
            self.city_data[city] = {
                'temp': StringVar(value="-- °C"),
                'humidity': StringVar(value="-- %"),
                'wind': StringVar(value="-- km/h"),
                'condition': StringVar(value=WEATHER_ICONS['partly_cloudy'])
            }

        self._build_style()
        self._build_ui()
        
        # Get initial data for graphed city
        try:
            data = self._get_weather_data(self.graphed_city)
            self._append_data(data['temperature'])
        except Exception:
            self._append_data(20.0)  # Default value if API fails
            
        # start update loop
        self.root.after(500, self.update_loop)

    def _get_city_names(self) -> List[str]:
        """Get comma-separated city names from user."""
        while True:
            cities_input = simpledialog.askstring(
                "City Input",
                "Enter city names (comma-separated):",
                initialvalue="London, Paris, New York"
            )
            if not cities_input:
                return ["Demo City"]  # fallback to prevent empty list
            cities = [city.strip() for city in cities_input.split(",") if city.strip()]
            if cities:
                return cities
            messagebox.showerror("Error", "Please enter at least one city name!")

    def _build_style(self):
        style = ttk.Style(self.root)
        # Use default theme but tweak colors for a clean look
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#f5f7fa")
        style.configure("TLabel", background="#f5f7fa", font=("Segoe UI", 11))
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Value.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#2c3e50")
        style.configure("City.TLabel", font=("Segoe UI", 12, "bold"), foreground="#34495e")

    def _build_ui(self):
        root = self.root
        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        # Top: title
        title = ttk.Label(main, text="Multi-City Virtual IoT Weather Station", style="Title.TLabel")
        title.pack(anchor="w", pady=(0, 16))

        # Data table frame with headers
        table_frame = ttk.Frame(main)
        table_frame.pack(fill="x", pady=(0, 12))

        # Headers
        headers = ["City", "Temperature", "Humidity", "Wind Speed", "Condition"]
        for col, header in enumerate(headers):
            label = ttk.Label(table_frame, text=header, style="Header.TLabel")
            label.grid(row=0, column=col, padx=8, pady=(0, 8), sticky="w")

        # City data rows
        for row, city in enumerate(self.cities, start=1):
            # City name
            city_label = ttk.Label(table_frame, text=city, style="City.TLabel")
            city_label.grid(row=row, column=0, padx=8, pady=4, sticky="w")

            # Temperature
            temp_value = ttk.Label(
                table_frame,
                textvariable=self.city_data[city]['temp'],
                style="Value.TLabel",
                foreground="#d9534f"
            )
            temp_value.grid(row=row, column=1, padx=8, pady=4, sticky="w")

            # Humidity
            hum_value = ttk.Label(
                table_frame,
                textvariable=self.city_data[city]['humidity'],
                style="Value.TLabel",
                foreground="#5bc0de"
            )
            hum_value.grid(row=row, column=2, padx=8, pady=4, sticky="w")

            # Wind
            wind_value = ttk.Label(
                table_frame,
                textvariable=self.city_data[city]['wind'],
                style="Value.TLabel",
                foreground="#5cb85c"
            )
            wind_value.grid(row=row, column=3, padx=8, pady=4, sticky="w")

            # Weather condition
            condition_value = ttk.Label(
                table_frame,
                textvariable=self.city_data[city]['condition'],
                style="Value.TLabel"
            )
            condition_value.grid(row=row, column=4, padx=8, pady=4, sticky="w")

        # Graph area
        graph_frame = ttk.Frame(main)
        graph_frame.pack(fill="both", expand=True, pady=(16, 0))

        graph_title = ttk.Label(
            graph_frame,
            text=f"Temperature History - {self.graphed_city}",
            style="Header.TLabel"
        )
        graph_title.pack(anchor="w", pady=(0, 8))

        self.fig = Figure(figsize=(6, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title(f"Temperature (°C) - {self.graphed_city}")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("°C")
        self.line, = self.ax.plot([], [], color="#d9534f", linewidth=2)
        self.ax.grid(alpha=0.25)

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # --- Weather data fetching ---
    def _get_weather_data(self, city: str) -> dict:
        """Get real weather data for a city using the weather service."""
        try:
            return self.weather_service.get_weather(city)
        except requests.RequestException as e:
            print(f"Error fetching weather for {city}: {e}")
            # Return dummy data on error
            return {
                "temperature": 20.0,
                "humidity": 50.0,
                "wind": 0.0,
                "condition": "❓"
            }

    def _append_data(self, temp):
        current_time = datetime.now()
        # Add a small random variation (±0.2°C) to show micro-changes
        variation = round(random.uniform(-0.2, 0.2), 1)
        display_temp = round(temp + variation, 1)
        print(f"Adding new data point: {display_temp}°C at {current_time.strftime('%H:%M:%S')}")
        self.temp_history.append(display_temp)
        self.time_history.append(current_time)

    def update_loop(self):
        print("\nUpdating weather data...")
        # Update data for each city
        for city in self.cities:
            # Get real weather data
            try:
                data = self._get_weather_data(city)
                print(f"Got new data for {city}: {data}")
                t = data["temperature"]
                h = data["humidity"]
                w = data["wind"]
                condition = data["condition"]  # Use API-provided condition
            except Exception as e:
                print(f"Error updating {city}: {e}")
                continue

            # Update UI for this city
            self.city_data[city]['temp'].set(f"{t} °C")
            self.city_data[city]['humidity'].set(f"{h} %")
            self.city_data[city]['wind'].set(f"{w} km/h")
            self.city_data[city]['condition'].set(condition)

            # Update graph data if this is the graphed city
            if city == self.graphed_city:
                self._append_data(t)
                self._update_graph()

            # Publish via MQTT if available
            if self.mqtt and self.mqtt.is_connected():
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "city": city,
                    "temperature": t,
                    "humidity": h,
                    "wind": w,
                    "condition": condition
                }
                # publish in separate thread to avoid blocking UI
                topic = f"weather/{sanitize_topic(city)}"
                threading.Thread(
                    target=self.mqtt.publish,
                    args=(topic, json.dumps(payload)),
                    daemon=True
                ).start()

        # schedule next update
        self.root.after(self.update_interval, self.update_loop)

    def _update_graph(self):
        if not self.time_history:
            return
        # Convert times to formatted strings for x-axis
        times = [t.strftime("%H:%M:%S") for t in self.time_history]
        temps = list(self.temp_history)

        # Clear the previous plot
        self.ax.clear()
        
        # Plot new data with both line and points
        self.ax.plot(range(len(temps)), temps, color="#d9534f", linewidth=2, marker='o', 
                    markersize=4, markerfacecolor='white')
        
        # Set title and labels
        self.ax.set_title(f"Temperature (°C) - {self.graphed_city}")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("°C")
        
        # Set axis limits with fixed range to show small changes better
        latest_temp = temps[-1] if temps else 0
        # Set y-axis to ±1°C around the current temperature
        y_min = latest_temp - 1
        y_max = latest_temp + 1
        self.ax.set_xlim(0, max(len(temps) - 1, DEFAULT_HISTORY))
        self.ax.set_ylim(y_min, y_max)
        
        # Update x-axis ticks with timestamps
        if len(times) > 1:
            step = max(1, len(times) // 6)
            xticks = list(range(0, len(times), step))
            self.ax.set_xticks(xticks)
            self.ax.set_xticklabels([times[i] for i in xticks], rotation=30)
        
        # Add grid
        self.ax.grid(alpha=0.25)
        
        # Adjust layout to prevent label cutoff
        self.fig.tight_layout()
        
        # Redraw the canvas
        self.canvas.draw()


def parse_args():
    p = argparse.ArgumentParser(description="Virtual IoT Weather Station GUI")
    p.add_argument("--mqtt", action="store_true", help="Enable MQTT publishing (requires paho-mqtt)")
    p.add_argument("--broker", default="localhost", help="MQTT broker host (default: localhost)")
    p.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    p.add_argument("--client-id", default="virtual-weather-client", help="MQTT client id")
    p.add_argument("--headless", action="store_true", help="Run without GUI, publishing data to MQTT/file")
    p.add_argument("--cities", help="Comma-separated city names (required in headless mode)")
    p.add_argument("--interval", type=int, default=2000, help="Update interval in milliseconds (default: 2000)")
    p.add_argument("--log-file", help="Log file to append JSON messages (optional)")
    return p.parse_args()


class HeadlessWeatherSimulator:
    """Headless version that publishes simulated data without a GUI."""
    
    def __init__(self, cities, mqtt_client=None, update_interval=2000, log_file=None):
        self.cities = cities
        self.mqtt = mqtt_client
        self.update_interval = update_interval
        self.log_file = log_file
        self._running = False
        
    def _simulate_data(self):
        """Generate simulated readings for all cities."""
        for city in self.cities:
            t = round(random.uniform(10.0, 35.0) + random.uniform(-1.5, 1.5), 1)
            h = round(random.uniform(20.0, 90.0), 1)
            w = round(random.uniform(0.0, 65.0), 1)
            condition = get_weather_condition(t, h)
            
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "city": city,
                "temperature": t,
                "humidity": h,
                "wind": w,
                "condition": condition
            }
            
            # MQTT publish if enabled
            if self.mqtt and self.mqtt.is_connected():
                topic = f"weather/{sanitize_topic(city)}"
                threading.Thread(
                    target=self.mqtt.publish,
                    args=(topic, json.dumps(payload)),
                    daemon=True
                ).start()
            
            # Log to file if enabled
            if self.log_file:
                try:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(payload) + '\n')
                except Exception as e:
                    print(f"Error writing to log file: {e}")
            
            # Always print to stdout for monitoring
            print(f"{city}: {t}°C, {h}%, {w}km/h {condition}")
    
    def start(self):
        """Start the simulation loop."""
        self._running = True
        try:
            print(f"Starting headless simulation for cities: {', '.join(self.cities)}")
            print(f"Update interval: {self.update_interval}ms")
            if self.mqtt:
                print(f"Publishing to MQTT broker: {self.mqtt.host}:{self.mqtt.port}")
            if self.log_file:
                print(f"Logging to file: {self.log_file}")
            
            while self._running:
                self._simulate_data()
                time.sleep(self.update_interval / 1000.0)
        except KeyboardInterrupt:
            print("\nStopping simulation...")
        finally:
            self._running = False
    
    def stop(self):
        """Stop the simulation loop."""
        self._running = False

def main():
    args = parse_args()
    
    # Validate headless mode arguments
    if args.headless and not args.cities:
        print("Error: --cities is required in headless mode")
        return 1
    
    mqtt_client = None
    if args.mqtt:
        try:
            from mqtt_client import MqttClient
            mqtt_client = MqttClient(host=args.broker, port=args.port, client_id=args.client_id)
            mqtt_client.connect()
        except Exception as e:
            print("MQTT could not be initialized:", e)
            mqtt_client = None
    
    if args.headless:
        # Run in headless mode
        cities = [c.strip() for c in args.cities.split(",") if c.strip()]
        simulator = HeadlessWeatherSimulator(
            cities=cities,
            mqtt_client=mqtt_client,
            update_interval=args.interval,
            log_file=args.log_file
        )
        simulator.start()
    else:
        # Run GUI mode
        root = Tk()
        app = WeatherApp(root, mqtt_client=mqtt_client, update_interval=args.interval)
        root.geometry("820x520")
        root.mainloop()


if __name__ == "__main__":
    main()
