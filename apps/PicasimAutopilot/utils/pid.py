from simple_pid import PID

class Pid:
    """
    PID controller using simple_pid
    """
    def __init__(self, kp: float, ki: float, kd: float, revert: bool = False, lowest: float = -1, highest: float = 1) -> None:
        self.pid = PID(kp, ki, kd, setpoint=0)
        self.pid.output_limits = (lowest, highest)
        self.revert = revert

    def set_target(self, target: float) -> None:
        """
        Set the target value for the PID controller to reach
        :param target: The target value
        :return:
        """
        self.pid.setpoint = target

    def get_control(self, value: float) -> float:
        """
        Get the control value for the PID controller
        :param value:
        :return:
        """
        control = self.pid(value)
        if self.revert:
            control = -control
        return control
