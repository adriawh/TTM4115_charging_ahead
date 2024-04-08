import json
import random

import stmpy
import logging
from collections import deque

import paho.mqtt.client as mqtt

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
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        # Create an instance of the charging stations

        self.stations = {
            1: Station(station_id=1, area_id=1, num_chargers=3),
            2: Station(station_id=2, area_id=1, num_chargers=2)
        }


        # Hold available chargers
        self.available_charger = 5

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe(MQTT_TOPIC_INPUT)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()

        # we start the stmpy driver, without any state machines for now
        self.stm_driver = stmpy.Driver()
        self.stm_driver.start(keep_active=True)
        self._logger.debug('Server initialization finished')

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
                data = None
                if payload.get('station_id'):
                    station = self.stations.get(int(payload.get('station_id')))
                    data = {'command': 'available_chargers', 'message': f"There are {station.available_chargers} available charger on station: {station.station_id}" }
                    self._logger.debug(f"There are {station.available_chargers} available charger on station: {station.station_id}")

                elif payload.get('area_id'):
                    stations_area = []
                    for station in self.stations.values():
                        if station.area_id == int(payload.get('area_id')):
                            stations_area.append(station)

                    data = {'command': 'available_chargers', 'message': f"There are {len(stations_area)} stations available in the area" }
                    self._logger.debug(f"There are {len(stations_area)} stations available in the area")

                self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json.dumps(data))

            elif command == 'register_to_queue':
                car_id = payload.get('car_id')
                station = self.stations.get(payload.get('station_id'))

                if station.available_chargers > 0:

                    charger_id = self.get_random_available_charger(station)

                    data = {
                        'command': 'charger_assigned', 'car_id': car_id, 'charger_id': charger_id
                    }
                    station.available_chargers -= 1

                    station.chargers[charger_id].car_id = car_id

                    self._logger.debug(f"There are {station.available_chargers} chargers left at station {station.station_id}")
                else:
                    station.add_to_queue(car_id)

                    data = {
                        'command': 'registered_in_queue', 'car_id': car_id, 'position': len(station.queue)
                    }
                    self._logger.debug(f'No chargers available, your position is {len(station.queue)}')

                self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json.dumps(data))

                dashboard_update = {
                    'action': 'queue_update',
                    'station_id': station.station_id,
                    'available_chargers': station.available_chargers,
                    'queue_length': len(station.queue)
                }
                self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))

            elif command == 'unregister_from_queue':
                car_id = payload.get('car_id')
                station = self.stations.get(payload.get('station_id'))

                station.remove_element(car_id)

                self._logger.debug(f'car {car_id} is now removed from queue')

                dashboard_update = {
                    'station_id': station.station_id,
                    'available_chargers': station.available_chargers,
                    'queue_length': len(station.queue),
                    #'assigned_chargers': station.chargers

                }
                self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))

            elif command == 'charger_disconnect':
                car_id = payload.get('car_id')
                charger_id = payload.get('charger_id')
                station = self.stations.get(int(payload.get('station_id')))

                station.chargers[charger_id].car_id = None
                station.chargers[charger_id].charging = False

                self._logger.debug(f"Charger {charger_id} has been disconnected from {car_id} and is now free")

                if len(station.queue) > 0:
                    new_id = station.queue.popleft()
                    self._logger.debug(f'Car {new_id} has been assigned charger {charger_id}')

                    station.chargers[charger_id].car_id = car_id
                    station.chargers[charger_id].charging = False

                    data = {
                        'command': 'charger_assigned', 'car_id': car_id, 'charger_id': charger_id
                    }

                else:
                    self._logger.debug(f"Charger {charger_id} available")
                    self.available_charger += 1


                self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json.dumps(data))


                dashboard_update = {
                    'action': 'charger_update',
                    'station_id': station.station_id,
                    'available_chargers': station.available_chargers,
                    'queue_length': len(station.queue)
                }

                self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))

            elif command == 'charger_connect':
                charger_id = payload.get('charger_id')
                station = self.stations.get(int(payload.get('station_id')))

                self._logger.debug(f"Charger {charger_id} has been connected to car {station.chargers.get(charger_id).car_id}")
                station.chargers[charger_id].charging = True

                dashboard_update = {
                    'station_id': station.station_id,
                    'available_chargers': station.available_chargers,
                    'queue_length': len(station.queue),
                    #'assigned_chargers': station.chargers

                }
                self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))


        except Exception as err:
            self._logger.error('Invalid arguments to command. {}'.format(err))

    def get_random_available_charger(self, station):
        charger = random.choice([
            v for k, v in station.chargers.items() if not v.charging
        ])

        return charger.id



    def stop(self):
        """
        Stop the component.
        """
        # stop the MQTT client
        self.mqtt_client.loop_stop()

        # stop the state machine Driver
        self.stm_driver.stop()


class Station:
    def __init__(self, station_id, area_id, num_chargers):
        self.station_id = station_id
        self.area_id = area_id
        self.queue = deque()
        self.num_chargers = num_chargers
        self.available_chargers = num_chargers
        self.chargers = self.init_chargers()


    def init_chargers(self):
        chargers = dict()
        for i in range(self.num_chargers):
            chargers.update({i: Charger(i)})

        return chargers

    def add_to_queue(self, id):
        self.queue.append(id)

    def remove_from_queue(self):
        self.queue.popleft()


    def remove_element(self, element):
        new_dq = deque()
        removed = False
        for item in self.queue:
            if item == element and not removed:
                removed = True
                continue
            new_dq.append(item)
        return new_dq


class Charger:
    def __init__(self, charger_id):
        self.id = charger_id
        self.car_id = None
        self.operational = True
        self.charging = False

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    server = Server()
    """
        charging_ahead/queue/command - {command: status_available_charger, station_id: 1} (expect 3)
        charging_ahead/queue/command - {command: status_available_charger, area_id: 1} (expect 2)
        charging_ahead/queue/command - {command: "queue", station_id: 1, car_id: 1} (expect 2 chargers left)
        charging_ahead/queue/command - {command: "queue", station_id: 1, car_id: 2} (expect 1 charger left)
        charging_ahead/queue/command - {command: "queue", station_id: 1, car_id: 3} (expect 0 charger left)
        charging_ahead/queue/command - {command: "queue", station_id: 1, car_id: 4} (expect queue len 1)
        charging_ahead/queue/command - {command: "charger_disconnected", station_id: 1 ,charger_id:1} (expect queue len 0)
        charging_ahead/queue/command - {command: "charger_disconnected", station_id: 1 ,charger_id:1} (expect 1 available charger)
    """
