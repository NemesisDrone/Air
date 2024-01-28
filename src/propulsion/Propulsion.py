import json
import threading
from typing import List

from utilities import component, ipc
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

        self.ESC_PIN = 13
        self.pi = pigpio.pi()
        # self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)

        self.min_value = 1225
        self.max_value = 1800

        self.is_armed = False
        self.redis.set("propulsion:armed", int(self.is_armed))

    def calibrate(self):
        """
        This method is used to calibrate the ESC.
        """
        self.is_armed = False
        self.redis.set("propulsion:armed", int(self.is_armed))
        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
        self.logger.warning("[ESC] Disconnect the battery NOW and wait 7 seconds", self.NAME)
        time.sleep(7)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.max_value)
        self.logger.warning(
            "[ESC] Connect the battery NOW.. Two beeps and a falling tone. Wait for 7 seconds",
            self.NAME,
        )
        time.sleep(7)

        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.min_value)
        self.logger.warning("[ESC] Wait for 12 seconds", self.NAME)
        time.sleep(12)

        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
        self.logger.warning("[ESC] Wait for 2 seconds", self.NAME)
        time.sleep(2)

        self.logger.warning("[ESC] Arming ESC", self.NAME)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.min_value)
        time.sleep(1)

        self.logger.warning("[ESC] ESC ARMED | READY FOR DEPARTURE", self.NAME)
        self.is_armed = True
        self.redis.set("propulsion:armed", int(self.is_armed))

    @ipc.Route(["propulsion:calibrate"], False).decorator
    def call_calibrate(self, call_data: ipc.CallData, payload: dict):
        self.calibrate()

    def arm(self):
        """
        This method is used to arm the ESC
        """
        self.logger.warning("[ESC] Arming ESC", self.NAME)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
        time.sleep(1)
        # TEST if this is necessary to arm the ESC
        # self.pi.set_servo_pulsewidth(self.ESC_PIN, self.max_value)
        # time.sleep(1)
        # self.pi.set_servo_pulsewidth(self.ESC_PIN, self.min_value)
        # time.sleep(1)

        self.logger.warning("[ESC] ESC ARMED | READY FOR DEPARTURE", self.NAME)
        self.redis.set("propulsion:speed", 0)
        self.is_armed = True
        self.redis.set("propulsion:armed", int(self.is_armed))

    @ipc.Route(["propulsion:arm"], False).decorator
    def call_arm(self, call_data: ipc.CallData, payload: dict):
        self.arm()

    @ipc.Route(["propulsion:disarm"], False).decorator
    def disarm(self, call_data: ipc.CallData, payload: dict):
        """
        This method is used to disarm the ESC
        """
        self.logger.warning("[ESC] Disarming ESC", self.NAME)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
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
            return 0
        return self.min_value + value * (self.max_value - self.min_value) / 100

    def _propulsion_work(self):
        """
        This method is used to control the ESC.
        The desired speed is saved on the Redis database and is recovered here.
        """
        self.logger.info("[ESC] Starting propulsion work", self.NAME)
        while self.alive:
            if self.is_armed:
                channels = self.redis.get("rc:channels")
                if not channels:
                    return
                channels = json.loads(channels)
                print(channels)

                for i in range(1, 11):
                    brushless_config: bytes = self.redis.get(f"config:brushless:canal:{i}")
                    if not brushless_config:
                        return
                    brushless_config: dict = json.loads(brushless_config)

                    gpios: List[int] = brushless_config["gpios"]
                    if len(gpios) == 0:
                        continue

                    value = self._calculate_pulsewidth(channels[str(i)])
                    print(value, flush=True)
                    for gpio in gpios:
                        self.pi.set_servo_pulsewidth(13, value)
                        print(value, flush=True)
                        time.sleep(0.05)
            else:
                self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
                time.sleep(0.05)

    def start(self):
        self.arm()
        self.alive = True
        self.thread.start()

    def stop(self):
        self.alive = False
        self.thread.join()
        self.disarm()
        self.pi.stop()
