
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

    def on_connect(self, client, userdata, flags, rc):
        # we just log that we are connected
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        pass

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
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()

        self.create_gui()

    def create_gui(self):
        self.app = gui()

        def extract_car_name(label):
            label = label.lower()
            if 'tesla model x' in label: return 'tesla model x'
            if 'tesla model y' in label: return 'tesla model y'
            if 'tesla model 3' in label: return 'tesla model 3'
            return None

        def extract_type_id(label):
            label = label.lower()
            if 'area' in label: return '1'
            if 'station' in label: return '1'
            return None

        def publish_command(command):
            payload = json.dumps(command)
            self._logger.info(command)
            self.mqtt_client.publish(MQTT_TOPIC_INPUT, payload=payload, qos=2)

        self.app.startLabelFrame('Adding cars to queue:')
        def on_button_pressed_queue(title):
            car_id = extract_car_name(title)
            station_id = 1
            command = {"command": "queue", "station_id": station_id, "car_id": car_id}
            publish_command(command)

        self.app.addButton('Add Tesla Model x to queue', on_button_pressed_queue)
        self.app.addButton('Add Tesla Model y to queue', on_button_pressed_queue)
        self.app.addButton('Add Tesla Model 3 to queue', on_button_pressed_queue)
        self.app.stopLabelFrame()


        self.app.startLabelFrame('Asking for available chargers:')
        def on_button_pressed_status(title):
            name = extract_type_id(title)
            command = {"command": "status_available_charger", "station_id": name}
            publish_command(command)

        self.app.addButton('Get available chargers on area 1', on_button_pressed_status)
        self.app.addButton('Get available chargers on station 1', on_button_pressed_status)
        self.app.stopLabelFrame()

        self.app.go()


    def stop(self):
        """
        Stop the component.
        """
        # stop the MQTT client
        self.mqtt_client.loop_stop()



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
