from utilities import component as component
import time
import random


class GPSComponent(component.Component):
    NAME = "gps"

    def __init__(self):
        super().__init__()
        self.send_gps_position = False
        self.last_running_status_sent = 0
        self.log("GPS component initialized")

    def start(self):
        self.log("GPS component started")
        self.send_gps_position = True

    def do_work(self):
        while self.send_gps_position:
            lat = -0.7563779 + random.uniform(-0.001, 0.001)
            lng = 48.0879123 + random.uniform(-0.001, 0.001)
            self.send("sensor:gps", {"lat": lat, "lng": lng})
            time.sleep(1)

            if time.time() - self.last_running_status_sent > 5:
                self.send("state:gps:running", True)
                self.last_running_status_sent = time.time()

    def stop(self):
        self.send_gps_position = False
        self.log("GPS component stopped")


def run():
    compo = GPSComponent()
    compo.start()
    compo.do_work()

