import time
from typing import List

from utilities import component as component, ipc
from time import sleep
import os
import json
import pigpio
os.system("pigpiod")
from utilities.ipc import route


class ServosComponent(component.Component):
    """
    This component is responsible for controlling the servos

    """
    NAME = "servos"

    def __init__(self):
        super().__init__()

        self.pi = pigpio.pi()
        self.nb_canals = 10

        self.alive = False

    def start(self):
        self.log("Servos component started")
        self.alive = True

        self.r.set("servos:canal:1", 180)

        for i in range(1, self.nb_canals + 1):
            angle = self.r.get(f"servos:canal:{i}")
            if not angle:
                continue
            # Get the gpio of the servo from the config
            canal = json.loads(self.r.get(f"config:canal:{i}"))
            gpios: List[int] = canal["gpios"]

            if len(gpios) == 0:
                continue
            # Set all servos to their middle position
            for gpio in gpios:
                self.pi.set_servo_pulsewidth(gpio, 1500)

    @staticmethod
    def calculate_pulsewidth_from_angle(angle: float) -> float:
        """
        This method is used to calculate the pulsewidth from an angle.
        The minimum pulsewidth is 500 and the maximum is 2500
        """
        # return int(angle / )
        return 500 + angle * 2000 / 180

    def update_angles(self) -> None:
        """
        This method is used to update the angles of the all servos, based on the redis values
        """
        for i in range(1, self.nb_canals + 1):
            angle = self.r.get(f"servos:canal:{i}")
            if not angle:
                continue
            # Get the gpio of the servo from the config
            canal = json.loads(self.r.get(f"config:canal:{i}"))
            gpios: List[int] = canal["gpios"]

            if len(gpios) == 0:
                continue

            # Change the angle of the servo
            for gpio in gpios:
                self.pi.set_servo_pulsewidth(gpio, self.calculate_pulsewidth_from_angle(float(angle)))

    def servos_work(self):
        while self.alive:
            self.update_angles()
            time.sleep(0.005)

    def stop(self):
        self.pi.stop()
        self.log("Servos component stopped")


def run():
    compo = ServosComponent()
    compo.start()
    compo.servos_work()


if __name__ == "__main__":
    run()
