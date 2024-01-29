import threading
import time
from typing import List, Union

from air.utilities import component as component, ipc
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
    def _calculate_pulsewidth_from_angle(angle: float) -> float:
        """
        This method is used to calculate the pulsewidth from an angle.
        The minimum pulsewidth is 500 and the maximum is 2500
        """
        # return int(angle / )
        return 500 + angle * 2000 / 180

    def _get_canal_config(self, canal: int) -> Union[dict, None]:
        """
        This method is used to get the canal config from redis
        """
        data: bytes = self.redis.get(f"config:servos:canal:{canal}")
        if not data:
            return None
        return json.loads(data)

    def _get_rc_channels(self) -> Union[dict, None]:
        """
        This method is used to get the rc channels from redis
        """
        data: bytes = self.redis.get("channels")
        if not data:
            return None
        return json.loads(data)

    def _update_angles(self) -> None:
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
        channels = self._get_rc_channels()
        # TODO: Change condition when autonome mode is implemented
        if not channels:
            return

        for i in range(1, self.nb_canals + 1):
            # Get canal gpios
            canal = self._get_canal_config(i)
            if not canal:
                continue

            gpios: List[int] = canal["gpios"]
            if len(gpios) == 0:
                continue

            # TODO: handle manual or autonome
            angle = self._calculate_pulsewidth_from_angle(
                channels[str(i)]
            )
            for gpio in gpios:
                self.pi.set_servo_pulsewidth(gpio, angle)

    def servos_work(self):
        while self.alive:
            self._update_angles()

    def stop(self):
        self.pi.stop()
