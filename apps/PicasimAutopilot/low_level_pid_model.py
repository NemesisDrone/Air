import time

from picasim import Plane, Channels

from simple_pid import PID


class Pid:

    def __init__(self, kp: float, ki: float, kd: float, revert: bool = False, lowest: float = -1, highest: float = 1):
        self.pid = PID(kp, ki, kd, setpoint=0)
        self.pid.output_limits = (lowest*10, highest*10)
        self.revert = revert

    def set_target(self, target: float):
        self.pid.setpoint = target

    def get_control(self, value: float) -> float:
        control = self.pid(value)
        if self.revert:
            control = -control
        return control/10


class LowLevelPid:
    """
    A simple autopilot model
    """

    HEIGHT_TARGET = 20

    def __init__(self, plane: Plane):
        self.plane = plane

    def get_telemetry(self):
        data = False
        while not data:
            data = self.plane.get_telemetry()

    def take_off(self):
        pitch_pid = Pid(0.1, 0.01, 0.05, revert=True, lowest=-0.5, highest=0.5)
        roll_pid = Pid(0.1, 0.01, 0.05, lowest=-0.5, highest=0.5)

        self.plane.control(Channels.THROTTLE, 1)

        pitch_pid.set_target(15)

        while True:
            data = self.plane.get_telemetry()
            print(data)

            if data.altitude > self.HEIGHT_TARGET:
                pitch_pid.set_target(0)

            self.plane.control(Channels.ELEVATOR, pitch_pid.get_control(data.pitch))
            self.plane.control(Channels.AILERON, roll_pid.get_control(data.roll))
            time.sleep(0.01)

    def run(self):
        self.plane.take_control()
        input("Press Enter to take off")
        self.take_off()
