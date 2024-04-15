import random
import string

import paho.mqtt.client as mqtt
import logging
import json
from appJar import gui

MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'charging_ahead/queue/command'
MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/answer'


class ChargingDetailsSenderComponent:
    """
    The component to simulate the dashboard of a car.
    """

    def __init__(self):
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe(MQTT_TOPIC_OUTPUT)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()

        self.create_gui()

    def on_connect(self, client, userdata, flags, rc):
        # we just log that we are connected
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
            if command == 'available_chargers':
                self.app.setLabel('info_label', payload.get('message'))


        except Exception as err:
            self._logger.error('Invalid arguments to command. {}'.format(err))

    def create_gui(self):
        self.app = gui()

        def publish_command(command):
            payload = json.dumps(command)
            self._logger.info(command)
            self.mqtt_client.publish(MQTT_TOPIC_INPUT, payload=payload, qos=2)

        def on_button_pressed_queue():
            car_id = generate_random_id()
            station_id = 1
            command = {"command": "register_to_queue", "station_id": station_id, "car_id": car_id}
            publish_command(command)

        def on_button_pressed_status_area():
            area_id = self.app.getEntry("area_input")
            command = {"command": "status_available_charger", "area_id": str(area_id)}
            publish_command(command)

        def on_button_pressed_status_station():
            station_id = self.app.getEntry("station_input")
            command = {"command": "status_available_charger", "station_id": str(station_id)}
            publish_command(command)

        self.app.startLabelFrame('Adding cars to queue:')
        self.app.addButton('Add a car to queue', on_button_pressed_queue)

        self.app.stopLabelFrame()

        self.app.startLabelFrame('Asking for available chargers:')

        self.app.addLabelEntry("area_input")
        self.app.addButton("Check Area Status", on_button_pressed_status_area)

        self.app.addLabelEntry("station_input")
        self.app.addButton("Check Station Status", on_button_pressed_status_station)
        self.app.stopLabelFrame()

        self.app.startLabelFrame('Info:')
        self.app.addLabel('info_label', '', row=1)  # Add an empty label to display info
        self.app.stopLabelFrame()

        self.app.go()

    def stop(self):
        """
        Stop the component.
        """
        # stop the MQTT client
        self.mqtt_client.loop_stop()


def generate_random_id():
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(10))


if __name__ == "__main__":
    debug_level = logging.DEBUG
    logger = logging.getLogger(__name__)
    logger.setLevel(debug_level)
    ch = logging.StreamHandler()
    ch.setLevel(debug_level)
    formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    t = ChargingDetailsSenderComponent()
