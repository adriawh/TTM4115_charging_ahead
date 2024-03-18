from stmpy import Driver, Machine
from threading import Thread

import paho.mqtt.client as mqtt

import json

class Game:
    def on_init(self):
        print("Init!")

    def buzzer(self):
        string = "Buzzed"
        print(string)
        self.mqtt_client.publish(string)

    def timeout(self):
        string = "Timeout"
        print(string)
        self.mqtt_client.publish(string)
    
    def timer_start(self):
        print("Timer on!")
        self.stm.start_timer("t", 20000)
        self.mqtt_client.publish("game start")


# initial transition
t0 = {"source": "initial", "target": "timer_off", "effect": "on_init"}

t1 = {
    "trigger": "master_button",
    "source": "timer_off",
    "target": "timer_on",
    "effect": 'timer_start',
}

t2 = {
    "trigger": "participant_button",
    "source": "timer_on",
    "target": "timer_off",
    "effect": "buzzer",
}

t3 = {
    "trigger": "t",
    "source": "timer_on",
    "target": "timer_off",
    "effect": "timeout",
}



class MQTT_Client_1:
    def __init__(self):
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)  
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print("on_connect(): {}".format(mqtt.connack_string(rc)))

    def on_message(self, client, userdata, msg):
        print("on_message(): topic: {}".format(msg.topic))
        #decode the message to json
        # make string to json

        object = json.loads(msg.payload.decode("utf-8"))
        message = object.get("msg")
        player = object.get("player")

        
        if message == "mb":
            print("Master button pressed by player, {}".format(player))
            self.stm_driver.send("master_button", "game")
        elif message == "pb":
            print("Participant button pressed by player, {}".format(player))
            self.stm_driver.send("participant_button", "game")

    def start(self, broker, port):

        print("Connecting to {}:{}".format(broker, port))
        self.client.connect(broker, port)

        self.client.subscribe("ttm4115/gr20")

        try:
            # line below should not have the () after the function!
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            print("Interrupted")
            self.client.disconnect()
            # broker, port = 'iot.eclipse.org', 1883
broker, port = "broker.hivemq.com", 1883

game = Game()
game_machine = Machine(transitions=[t0, t1, t2, t3], obj=game, name="game")

game.stm = game_machine

driver = Driver()
driver.add_machine(game_machine)

myclient = MQTT_Client_1()
game.mqtt_client = myclient.client
myclient.stm_driver = driver

driver.start()
myclient.start(broker, port)