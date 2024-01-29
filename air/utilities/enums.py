from enum import Enum


class FlightMode(int, Enum):
    """
    Flight mode enum.
    When flight mode is manual, the drone is controlled by the user using the rc controller.
    """

    MANUAL = 0
    AUTONOMOUS = 1
