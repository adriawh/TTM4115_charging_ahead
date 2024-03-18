import paho.mqtt.client as mqtt
import stmpy
import logging
from threading import Thread
import json
import random
import string


# TODO: choose proper MQTT broker address
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'charging_ahead/queue/command'
MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/answer'


class CarStateMachine:
    def __init__(self, duration):
        self._logger = logging.getLogger(__name__)
        self.duration = duration
        self.name = self.generate_random_id(10)


        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)  # MQTTv311 corresponds to version 3.1.1
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

        self.client.loop_start()

        t0 = {'trigger': 'register', 'source': 'initial', 'target': 'in_queue', 'effect': 'register_for_queue'}
        t1 = {'trigger': 'start_charging', 'source': 'in_queue', 'target': 'charging', 'effect': 'start_charging'}
        t2 = {'trigger': 'stop_charging', 'source': 'charging', 'target': 'charge_complete', 'effect': 'stop_charging'}
        t3 = {'trigger': 'disconnect', 'source': 'in_queue', 'target': 'disconnected', 'effect': 'disconnect'}
        t4 = {'trigger': 'disconnect', 'source': 'charging', 'target': 'disconnected', 'effect': 'disconnect'}
        t5 = {'trigger': 'disconnect', 'source': 'charge_complete', 'target': 'disconnected', 'effect': 'disconnect'}

        self.stm = stmpy.Machine(name=self.name, transitions=[t0, t1, t2, t3, t4, t5], obj=self)
        self.stm_driver = stmpy.Driver()
        self.stm_driver.add_machine(self.stm)
        self.stm_driver.start(keep_active=True)

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker with result code "+str(rc))
        client.subscribe(MQTT_TOPIC_OUTPUT)

    def on_message(self, client, userdata, msg):
        print('Received message: {}'.format(msg.payload))
        payload = json.loads(msg.payload.decode('utf-8'))
        command = payload.get('command')

        if command == 'start_engine':
            self.stm.send('start_charging')
        elif command == 'stop_engine':
            self.stm.send('stop_charging')
        else:
            self._logger.warning('Unknown command: {}'.format(command))

    def start_charging(self):
        print('Starting charging')
        self.client.publish(MQTT_TOPIC_OUTPUT, 'Starting charging')
        # Perform charging logic here

    def stop_charging(self):
        print('Stopping charging')
        self.client.publish(MQTT_TOPIC_OUTPUT, 'Stopping charging')
        # Perform stop charging logic here

    def disconnect(self):
        print('Disconnecting')
        self.client.publish(MQTT_TOPIC_OUTPUT, 'Disconnecting')
        # Perform disconnect logic here

    def register_for_queue(self):
        print('Registering for queue')
        self.client.publish("queue", "register")
        
    def generate_random_id(self, length):
            letters_and_digits = string.ascii_letters + string.digits
            return ''.join(random.choice(letters_and_digits) for _ in range(length))


car_stm = CarStateMachine(10)