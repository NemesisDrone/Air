import threading
import time

from utilities import component as component
from sense_hat import SenseHat


class SensorsComponent(component.Component):
    NAME = "sensors"

    def __init__(self):
        super().__init__()
        self.log("Sensors component initialized")

        self.alive = False

        self.hat = SenseHat()
        self.hat.set_imu_config(1, 1, 1)
        self.hat._init_humidity()
        self.hat._init_pressure()

    def main(self):
        while self.alive:
            self.hat._imu.IMURead()
            self.log(f"{self.hat._imu.getIMUData()}")
            time.sleep(0.1)

    def start(self):
        self.alive = True
        threading.Thread(target=self.main).start()
        self.log("Sensors component started")

    def stop(self):
        self.alive = False
        self.log("Sensors component stopped")


def run():
    SensorsComponent().start()
