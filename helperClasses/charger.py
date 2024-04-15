class Charger:
    def __init__(self, charger_id):
        self.id = charger_id
        self.car_id = None
        self.operational = True
        self.charging = False
        self.assigned = False

    def serialize(self):
        return {
            'id': self.id,
            'car_id': self.car_id,
            'operational': self.operational,
            'charging': self.charging,
            'assigned': self.assigned
        }