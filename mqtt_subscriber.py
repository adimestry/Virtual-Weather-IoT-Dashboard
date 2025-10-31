#!/usr/bin/env python3
"""Simple MQTT subscriber used to verify messages from the virtual weather app.

Usage:
    python mqtt_subscriber.py --broker test.mosquitto.org --port 1883 --topic "weather/#" --count 10 --timeout 30
"""
import argparse
import time
import threading

try:
    import paho.mqtt.client as mqtt
except Exception as e:
    raise SystemExit("paho-mqtt is required to run the subscriber. Install with: pip install paho-mqtt")

args_parser = argparse.ArgumentParser()
args_parser.add_argument("--broker", default="test.mosquitto.org")
args_parser.add_argument("--port", type=int, default=1883)
args_parser.add_argument("--topic", default="weather/#")
args_parser.add_argument("--count", type=int, default=10, help="Number of messages to collect before exiting")
args_parser.add_argument("--timeout", type=int, default=30, help="Max seconds to wait before exiting")
args = args_parser.parse_args()

received = 0
received_lock = threading.Lock()


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker {args.broker}:{args.port}")
        client.subscribe(args.topic)
        print(f"Subscribed to {args.topic}")
    else:
        print(f"Failed to connect, rc={rc}")


def on_message(client, userdata, msg):
    global received
    with received_lock:
        received += 1
        idx = received
    try:
        payload = msg.payload.decode('utf-8')
    except Exception:
        payload = repr(msg.payload)
    print(f"[{idx}] {msg.topic} -> {payload}")
    if idx >= args.count:
        # disconnect from broker
        def stop():
            client.disconnect()
        threading.Thread(target=stop, daemon=True).start()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(args.broker, args.port, 60)
client.loop_start()

start = time.time()
while True:
    with received_lock:
        if received >= args.count:
            break
    if time.time() - start > args.timeout:
        print(f"Timeout reached ({args.timeout}s). Exiting.")
        break
    time.sleep(0.2)

client.loop_stop()
print("Subscriber exiting")
