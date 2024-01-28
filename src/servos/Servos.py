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

        # Set all servos to 90 degrees
        for i in range(1, self.nb_canals + 1):
            self.redis.set(f"servos:canal:{i}", 90)

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
        """
        Reminder: 
        Channels is a dict of the form:
        {
            "1": 0,
            "2": 0,
            "3": 0,
            "4": 0,
            "5": 0,
            "6": 0,
            "7": 0,
            "8": 0,
            "9": 0,
            "10": 0,
        }
        """
        channels = self.redis.get("rc:channels")
        if not channels:
            return
        channels = json.loads(channels)
        for i in range(1, self.nb_canals + 1):
            # Get canal gpios
            data: bytes = self.redis.get(f"config:servos:canal:{i}")
            if not data:
                return
            data: dict = json.loads(data)

            gpios: List[int] = data["gpios"]
            if len(gpios) == 0:
                continue

            angle = channels[str(i)]
            # angle = float(self.redis.get(f"servos:canal:{i}"))
            angle = self.calculate_pulsewidth_from_angle(angle)
            for gpio in gpios:
                self.pi.set_servo_pulsewidth(gpio, angle)

    def servos_work(self):
        while self.alive:
            self.update_angles()

    def stop(self):
        self.pi.stop()
