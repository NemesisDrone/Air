# Autopilot model
import time

from picasim import Plane, Channels


class AutopilotModel1:
    """
    A simple autopilot model
    """
    def __init__(self, plane: Plane):
        self.plane = plane

        self.altitude_objective = 20
        self.roll_objective = 0.1

        self.is_climbing = False
        self.is_turning = False

    def run(self):
        print("Take control")
        self.plane.take_control()
        print("Start autopilot")

        # Set speed to maximum
        self.plane.control(Channels.THROTTLE, 1)

        while True:
            data = self.plane.get_telemetry()
            if not data:
                continue

            if data.altitude < self.altitude_objective-1:
                if data.pitch < 20:
                    self.plane.control(Channels.ELEVATOR, -0.2)
                else:
                    self.plane.control(Channels.ELEVATOR, 0)
            elif data.altitude > self.altitude_objective+1:
                self.plane.control(Channels.ELEVATOR, 0.2)
            else:
                self.plane.control(Channels.ELEVATOR, 0)

            if data.roll < self.roll_objective-5:
                self.plane.control(Channels.AILERON, 0.2)
            elif data.roll > self.roll_objective+5:
                self.plane.control(Channels.AILERON, -0.2)
            else:
                self.plane.control(Channels.AILERON, 0)

            time.sleep(0.01)

    def update(self):
        pass
