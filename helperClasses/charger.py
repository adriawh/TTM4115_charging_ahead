class Charger:
    def __init__(self, charger_id):
        self.id = charger_id
        self.car_id = None
        self.operational = True
        self.charging = False