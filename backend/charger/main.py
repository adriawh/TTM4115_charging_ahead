import json
import stmpy
import random
import string
import logging
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO


# TODO: choose proper MQTT broker address
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_SERVER_INPUT = 'charging_ahead/queue/server_input'
MQTT_TOPIC_SERVER_OUTPUT = 'charging_ahead/queue/server_output'

red = 4
yellow = 22
green = 9
charger_pin = 21
service_button = 7


class charger_logic:
    def __init__(self, duration):
        self._logger = logging.getLogger(__name__)

        self.id = self.generate_random_id(10)
        self.duration = duration
        self.car_id = None
        
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)  # MQTTv311 corresponds to version 3.1.1
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

        self.client.loop_start()
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(red, GPIO.OUT)
        GPIO.setup(yellow, GPIO.OUT)
        GPIO.setup(green, GPIO.OUT)
        
        GPIO.setup(service_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(service_button, GPIO.FALLING, callback=self.button, bouncetime=100)
        
        GPIO.setup(charger_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(charger_pin, GPIO.BOTH, callback=self.charger, bouncetime=500)



        
        transitions = [
            {'source': 'initial', 'target': 'disconnected'},
            {'trigger': 'mqtt_connected','source': 'disconnected', 'target': 'waiting', 'effect': 'waiting'},
            {'trigger': 'button', 'source': 'waiting', 'target':'out_of_order', 'effect': 'out_of_order'},
            {'trigger': 'button', 'source': 'out_of_order', 'target': 'waiting', 'effect': 'waiting'},
            {'trigger': 'server_book', 'source': 'waiting', 'target': 'booked', 'effect': 'booked'},
            {'trigger': 'charger_connected', 'source': 'booked', 'target': 'in_use', 'effect': 'charger_connected'},
            {'trigger': 'charger_disconnected', 'source': 'in_use', 'target': 'waiting', 'effect': 'waiting'},
            {'trigger': 'failure', 'source': 'in_use', 'target': 'out_of_order', 'effect': 'out_of_order'},
            {'trigger': 'failure', 'source': 'booked', 'target': 'out_of_order', 'effect': 'out_of_order'},
        ]

        self.stm = stmpy.Machine(name=self.id, transitions=transitions, obj=self)
        self.stm_driver = stmpy.Driver()
        self.stm_driver.add_machine(self.stm)
        self.stm_driver.start(keep_active=True)


    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker with result code "+str(rc))
        client.subscribe(MQTT_TOPIC_SERVER_OUTPUT)
        self.stm_driver._stms_by_id.get(self.stm.id).send('mqtt_connected')

        
    def on_message(self, client, userdata, msg):
        print('Received message: {}'.format(msg.payload))
        payload = json.loads(msg.payload.decode('utf-8'))
        command = payload.get('command')

        if command == 'charger_assigned':
            if payload.get('charger_id') == self.id:
                self.car_id = payload.get('car_id')
                print('Charger assigned with car: {}'.format(self.car_id))
                self.stm_driver._stms_by_id.get(self.stm.id).send('server_book')
        elif command == 'stop_engine':
            self.stm.send('stop_charging')
        else:
            self._logger.warning('Unknown command: {}'.format(command))

    def waiting(self):
        print("waiting")
        self.green_light()
        data = {
            'command': 'charger_available', 
            'charger_id': self.id, 
            'station_id': 1,  
        }
        self.client.publish(MQTT_TOPIC_SERVER_INPUT, json.dumps(data))
       
    def booked(self):
        self.yellow_light()
        
    def charger_connected(self):
        self.yellow_light()
        print("Charger connected")
        data = {
            'command': 'charger_connected', 
            'charger_id': self.id, 
            'station_id': 1,  
        }
        self.client.publish(MQTT_TOPIC_SERVER_INPUT, json.dumps(data))
    
    def out_of_order(self):
        self.red_light()
        print("Out of order")
        data = {
            'command': 'out_of_order', 
            'charger_id': self.id, 
            'station_id': 1,  
        }
        self.client.publish(MQTT_TOPIC_SERVER_INPUT, json.dumps(data))
        
    def generate_random_id(self, length):
            letters_and_digits = string.ascii_letters + string.digits
            return ''.join(random.choice(letters_and_digits) for _ in range(length))

    
    def red_light(self):
        GPIO.output(red, GPIO.HIGH)
        GPIO.output(yellow, GPIO.LOW)
        GPIO.output(green, GPIO.LOW)

    def yellow_light(self):
        GPIO.output(red, GPIO.LOW)
        GPIO.output(yellow, GPIO.HIGH)
        GPIO.output(green, GPIO.LOW)

    def green_light(self):
        GPIO.output(red, GPIO.LOW)
        GPIO.output(yellow, GPIO.LOW)
        GPIO.output(green, GPIO.HIGH)

    def off_light(self):
        GPIO.output(red, GPIO.LOW)
        GPIO.output(yellow, GPIO.LOW)
        GPIO.output(green, GPIO.LOW)
    
    def charger(self, channel):
        if GPIO.input(channel) == True:
            self.stm_driver._stms_by_id.get(self.stm.id).send('charger_disconnected')
            print("Charger unplugged")
        else:
            self.stm_driver._stms_by_id.get(self.stm.id).send('charger_connected')
            print("Charger plugged")
            
    def button(self, channel):
        self.stm_driver._stms_by_id.get(self.stm.id).send('button')

            
        
car_stm = charger_logic(10)
