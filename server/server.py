import json
import random

import stmpy
import logging

import paho.mqtt.client as mqtt

from helperClasses import station
from helperClasses.charger import Charger
from helperClasses.station import Station

MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'charging_ahead/queue/command'
MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/answer'
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
            1: Station(station_id=1, area_id=1, num_chargers=3),
            2: Station(station_id=2, area_id=1, num_chargers=2)
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

        for station in self.stations.values():
            self.update_dashboard(station.id)

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
                self.update_dashboard(payload.get('station_id'))

            elif command == 'charger_disconnected':
                data = self.charger_disconnected(payload)
                self.publish_command(data)

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
        data = None
        if payload.get('station_id'):
            station = self.stations.get(int(payload.get('station_id')))
            if station is None:
                self._logger.debug(f"No station exist with the id {payload.get('station_id')}")
                data = {'command': 'available_chargers',
                        'message':  f"No station exist with the id {payload.get('station_id')}"}
            else:
                data = {'command': 'available_chargers',
                        'message': f"There are {station.available_chargers} available charger on station: {station.id}"}
                self._logger.debug(
                    f"There are {station.available_chargers} available charger on station: {station.id}")

        elif payload.get('area_id'):
            stations_area = []
            for station in self.stations.values():
                if station.area_id == int(payload.get('area_id')):
                    stations_area.append(station)
            if len(stations_area) == 0:
                self._logger.debug(f"No stations exist in the area with id: {payload.get('area_id')}")
                data = {'command': 'available_chargers',
                        'message':  f"No station exist with the id {payload.get('station_id')}"}
            else:
                data = {'command': 'available_chargers',
                        'message': f"There are {len(stations_area)} stations available in the area"}
                self._logger.debug(f"There are {len(stations_area)} stations available in the area")

        return data

    def register_to_queue(self, payload):
        car_id = payload.get('car_id')
        station = self.stations.get(payload.get('station_id'))

        if station.available_chargers > 0:

            charger_id = self.get_random_available_charger(station)

            data = {
                'command': 'charger_assigned', 'car_id': car_id, 'charger_id': charger_id
            }

            charger = station.chargers[charger_id]
            charger.car_id = car_id
            charger.assigned = True

            station.available_chargers -= 1

            self._logger.debug(
                f"There are {station.available_chargers} chargers left at station {station.id}")
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

        station.remove_element(car_id)

        self._logger.debug(f'car {car_id} is now removed from queue')

    def charger_disconnected(self, payload):
        charger_id = payload.get('charger_id')
        station = self.stations.get(int(payload.get('station_id')))
        car_id = station.chargers[charger_id].car_id
        charger = station.chargers[charger_id]
        charger.car_id = None
        charger.charging = False
        charger.assigned = False

        self._logger.debug(f"Charger {charger_id} has been disconnected from {car_id} and is now free")

        if len(station.queue) > 0:
            car_id = station.queue.popleft()
            charger_id = self.get_random_available_charger(station)

            charger = station.chargers[charger_id]
            charger.car_id = car_id
            charger.assigned = True

            self._logger.debug(f'Car {car_id} has been assigned charger {charger_id}')

            data = {
                'command': 'charger_assigned', 'car_id': car_id, 'charger_id': charger_id
            }
        else:
            self._logger.debug(f"Charger {charger_id} available")
            station.available_chargers += 1

        return data

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
        else:
            charger = station.chargers[payload.get('charger_id')]
            charger.operational = True

        station.available_chargers += 1

    def charger_out_of_order(self, payload):
        station = self.stations.get(payload.get('station_id'))
        charger = station.chargers[payload.get('charger_id')]
        charger.operational = False
        station.unavailable_chargers -= 1

    def update_dashboard(self, station_id):
        station = self.stations.get(station_id)
        chargers = [charger.serialize() for charger in station.chargers.values()]
        dashboard_update = {
            'station_id': station.id,
            'available_chargers': station.available_chargers,
            'unavailable_chargers': station.unavailable_chargers,
            'queue': list(station.queue),
            'queue_length': len(station.queue),
            'chargers': chargers
        }

        self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))

    def publish_command(self, command):
        payload = json.dumps(command)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, payload=payload)

    def get_random_available_charger(self, station):
        charger = random.choice([
            v for k, v in station.chargers.items() if not v.assigned and v.operational
        ])

        return charger.id

    def stop(self):
        self.mqtt_client.loop_stop()
        self.stm_driver.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    server = Server()
