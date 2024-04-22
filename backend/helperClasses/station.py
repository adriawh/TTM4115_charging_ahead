from collections import deque

from backend.helperClasses.charger import Charger


class Station:
    def __init__(self, station_id, area_id, station_name, area_name, num_chargers):
        self.id = station_id
        self.area_id = area_id
        self.station_name = station_name
        self.area_name = area_name
        self.queue = deque()
        self.num_chargers = num_chargers
        self.available_chargers = num_chargers
        self.unavailable_chargers = 0
        self.chargers = self.init_chargers()

    def init_chargers(self):
        chargers = dict()
        for i in range(self.num_chargers):
            chargers.update({i: Charger(i)})

        return chargers

    def add_to_queue(self, id):
        self.queue.append(id)

    def remove_from_queue(self):
        self.queue.popleft()

    def remove_element(self, element):
        new_dq = deque()
        removed = False
        for item in self.queue:
            if item == element and not removed:
                removed = True
                continue
            new_dq.append(item)
        return new_dq