import json
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
                s = ''
                if payload.get('station_id'):
                    station = self.stations.get(int(payload.get('station_id')))
                    s = f"There are {station.available_chargers} available charger on station: {station.station_id}"
                    self._logger.debug(f"There are {station.available_chargers} available charger on station: {station.station_id}")


                elif payload.get('area_id'):
                    stations_area = []
                    for station in self.stations.values():
                        if station.area_id == int(payload.get('area_id')):
                            stations_area.append(station)

                    s = f"There are {len(stations_area)} stations available in the area"
                    self._logger.debug(f"There are {len(stations_area)} stations available in the area")

                self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)
            elif command == 'queue':
                car_id = payload.get('car_id')
                station = self.stations.get(int(payload.get('station_id')))

                if car_id in station.queue:
                    position = station.queue.index(
                        car_id) + 1
                    s = f'You are already in the queue, your position is {position}.'
                    self._logger.debug(f'Car {car_id} is already in the queue, position {position}.')

                elif station.available_chargers > 0:
                    # Charger available. Return charger id
                    s = 'You are assigned charger..'
                    station.available_chargers -= 1
                    self._logger.debug(f"There are {station.available_chargers} chargers left at station {station.station_id}")
                else:
                    station.add_to_queue(car_id)
                    # No chargers are available. Return position in queue
                    s = f'No chargers available, your position is {len(station.queue)}'
                    self._logger.debug(f'No chargers available, your position is {len(station.queue)}')

                self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)

                dashboard_update = {
                    'action': 'queue_update',
                    'station_id': station.station_id,
                    'available_chargers': station.available_chargers,
                    'queue_length': len(station.queue)
                }
                self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))

            elif command == 'charger_disconnected':
                self._logger.debug(f"Charger has been disconnected")
                charger_id = payload.get('charger_id')
                station = self.stations.get(int(payload.get('station_id')))
                if len(station.queue) > 0:
                    new_id = station.queue.popleft()
                    s = f'Car {new_id} has been assigned charger {charger_id}'
                    self._logger.debug(f"There length of the queue: {len(station.queue)}")
                    self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)
                else:
                    self._logger.debug(f"Charger {charger_id} available")
                    self.available_charger += 1

                dashboard_update = {
                    'action': 'charger_update',
                    'station_id': station.station_id,
                    'available_chargers': station.available_chargers,
                    'queue_length': len(station.queue)
                }
                self.mqtt_client.publish(MQTT_TOPIC_DASHBOARD_UPDATE, json.dumps(dashboard_update))

            #Add more checks as start_charging, stop_charging... Use the driver object and call the methods. Now the state Car state machine is independent.
            #The server handles initalizaton of Car state machine objects, which means that the state machine itself does not have to communicate directly.

        except Exception as err:
            self._logger.error('Invalid arguments to command. {}'.format(err))

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

    def add_to_queue(self, id):
        self.queue.append(id)

    def remove_from_queue(self):
        self.queue.popleft()


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
