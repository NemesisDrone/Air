from utilities import component as component, ipc
import time
import pigpio
import os

from utilities.ipc import route


class PropulsionComponent(component.Component):
    """
    This component is responsible for controlling the ESC.
    Redis key used :
     - propulsion:speed: The desired speed of the ESC
     - propulsion:armed: The state of the ESC

    """
    NAME = "propulsion"

    def __init__(self):
        super().__init__()

        os.system("pigpiod")
        time.sleep(3)

        self.ESC_PIN = 13
        self.pi = pigpio.pi()
        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)

        self.min_value = 700
        self.max_value = 2500

        self.is_armed = False
        self.r.set("propulsion:armed", int(self.is_armed))

        self.log("Propulsion component initialized")

    def start(self):
        self.log("Propulsion component started")

    def calibrate(self, payload=None):
        """
        This method is used to calibrate the ESC.
        """
        self.is_armed = False
        self.r.set("propulsion:armed", int(self.is_armed))
        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
        self.log("[ESC] Disconnect the battery NOW and wait 7 seconds", ipc.LogLevels.WARNING)
        time.sleep(7)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.max_value)
        self.log(
            "[ESC] Connect the battery NOW.. Two beeps and a falling tone. Wait for 7 seconds",
            ipc.LogLevels.WARNING
        )
        time.sleep(7)

        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.min_value)
        self.log("[ESC] Wait for 12 seconds", ipc.LogLevels.WARNING)
        time.sleep(12)

        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
        self.log("[ESC] Wait for 2 seconds", ipc.LogLevels.WARNING)
        time.sleep(2)

        self.log("[ESC] Arming ESC", ipc.LogLevels.WARNING)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.min_value)
        time.sleep(1)

        self.log("[ESC] ESC ARMED | READY FOR DEPARTURE", ipc.LogLevels.WARNING)
        self.is_armed = True
        self.r.set("propulsion:armed", int(self.is_armed))

    @route("propulsion:calibrate")
    def call_calibrate(self, payload=None):
        self.calibrate()

    def arm(self):
        """
        This method is used to arm the ESC
        """
        self.log("[ESC] Arming ESC", ipc.LogLevels.WARNING)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
        time.sleep(1)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.max_value)
        time.sleep(1)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, self.min_value)
        time.sleep(1)
        self.log("[ESC] ESC ARMED | READY FOR DEPARTURE", ipc.LogLevels.WARNING)
        self.r.set("propulsion:speed", 0)
        self.is_armed = True
        self.r.set("propulsion:armed", int(self.is_armed))

    @route("propulsion:arm")
    def call_arm(self, payload=None):
        self.arm()

    @route("propulsion:disarm")
    def disarm(self, payload=None):
        """
        This method is used to disarm the ESC
        """
        self.log("[ESC] Disarming ESC", ipc.LogLevels.WARNING)
        self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
        self.is_armed = False
        self.r.set("propulsion:armed", int(self.is_armed))

    @route("propulsion:speed")
    def set_speed(self, payload):
        """
        This method is used to set the speed of the ESC
        """
        self.log(f"[ESC] Setting speed to {payload}", ipc.LogLevels.INFO)
        self.r.set("propulsion:speed", payload)

    def propulsion_work(self):
        """
        This method is used to control the ESC.
        The desired speed is saved on the Redis database and is recovered here.
        """
        self.log("[ESC] Starting propulsion work", ipc.LogLevels.INFO)
        while True:
            if self.is_armed:
                desired_speed = self.r.get("propulsion:speed")
                if desired_speed is not None:
                    desired_speed = int(desired_speed)
                else:
                    desired_speed = 0

                self.pi.set_servo_pulsewidth(self.ESC_PIN, desired_speed)
                time.sleep(0.05)
            else:
                self.pi.set_servo_pulsewidth(self.ESC_PIN, 0)
                time.sleep(0.05)

    def stop(self):
        self.disarm()
        self.pi.stop()
        self.log("Propulsion component stopped")


def run():
    compo = PropulsionComponent()
    compo.start()
    compo.arm()
    compo.propulsion_work()
