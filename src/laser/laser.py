import json

from utilities import component as component, ipc
import time
import board
import busio
import adafruit_vl53l0x


class LaserComponent(component.Component):
    """
    This component is responsible for reading the laser distance sensor and sending the distance on redis IPC.
    Redis key: sensors:laser-distance
    IPC route: sensors:laser-distance
    """
    NAME = "laser"

    def __init__(self):
        super().__init__()

        self.valid = True
        self.alive = False

        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.vl53 = adafruit_vl53l0x.VL53L0X(self.i2c)
        except Exception as e:
            self.log(f"Could not initialize laser: {e}", level=ipc.LogLevels.WARNING)
            self.valid = False

        self.r.set("state:laser:custom", json.dumps({"valid": self.valid, "alive": self.alive}))
        self.send("state:laser:custom", {"valid": self.valid, "alive": self.alive})
        self.log("Laser component initialized")

    def start(self):
        if self.valid:
            self.alive = True

        return self

    def do_work(self):
        """
        The do_work method is the main method in charge of getting the laser distance and sending it on redis IPC.
        """
        self.r.set("state:laser:custom", json.dumps({"valid": self.valid, "alive": self.alive}))
        self.send("state:laser:custom", {"valid": self.valid, "alive": self.alive})

        if not self.alive:
            return

        try:
            with self.vl53.continuous_mode():
                while self.alive:
                    # Get a measurement
                    laser_distance = self.vl53.range

                    # Send the measurement on redis IPC and save it in redis db
                    self.send("sensors:laser:distance", laser_distance)
                    self.r.set("sensors:laser:distance", laser_distance)

                    # limit the frequency of the laser distance sensor
                    time.sleep(0.05)

        except Exception as e:
            self.log("Laser component stopped unexpectedly: " + str(e), level=ipc.LogLevels.ERROR)
            self.alive = False
            self.valid = False

        self.r.set("state:laser:custom", json.dumps({"valid": self.valid, "alive": self.alive}))
        self.send("state:laser:custom", {"valid": self.valid, "alive": self.alive})

    def stop(self):
        self.alive = False
        self.log("Laser component stopped")


def run():
    compo = LaserComponent().start()
    compo.log("Laser component started")
    compo.do_work()
