import time

from utils.utils import normalize
from picasim import Plane, Channels
from utils.pid import Pid


class SimpleAutoPilotWingLevel:
    """
    A simple autopilot model exemple for wing level
    """

    def __init__(self, plane: Plane):
        self.plane = plane
        self.CRUISING_ALTITUDE = 20

    def run(self):
        self.plane.take_control()

        roll_pid = Pid(0.05, 0.001, 0.0)
        pitch_pid = Pid(0.1, 0.01, 0.0, revert=True)
        altitude_pid = Pid(0.5, 0.05, 0, lowest=-25, highest=25)

        roll_pid.set_target(0)
        pitch_pid.set_target(2)
        altitude_pid.set_target(self.CRUISING_ALTITUDE)

        self.plane.control(Channels.THROTTLE, 1)

        while True:
            data = self.plane.get_telemetry()
            if not data:
                continue

            # Roll handling
            roll_control = roll_pid.get_control(data.roll)
            self.plane.control(Channels.AILERON, roll_control)

            # Pitch handling for altitude
            altitude_control = altitude_pid.get_control(data.altitude)

            pitch_pid.set_target(altitude_control)
            pitch_control = normalize(pitch_pid.get_control(data.pitch), _min=-20, _max=20)
            self.plane.control(Channels.ELEVATOR, pitch_control)

            print(data)

            time.sleep(0.01)

