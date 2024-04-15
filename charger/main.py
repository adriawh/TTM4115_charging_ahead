import json
import stmpy
import random
import string
import paho.mqtt.client as mqtt


# TODO: choose proper MQTT broker address
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'charging_ahead/queue/command'
MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/answer'




class Car_logic:
    def __init__(self, duration, component):
        
        self.id = self.generate_random_id(10)
        self.duration = duration
        self.component = component
        self.car_id = None
        
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)  # MQTTv311 corresponds to version 3.1.1
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

        self.client.loop_start()
        
        transitions = [
            {'source': 'initial', 'target': 'waiting', 'effect': 'waiting'},
            {'trigger': 'failure', 'source': 'waiting', 'target':'out_of_order', 'effect': 'out_of_order'},
            {'trigger': 'start_service', 'source': 'out_of_order', 'target': 'under_service'},
            {'trigger': 'finish_service', 'source': 'under_service', 'target': 'waiting', 'effect': 'waiting'},
            {'trigger': 'server_book', 'source': 'waiting', 'target': 'booked'},
            {'trigger': 'charger_connected', 'source': 'booked', 'target': 'in_use', 'effect': 'charger_connected'},
            {'trigger': 'charger_disconnected', 'source': 'in_use', 'target': 'waiting', 'effect': 'effect'},
        ]

        self.stm = stmpy.Machine(name=self.name, transitions=transitions, obj=self)


    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker with result code "+str(rc))
        client.subscribe(MQTT_TOPIC_INPUT)


    def on_message(self, client, userdata, msg):
        print('Received message: {}'.format(msg.payload))
        payload = json.loads(msg.payload.decode('utf-8'))
        command = payload.get('command')

        if command == 'charger_assigned':
            if payload.get('charger_id') != self.id:
                self.car_id = payload.get('car_id')
                print('Charger assigned with car: {}'.format(self.car_id))
                self.stm_driver._stms_by_id.get(self.stm.id).send('server_book')
        elif command == 'stop_engine':
            self.stm.send('stop_charging')
        else:
            self._logger.warning('Unknown command: {}'.format(command))

    def waiting(self):
        # TODO self.led("green")
        data = {
            'command': 'charger_available', 
            'charger_id': self.id, 
            'station_id': 1,  
        }
        self.client.publish(MQTT_TOPIC_INPUT, json.dumps(data))
       
    def charger_connected(self):
        # TODO led("red")
        print("Charger connected")
        data = {
            'command': 'charger_connected', 
            'charger_id': self.id, 
            'station_id': 1,  
        }
        self.client.publish(MQTT_TOPIC_INPUT, json.dumps(data))
    
    def out_of_order(self):
        print("Out of order")
        data = {
            'command': 'out_of_order', 
            'charger_id': self.id, 
            'station_id': 1,  
        }
        self.client.publish(MQTT_TOPIC_INPUT, json.dumps(data))
