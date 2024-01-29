import json
import threading
from typing import List, Union

from air.utilities import component, ipc
import time
import pigpio
import os


class PropulsionComponent(component.Component):
    """
    This component is responsible for controlling the ESC.
    Redis key used :
     - propulsion:speed: The desired speed of the ESC
     - propulsion:armed: The state of the ESC

    """
    NAME = "propulsion"

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        self.alive = False
        self.thread = threading.Thread(target=self._propulsion_work)

        os.system("pigpiod")
        time.sleep(3)

        self.pi = pigpio.pi()

        self.min_value = 1225
        self.max_value = 1800

        self.is_armed = False
        self.redis.set("propulsion:armed", int(self.is_armed))

    def _arm(self):
        """
        This method is used to arm the ESC
        """
        self.logger.warning("[ESC] Arming ESC", self.NAME)

        for i in range(1, 11):
            brushless_config = self._get_canal_config(i)

            gpios: List[int] = brushless_config["gpios"]
            if len(gpios) == 0:
                continue

            for gpio in gpios:
                self.pi.set_servo_pulsewidth(gpio, 0)
                time.sleep(0.05)
                """
                TEST if this is necessary to arm the ESC.
                For the moment it doesn't seem to be necessary
                """
                # self.pi.set_servo_pulsewidth(gpio, self.max_value)
                # time.sleep(1)
                # self.pi.set_servo_pulsewidth(gpio, self.min_value)
                # time.sleep(1)
        self.logger.warning("[ESC] ESCs ARMED | READY FOR DEPARTURE", self.NAME)
        self.redis.set("propulsion:speed", 0)
        self.is_armed = True
        self.redis.set("propulsion:armed", int(self.is_armed))

    @ipc.Route(["propulsion:arm"], False).decorator
    def call_arm(self, call_data: ipc.CallData, payload: dict):
        self._arm()

    @ipc.Route(["propulsion:disarm"], False).decorator
    def disarm(self, call_data: ipc.CallData, payload: dict):
        """
        This method is used to disarm the ESC
        """
        self.logger.warning("[ESC] Disarming ESCs", self.NAME)

        for i in range(1, 11):
            brushless_config = self._get_canal_config(i)

            gpios: List[int] = brushless_config["gpios"]
            if len(gpios) == 0:
                continue

            for gpio in gpios:
                self.pi.set_servo_pulsewidth(gpio, 0)
                time.sleep(0.05)

        self.is_armed = False
        self.redis.set("propulsion:armed", int(self.is_armed))

    @ipc.Route(["propulsion:speed"], True).decorator
    def set_speed(self, call_data: ipc.CallData, payload: dict):
        """
        This method is used to set the speed of the ESC
        """
        self.logger.info(f"[ESC] Setting speed to {payload}", self.NAME)
        self.redis.set("propulsion:speed", json.dumps(payload))

    def _calculate_pulsewidth(self, value: float) -> float:
        """
        This method is used to calculate the pulsewidth from a value between 0 and 100
        """
        if value <= 1:
            return 800
        return self.min_value + value * (self.max_value - self.min_value) / 100

    def _get_canal_config(self, canal: int) -> Union[dict, None]:
        """
        This method is used to get the canal config from the redis database
        """
        config: bytes = self.redis.get(f"config:brushless:canal:{canal}")
        if not config:
            return None
        return json.loads(config)

    def _get_rc_channels(self) -> Union[dict, None]:
        """
        This method is used to get the rc channels from the redis database
        """
        channels: bytes = self.redis.get("rc:channels")
        if not channels:
            return None
        return json.loads(channels)

    def _propulsion_work(self):
        """
        This method is used to control the ESC.
        The desired speed is saved on the Redis database and is recovered here.
        """
        self.logger.info("[ESC] Starting propulsion work", self.NAME)
        while self.alive:
            if self.is_armed:
                channels = self._get_rc_channels()
                if not channels:
                    continue

                for i in range(1, 11):
                    brushless_config = self._get_canal_config(i)

                    gpios: List[int] = brushless_config["gpios"]
                    if len(gpios) == 0:
                        continue

                    value = self._calculate_pulsewidth(channels[str(i)])

                    for gpio in gpios:
                        self.pi.set_servo_pulsewidth(gpio, value)
                        print(value, flush=True)
                        time.sleep(0.05)
            else:
                # Disarm all the ESC
                for i in range(1, 11):
                    brushless_config = self._get_canal_config(i)

                    gpios: List[int] = brushless_config["gpios"]
                    if len(gpios) == 0:
                        continue

                    for gpio in gpios:
                        self.pi.set_servo_pulsewidth(gpio, 0)
                        time.sleep(0.05)

    def start(self):
        self._arm()
        self.alive = True
        self.thread.start()

    def stop(self):
        self.alive = False
        self.thread.join()
        self.disarm()
        self.pi.stop()