from utilities import component as component, ipc
import time
import board
import busio
import adafruit_vl53l0x


class LaserDistanceComponent(component.Component):
    """
    This component is responsible for reading the laser distance sensor and sending the distance on redis IPC.
    Redis key: sensor:laser-distance
    IPC route: sensor:laser-distance
    """
    NAME = "laser-distance"

    def __init__(self):
        super().__init__()

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.vl53 = adafruit_vl53l0x.VL53L0X(self.i2c)

        self.send_laser_distance = False
        self.last_running_status_sent = 0
        self.log("Laser distance component initialized")

    def start(self):
        self.log("Laser component started")
        self.send_laser_distance = True

    def do_work(self):
        """
        The do_work method is the main method in charge of getting the laser distance and sending it on redis IPC.
        """
        try:
            with self.vl53.continuous_mode():
                while self.send_laser_distance:
                    # Get a measurement
                    laser_distance = self.vl53.range

                    # Send the measurement on redis IPC and save it in redis db
                    self.send("sensor:laser-distance", laser_distance)
                    self.r.set("sensor:laser-distance", laser_distance)
                    self.log(f"laser distance: {laser_distance}")
                    # Send the running status every 5 seconds
                    if time.time() - self.last_running_status_sent > 5:
                        self.send("state:laser-distance:running", True)
                        self.last_running_status_sent = time.time()

                    # limit the frequency of the laser distance sensor
                    time.sleep(0.05)
        except Exception as e:
            self.log("Laser component stopped working", level=ipc.LogLevels.ERROR)
            self.send("state:laser-distance:running", False)

    def stop(self):
        self.send_laser_distance = False
        self.log("Laser component stopped")


def run():
    compo = LaserDistanceComponent()
    compo.start()
    compo.do_work()

