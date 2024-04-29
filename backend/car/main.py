import paho.mqtt.client as mqtt
import stmpy
import logging
from threading import Thread
import json
import random
import string
import RPi.GPIO as GPIO


# TODO: choose proper MQTT broker address
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_SERVER_INPUT = 'charging_ahead/queue/server_input'
MQTT_TOPIC_SERVER_OUTPUT = 'charging_ahead/queue/server_output'

register_button = 17
charger_pin = 21
pulled_down_pin = 20


class CarStateMachine:
    def __init__(self, duration):
        self._logger = logging.getLogger(__name__)
        self.duration = duration
        self.id = self.generate_random_id(10)
        self.charger_id = None

        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)  # MQTTv311 corresponds to version 3.1.1
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

        self.client.loop_start()

        transitions = [
            {'source': 'initial', 'target': 'disconnected'},
            {'trigger': 'register', 'source': 'disconnected', 'target': 'in_queue', 'effect': 'register_for_queue'},
            {'trigger': 'assigned_charger', 'source': 'disconnected', 'target': 'assigned'},
            {'trigger': 'register', 'source': 'in_queue', 'target': 'disconnected', 'effect': 'unregister_from_queue'},
            {'trigger': 'charger_connected', 'source': 'in_queue', 'target': 'charging', 'effect': 'charger_connected'},
            {'trigger': 'charger_disconnected', 'source': 'charging', 'target': 'disconnected'},
        ]

        self.stm = stmpy.Machine(name=self.id, transitions=transitions, obj=self)
        self.stm_driver = stmpy.Driver()
        self.stm_driver.add_machine(self.stm)
        self.stm_driver.start(keep_active=True)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(register_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(register_button, GPIO.FALLING, callback=self.button_press, bouncetime=500)

        
        GPIO.setup(charger_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(charger_pin, GPIO.BOTH, callback=self.charger, bouncetime=500)

        GPIO.setup(pulled_down_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker with result code "+str(rc))
        client.subscribe(MQTT_TOPIC_SERVER_OUTPUT)

    def on_message(self, client, userdata, msg):
        print('Received message: {}'.format(msg.payload))
        payload = json.loads(msg.payload.decode('utf-8'))
        command = payload.get('command')

        if command == 'charger_assigned':
            if payload.get('car_id') == self.id:
                self.charger_id = payload.get('charger_id')
                print('Charger assigned: {}'.format(self.charger_id))
                self.stm_driver._stms_by_id.get(self.stm.id).send('assigned_charger')
        elif command == 'registered_in_queue':
            position = payload.get('position')
            print('Position in queue: {}'.format(position))

        else:
            self._logger.warning('Unknown command: {}'.format(command))

    def charger_connected(self):
        print('Starting charging')
        data = {
            'command': 'charger_connected',
            'charger_id': self.charger_id,
            'station_id': 1,
        }
        self.client.publish(MQTT_TOPIC_SERVER_INPUT, json.dumps(data))
        
    def charger_disconnecd(self):
        print('Disconnecting')
        data = {
            'command': 'charger_disconnected',
            'charger_id': self.charger_id,
            'station_id': 1,
        }
        self.client.publish(MQTT_TOPIC_SERVER_INPUT, json.dumps(data))
        self.charger_id =  None

    def register_for_queue(self):
        print('Registering for queue')
        data = {
            'command': 'register_to_queue',
            'car_id': self.id,
            'station_id': 1,
        }
        self.client.publish(MQTT_TOPIC_SERVER_INPUT, json.dumps(data))

    def unregister_from_queue(self):
        print('Unregistering from queue')
        data = {
            'command': 'unregister_from_queue',
            'car_id': self.id,
            'station_id': 1,
        }
        self.client.publish(MQTT_TOPIC_SERVER_INPUT, json.dumps(data))

    def generate_random_id(self, length):
            letters_and_digits = string.ascii_letters + string.digits
            return ''.join(random.choice(letters_and_digits) for _ in range(length))

    def button_press(self, channel):
        self.stm_driver._stms_by_id.get(self.stm.id).send('register')

    def charger(self, channel):
        if GPIO.input(channel) == True:
            self.stm_driver._stms_by_id.get(self.stm.id).send('charger_disconnected')
            print("Charger unplugged")
        else:
            self.stm_driver._stms_by_id.get(self.stm.id).send('charger_connected')
            print("Charger plugged")


car_stm = CarStateMachine(10)