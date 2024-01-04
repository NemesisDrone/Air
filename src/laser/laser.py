import json

from utilities import component as component, ipc
from utilities.ipc import LogLevels as ll
import time
import board
import busio
import adafruit_vl53l0x.VL53L0X as drv
import threading


class LaserState(int):
    """
    Class representing the different states of NVSComponent.
    """
    I2CInitFail: int = 0
    VL53InitFail: int = 1
    Unknown: int = 2
    Initialized: int = 3
    PendingStop: int = 4
    Alive: int = 5


class LaserComponent(component.Component):
    """
    This component is responsible for reading the laser distance sensor and sending the distance on redis IPC.
    Redis key: sensors:laser-distance
    IPC route: sensors:laser-distance
    """

    NAME = "laser"

    def __init__(self):
        super().__init__()

        self._state: int = LaserState.Unknown
        self.i2c: busio.I2C = None
        self.vl53: drv = None
        self.thread: threading.Thread = None

        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
        except Exception as e:
            self.set_laser_state(LaserState.I2CInitFail)
            self.log("Failed to create I2C interface: " + str(e), ll.WARNING)
            return

        if self._state != LaserState.I2CInitFail:
            try:
                self.vl53: drv = drv(self.i2c)
                self.set_laser_state(LaserState.Initialized)
            except Exception as e:
                self.set_laser_state(LaserState.VL53InitFail)
                self.log("Failed to init VL53 Driver: " + str(e), ll.WARNING)
                return

        self.log("Initialized.")


    def __del__(self):
        self.stop()


    def start(self) -> bool:
        """
        Function used to start the component. It will set up a thread and schedule tasks to make the measurements.
        """

        if self._state != LaserState.Initialized:
            self.log("Impossible to start, wrongly initialized.", ll.INFO)
            return False

        self.thread = threading.Thread(target=self._do_work)
        self.thread.start()

        self.log("Started.", ll.INFO)
        return True


    def stop(self) -> None:
        """
        Stops the measurements. It will wait until all the threads are able to stop.
        This means that the function might be blocking for an undetermined amount of time.
        """
        if self._state <= LaserState.PendingStop:
            return

        # Make the measurements loop stop.
        self.set_laser_state(LaserState.PendingStop)
        while self._state >= LaserState.PendingStop:
            pass

        # Make the thread join.
        if self.thread:
            self.thread.join()

        self.log("Stopped.", ll.INFO)


    def _do_work(self) -> None:
        """
        The _do_work method is in charge of getting the laser distance and sending it on Redis IPC.
        """
        self.set_laser_state(LaserState.Alive)

        try:
            # Notice that we don't need to use busio.I2C.try_lock and unlock because we have only one
            # instance running within the program.
            with self.vl53.continuous_mode():
                while self._state == LaserState.Alive:
                    # Get a measurement
                    laser_distance = self.vl53.range

                    # Send the measurement on Redis IPC and save it in Redis DB.
                    self.send("sensors:laser:distance", laser_distance)
                    self.r.set("sensors:laser:distance", laser_distance)

                    # Sleep to limit the frequency of the measurements.
                    time.sleep(0.05)

            # Set back to proper state.
            self.set_laser_state(LaserState.Initialized)

        except Exception as e:
            self.log("Stopped unexpectedly: " + str(e), ll.ERROR)
            self.set_laser_state(LaserState.Unknown)


    def set_laser_state(self, val: int) -> None:
        """
        Sets value of the internal state. Used as guard to watch unproper behaviours on value updates.
        :param int val: Value of a LaserState.
        """
        if val < LaserState.Initialized:
            self.log("Warning, state:" + str(val), ll.CRITICAL)
        self._state = val
        self._publish_state()


    def _publish_state(self) -> None:
        """
        Publishes the internal state of the component on Redis.
        """
        self.send("state:laser:custom", {"state": self._state, "alive": (self.alive >= LaserState.Alive)})
        self.r.set("state:laser:custom", json.dumps({"state": self._state, "alive": (self.alive >= LaserState.Alive)}))


def run() -> bool:
    compo = LaserComponent()
    return compo.start()
