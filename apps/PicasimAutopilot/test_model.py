import threading
import time
from enum import Enum

from utils.utils import normalize
from picasim import Plane, Channels
from utils.pid import Pid


class PlaneStates(Enum):
    CRUISING = "cruising"
    CLIMBING_OR_DESCENDING = "climbing_or_descending"
    TURNING = "turning"


class TestAutoPilot:
    """
    A simple autopilot for pitch/altitude/roll and yow to control roll
    """

    def __init__(self, plane: Plane):
        self.plane = plane
        self.CRUISING_ALTITUDE = 30
        self.YAW_DIRECTION = 45

        self.plane_state = PlaneStates.CRUISING

    def run(self):
        control_thread = threading.Thread(target=self.update, daemon=True)
        control_thread.start()

        while True:
            print("""
- Pause: p
- Unpause: u
- Reset: r
- Quit: q
- Altitude: a <value>
- Take control: t
- Release control: l
- Direction: y <value>""")
            action = input("Enter action: ")

            if action == "p":
                self.plane.send_data("pause")
            elif action == "u":
                self.plane.send_data("unpause")
            elif action == "r":
                self.plane.send_data("reset")
            elif action == "q":
                break
            elif action == "t":
                self.plane.take_control()
            elif action == "l":
                self.plane.release_control()
            elif action.startswith("a"):
                value = action.split(" ")[1]
                self.CRUISING_ALTITUDE = int(value)
            elif action.startswith("y"):
                value = action.split(" ")[1]
                self.YAW_DIRECTION = int(value)
            else:
                print("Invalid action")

    @staticmethod
    def _need_to_climb_or_descend(altitude, target, margin_percent=10):
        return abs(altitude - target) > (target * margin_percent / 100)

    def update(self):
        self.plane.take_control()

        pitch_pid = Pid(0.1, 0.01, 0.0, revert=True)
        altitude_pid = Pid(1, 0.05, 0, lowest=-25, highest=25)

        roll_pid = Pid(0.05, 0.01, 0.0)
        yaw_pid = Pid(0.6, 0.05, 0, lowest=-25, highest=25, revert=True)

        roll_pid.set_target(0)
        pitch_pid.set_target(2)

        self.plane.control(Channels.THROTTLE, 1)

        limited_roll = 20

        while True:
            data = self.plane.get_telemetry()
            if not data:
                continue

            NEED_TO_CLIMB_OR_DESCEND = self._need_to_climb_or_descend(data.altitude, self.CRUISING_ALTITUDE)

            if NEED_TO_CLIMB_OR_DESCEND:
                self.plane_state = PlaneStates.CLIMBING_OR_DESCENDING
            else:
                self.plane_state = PlaneStates.CRUISING

            altitude_pid.set_target(self.CRUISING_ALTITUDE)

            # Pitch handling for altitude
            altitude_control = altitude_pid.get_control(data.altitude)

            pitch_pid.set_target(altitude_control)
            pitch_control = normalize(pitch_pid.get_control(data.pitch), _min=-20, _max=20)
            self.plane.control(Channels.ELEVATOR, pitch_control)

            # Roll handling.

            yaw_pid.set_target(self.YAW_DIRECTION)
            yaw_control = yaw_pid.get_control(data.yaw)

            roll_pid.set_target(yaw_control)
            roll_control = normalize(roll_pid.get_control(data.roll), _min=-limited_roll, _max=limited_roll)

            self.plane.control(Channels.AILERON, roll_control)

            print("Yaw objective:", self.YAW_DIRECTION, "Yaw:", data.yaw, "Altitude objective:", self.CRUISING_ALTITUDE, "Altitude:", data.altitude)

            time.sleep(0.01)
