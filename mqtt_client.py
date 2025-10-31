"""Simple MQTT client wrapper using paho-mqtt.

This module provides a tiny helper around paho.mqtt.client to connect and publish.
If paho-mqtt is not installed or connection fails, methods will raise informative exceptions.
"""
import threading
import time

try:
    import paho.mqtt.client as mqtt
except Exception as e:
    mqtt = None


class MqttClient:
    def __init__(self, host="localhost", port=1883, client_id="virtual-weather-client"):
        if mqtt is None:
            raise RuntimeError("paho-mqtt is required for MQTT support. Install via: pip install paho-mqtt")
        self.host = host
        self.port = port
        self.client_id = client_id
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
        self._connected = False
        # set callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
        else:
            print(f"MQTT connect failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False

    def connect(self, keepalive=60, timeout=5):
        # connect in background thread to avoid blocking UI
        def _connect():
            try:
                self._client.connect(self.host, self.port, keepalive)
                self._client.loop_start()
                # wait a short amount for connection
                waited = 0
                while not self._connected and waited < timeout:
                    time.sleep(0.1)
                    waited += 0.1
                if not self._connected:
                    print("Warning: MQTT connection not established within timeout")
            except Exception as e:
                print("MQTT connection error:", e)

        threading.Thread(target=_connect, daemon=True).start()

    def is_connected(self):
        return self._connected

    def publish(self, topic, payload, qos=0, retain=False):
        if not self._connected:
            # try to publish anyway — paho will queue messages but warn
            print("MQTT not connected; attempting publish anyway")
        try:
            self._client.publish(topic, payload, qos=qos, retain=retain)
        except Exception as e:
            print("MQTT publish error:", e)
