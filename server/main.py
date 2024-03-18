import json
import stmpy
import logging
from collections import deque

import paho.mqtt.client as mqtt

MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'charging_ahead/queue/command'
MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/answer'


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

        # Create an instance of the queue

        self.queueObject = Queue()
        self.queue = self.queueObject.queue

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
                    s = f"There are {self.available_charger} available charger on station: {payload.get('station_id')}"
                elif payload.get('area_id'):
                    s = f"Here are the available chargers for {payload.get('area_id')}"

                self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)
            elif command == 'queue':
                car_id = payload.get('car_id')
                # Find queue
                self._logger.debug(f"Length of the queue {len(self.queue)}")

                if self.available_charger > 0:
                    # Charger available. Return charger id
                    s = 'Available charger.'
                    self.available_charger -= 1

                else:
                    self.queueObject.add_to_queue(car_id)
                    # No chargers are available. Return position in queue
                    s = f'No chargers available, your position is {len(self.queue)})'

                self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)

            elif command == 'charger_disconnected':
                charger_id = payload.get('charger_id')
                if len(self.queue) > 0:
                    new_id = self.queue.popleft()
                    s = f'Car {new_id} has been assigned charger {charger_id}'
                    self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)
                else:
                    self._logger.debug(f"Charger {charger_id} available")
                    self.available_charger += 1

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


class Queue:
    def __init__(self):
        self.queue = deque()

    def add_to_queue(self, id):
        self.queue.append(id)

    def remove_from_queue(self):
        self.queue.popleft()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    server = Server()
