import paho.mqtt.client as mqtt
import json

# Configuration
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883
MQTT_TOPIC_DASHBOARD_UPDATE = 'charging_ahead/dashboard/update'


class DashboardClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.stations = {}

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        self.client.subscribe(MQTT_TOPIC_DASHBOARD_UPDATE)

    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        self.process_update(payload)

    def process_update(self, payload):
        action = payload.get('action')
        station_id = payload.get('station_id')

        # Update internal state based on the action
        if action in ['queue_update', 'charger_update']:
            self.stations[station_id] = {
                'available_chargers': payload.get('available_chargers'),
                'queue_length': payload.get('queue_length')
            }

        # After processing the update, print the current state
        self.print_dashboard()

    def print_dashboard(self):
        print("\nCurrent Status of Charging Stations:")
        for station_id, info in self.stations.items():
            print(
                f"Station {station_id}: {info['available_chargers']} chargers available, {info['queue_length']} cars in queue")
        print("-" * 50)

    def run(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_forever()


if __name__ == "__main__":
    dashboard = DashboardClient()
    dashboard.run()
