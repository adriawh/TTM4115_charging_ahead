import stmpy
import random
import string


# TODO: choose proper MQTT broker address
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'charging_ahead/queue/command'
MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/answer'


class Car_logic:
    def __init__(self, duration, component):
        
        self.name = self.generate_random_id(10)
        self.duration = duration
        self.component = component
        
        # Transitions
        t0 = {'trigger': 'register', 'source': 'disconnected', 'target': 'in_queue', 'effect': 'register_for_queue'}
        t1 = {'trigger': 'start_charging', 'source': 'in_queue', 'target': 'charging', 'effect': 'start_charging'}
        t2 = {'trigger': 'stop_charging', 'source': 'charging', 'target': 'charge_complete', 'effect': 'stop_charging'}
        t3 = {'trigger': 'disconnect', 'source': ['in_queue', 'charging', 'charge_complete'], 'target': 'disconnected', 'effect': 'disconnect'}

        self.stm = stmpy.Machine(name=self.name, transitions=[t0, t1, t2, t3], obj=self)

    def start_charging(self):
        print("Starting charging")
        # Perform charging logic here

    def stop_charging(self):
        print("Stopping charging")
        # Perform stop charging logic here

    def disconnect(self):
        print("Disconnecting")
        # Perform disconnect logic here
    def generate_random_id(length):
            letters_and_digits = string.ascii_letters + string.digits
            return ''.join(random.choice(letters_and_digits) for _ in range(length))

    def register_for_queue(self):
        print("Registering for queue")
        self.mqtt_client.publish("queue", "register")
        
        
class Car_co:
    