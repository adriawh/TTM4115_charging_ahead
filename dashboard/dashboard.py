import time

import paho.mqtt.client as mqtt
import json

# Configuration
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883
MQTT_TOPIC_DASHBOARD_UPDATE = 'charging_ahead/dashboard/update'


class DashboardClient:
    def __init__(self):
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        self.client.subscribe(MQTT_TOPIC_DASHBOARD_UPDATE)

    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        self.print_dashboard(payload)

    def print_dashboard(self, payload):
        print(payload)

    def run(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=300)
        self.client.subscribe(MQTT_TOPIC_DASHBOARD_UPDATE)
        self.client.loop_start()

        # Loop indefinitely
        while True:
            try:
                # Do nothing here, just sleep
                time.sleep(1)
            except KeyboardInterrupt:
                print("Script interrupted. Exiting...")
                break


if __name__ == "__main__":
    dashboard = DashboardClient()
    dashboard.run()
