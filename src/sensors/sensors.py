import threading
import time

from utilities import component as component
from utilities.sense_hat import SenseHat


class SensorsComponent(component.Component):
    NAME = "sensors"

    def __init__(self):
        super().__init__()
        self.log("Sensors component initialized")

        self.alive = False

        self.hat = SenseHat()
        self.hat.set_imu_config(True, True, True)

    def main(self):
        while self.alive:
            self.log(f"{self.hat.get_orientation()}")
            time.sleep(1)

    def start(self):
        self.alive = True
        threading.Thread(target=self.main).start()
        self.log("Sensors component started")

    def stop(self):
        self.alive = False
        self.log("Sensors component stopped")


def run():
    SensorsComponent().start()
