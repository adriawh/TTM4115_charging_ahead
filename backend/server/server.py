import json
import random

import stmpy
import logging

import paho.mqtt.client as mqtt

from backend.helperClasses.charger import Charger
from backend.helperClasses.station import Station

MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'charging_ahead/queue/server_input'
MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/server_output'
MQTT_TOPIC_DASHBOARD_UPDATE = 'charging_ahead/dashboard/update'


class Server:
    def __init__(self):
        """
        Start the server.

        ## Start of MQTT
        We subscribe to the topic(s) the component listens to.
        The client is available as variable `self.client` so that subscriptions
        may also be changed over time if necessary.

        The MQTT client reconnects in case of failures.
        """

        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        self.stations = {
            1: Station(station_id=1, area_id=1, station_name="Sluppen", area_name="Trondheim", num_chargers=4),
            2: Station(station_id=2, area_id=1, station_name="Lade", area_name="Trondheim", num_chargers=4),
            3: Station(station_id=3, area_id=2, station_name="Sandvika", area_name="Oslo", num_chargers=8),
            4: Station(station_id=4, area_id=1, station_name="Øya", area_name="Trondheim", num_chargers=4)
        }

        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)

        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        self.mqtt_client.subscribe(MQTT_TOPIC_INPUT)
        self.mqtt_client.loop_start()

        self.stm_driver = stmpy.Driver()
        self.stm_driver.start(keep_active=True)
        self._logger.debug('Server initialization finished')

        self.init_dashboard()

    def on_connect(self, client, userdata, flags, rc):
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            return

        command = payload.get('command')
        self._logger.debug('Command in message is {}'.format(command))

        try:
            if command == 'status_available_charger':
                data = self.get_available_chargers(payload)
                self.publish_command(data)

            elif command == 'register_to_queue':
                data = self.register_to_queue(payload)
                self.publish_command(data)

            elif command == 'unregister_from_queue':
                self.unregister_from_queue(payload)

            elif command == 'charger_connected':
                self.charger_connected(payload)

            elif command == 'charger_available':
                self.charger_available(payload)

            elif command == 'out_of_order':
                self.charger_out_of_order(payload)

            self.update_dashboard(payload.get('station_id'))


        except Exception as err:
            self._logger.error('Invalid arguments to command. {}'.format(err))

    def get_available_chargers(self, payload):
        search_string = payload.get('search_string', '').lower()
        matching_stations = []

        for station in self.stations.values():
            if search_string in station.station_name.lower() or search_string in station.area_name.lower():
                matching_stations.append({
                    'id': station.id,
                    'name': station.station_name,
                    'availableChargers': self.get_num_available_chargers(station.id),
                    'queue': list(station.queue),
                    'chargers': [charger.serialize() for charger in station.chargers.values()]
                })

        if matching_stations:
            return {
                'command': 'available_chargers',
                'stations': matching_stations
            }
        else:
            return {
                'command': 'available_chargers',
                'message': 'No matching station or area found.'
            }

    def register_to_queue(self, payload):
        car_id = payload.get('car_id')
        station = self.stations.get(payload.get('station_id'))

        if self.get_num_available_chargers(station.id) > 0:

            charger_id = self.get_random_available_charger(station)

            data = {
                'command': 'charger_assigned', 'car_id': car_id, 'charger_id': charger_id
            }

            charger = station.chargers[charger_id]
            charger.car_id = car_id
            charger.assigned = True

            self._logger.debug(
                f"There are { self.get_num_available_chargers(station.id)} chargers left at station {station.id}")
        else:
            station.add_to_queue(car_id)

            data = {
                'command': 'registered_in_queue', 'car_id': car_id, 'position': len(station.queue)
            }
            self._logger.debug(f'No chargers available, your position is {len(station.queue)}')

        return data

    def unregister_from_queue(self, payload):
        car_id = payload.get('car_id')
        station = self.stations.get(payload.get('station_id'))

        # If the element is assigned to a charger, remove it
        for charger in station.chargers.values():
            if charger.car_id == car_id:
                charger.car_id = None
                charger.charging = False
                charger.assigned = False

        # If the element is in the queue, remove it
        station.remove_element(car_id)

        self._logger.debug(f'car {car_id} is now removed')

    def charger_connected(self, payload):
        charger_id = payload.get('charger_id')
        station = self.stations.get(int(payload.get('station_id')))

        station.chargers[charger_id].charging = True

        self._logger.debug(
            f"Charger {charger_id} has been connected to car {station.chargers.get(charger_id).car_id}")

    def charger_available(self, payload):
        station = self.stations.get(payload.get('station_id'))
        charger_id = payload.get('charger_id')

        if charger_id not in station.chargers:
            charger = Charger(charger_id)
            station.chargers.update({charger_id: charger})

        charger = station.chargers[charger_id]
        charger.operational = True

        car_id = station.chargers[charger_id].car_id

        if car_id is not None:
            self._logger.debug(f"Charger {charger_id} has been disconnected from {car_id} and is now free")
            charger.car_id = None
            charger.charging = False
            charger.assigned = False

        if len(station.queue) > 0:

            car_id = station.queue.popleft()
            charger_id = self.get_random_available_charger(station)

            charger = station.chargers[charger_id]
            charger.car_id = car_id
            charger.assigned = True

            self._logger.debug(f'Car {car_id} has been assigned charger {charger_id}')

            data = {
                'command': 'charger_assigned', 'car_id': car_id, 'charger_id': charger_id, 'queue': list(station.queue)
            }

            self.publish_command(data)

    def charger_out_of_order(self, payload):
        station = self.stations.get(payload.get('station_id'))
        charger = station.chargers[payload.get('charger_id')]
        charger.operational = False

    def update_dashboard(self, station_id):
        station = self.stations.get(int(station_id))

        chargers = [charger.serialize() for charger in station.chargers.values()]
        dashboard_update = {
            'id': station.id,
            'stationName': station.station_name,
            'availableChargers':  self.get_num_available_chargers(station.id),
            'unavailableChargers': station.unavailable_chargers,
            'queue': list(station.queue),
            'chargers': chargers
        }

        self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))

    def init_dashboard(self):
        data = []
        for station in self.stations.values():
            chargers = [charger.serialize() for charger in station.chargers.values()]
            dashboard_update = {
                'id': station.id,
                'stationName': station.station_name,
                'availableChargers': self.get_num_available_chargers(station.id),
                'unavailableChargers': station.unavailable_chargers,
                'queue': list(station.queue),
                'queueLength': len(station.queue),
                'chargers': chargers
            }
            data.append(dashboard_update)

        self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(data))

    def publish_command(self, command):
        payload = json.dumps(command)
        print("server", payload)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, payload=payload)

    def get_random_available_charger(self, station):
        charger = random.choice([
            v for k, v in station.chargers.items() if not v.assigned and v.operational
        ])

        return charger.id

    def get_num_available_chargers(self, station_id):
        station = self.stations.get(station_id)
        available_chargers = 0
        for charger in station.chargers.values():
            if not charger.assigned and charger.operational:
                available_chargers += 1
        return available_chargers

    def stop(self):
        self.mqtt_client.loop_stop()
        self.stm_driver.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    server = Server()
