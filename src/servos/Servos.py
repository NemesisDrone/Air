import threading
import time
from typing import List

from utilities import component as component, ipc
from time import sleep
import os
import json
import pigpio
os.system("pigpiod")


class ServosComponent(component.Component):
    """
    This component is responsible for controlling the servos

    """
    NAME = "servos"

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        self.pi = pigpio.pi()
        self.nb_canals = 10

        self.alive = False

    def start(self):
        self.alive = True

        self.redis.set("servos:canal:1", 180)

        for i in range(1, self.nb_canals + 1):
            angle = self.redis.get(f"servos:canal:{i}")
            if not angle:
                continue
            # Get the gpio of the servo from the config
            canal = json.loads(self.redis.get(f"config:canal:{i}"))
            gpios: List[int] = canal["gpios"]

            if len(gpios) == 0:
                continue
            # Set all servos to their middle position
            for gpio in gpios:
                self.pi.set_servo_pulsewidth(gpio, 1500)

        threading.Thread(target=self.servos_work, daemon=True).start()

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
            angle = self.redis.get(f"servos:canal:{i}")
            if not angle:
                continue
            # Get the gpio of the servo from the config
            canal = json.loads(self.redis.get(f"config:canal:{i}"))
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
