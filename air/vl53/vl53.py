import json
import threading
import time
import typing
from contextlib import ExitStack

import adafruit_vl53l0x
import board
from digitalio import DigitalInOut
from air.utilities import component, ipc


class Vl53Component(component.Component):
    """
    This component is responsible for sensing the distance between the drone and the ground using 2 vl53l0x sensor.
    """

    NAME = "vl53"

    # For using multiple sensors, XSHUTS pins must be used.
    # First sensor XSHUTS pin
    FIRST_SENSOR_XSHUTS_PIN_NUMBER = 20
    # Second sensor XSHUTS pin
    SECOND_SENSOR_XSHUTS_PIN_NUMBER = None

    # The measurement timing budget in microseconds, tests have not shown a huge improvement in accuracy with 200K
    # budget (approx 15 measurements per second) so we use 100K budget (approx 30 measurements per second) witch is
    # enough for our use case. (the default value is 30K but again tests have not shown a huge improvement in speed).
    MEASUREMENT_TIMING_BUDGET = 100000

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        #: Is the sensing worker is alive
        self._sensing_worker_alive = False
        #: The sensing worker thread
        self._sensing_worker_thread = threading.Thread(target=self._sensing_worker, daemon=True)
        #: Is the first sensor (0x29) data is emulated or not
        self._first_sensor_emulation = False
        #: Is the second sensor (0x30) data is emulated or not
        self._second_sensor_emulation = False

        #: First sensor
        self._first_vl53 = None
        #: Second sensor
        self._second_vl53 = None

        #: First sensor SHUT pin
        self._first_sensor_shut_pin = self._init_shut_pin(self.FIRST_SENSOR_XSHUTS_PIN_NUMBER)
        #: Second sensor SHUT pin
        self._second_sensor_shut_pin = self._init_shut_pin(self.SECOND_SENSOR_XSHUTS_PIN_NUMBER)

        #: I2C bus
        self._i2c = self._init_i2c()

        if self._i2c is None:
            self._first_sensor_emulation = True
            self._second_sensor_emulation = True
        else:
            self._first_vl53 = self._init_vl53(1)
            self._second_vl53 = self._init_vl53(2)

        self._update_custom_status()

    def _init_i2c(self):
        """
        Initialize the i2c bus
        """
        try:
            i2c = board.I2C()
            # Alternatively if there is some issues: busio.I2C(board.SCL, board.SDA)
            return i2c
        except Exception as e:
            self.logger.warning(
                f"Could not initialize I2C bus for VL53, defaulting to emulated data for both sensors: {e}", self.NAME
            )

    def _init_shut_pin(self, pin_number: typing.Union[int, None]):
        """
        Initialize the SHUT pin
        """
        if pin_number is not None:
            if not hasattr(board, f"D{pin_number}"):
                self.logger.error(
                    f"{pin_number} is an invalid pin number, the component will not be able to use multiple "
                    f"sensors, a single sensor will work but correct this error by giving a valid pin number to vl53 "
                    f"component class.",
                    self.NAME,
                )
                return None

            try:
                pin = DigitalInOut(getattr(board, f"D{pin_number}"))
                pin.switch_to_output(value=False)
                return pin
            except Exception as e:
                self.logger.warning(
                    f"Could not initialize {pin_number} SHUT pin for VL53, the component will not be able to "
                    f"use multiple sensors, a single sensor will work but this error should be corrected: {e}",
                    self.NAME,
                )
                return None

    def _init_vl53(self, number: int):
        """
        Initialize the VL53 sensor
        """
        pin, label, address = (
            (self._first_sensor_shut_pin, "first", 0x30)
            if number == 1
            else (self._second_sensor_shut_pin, "second", 0x29)
        )

        try:
            if pin is not None:
                # Enable the sensor, i2c address will be defaulted 0x29
                pin.value = True
                time.sleep(0.01)

            vl53 = adafruit_vl53l0x.VL53L0X(self._i2c)

            if number == 1:
                # Change address to 0x30
                vl53.set_address(address)

            vl53.measurement_timing_budget = self.MEASUREMENT_TIMING_BUDGET

            self.logger.info(f"VL53 {label} sensor initialized on address {hex(address)}", self.NAME)

            return vl53
        except Exception as e:
            self.logger.warning(
                f"Could not initialize {label} sensor, defaulting to emulated data for this sensor: {e}", self.NAME
            )

            if number == 1:
                self._first_sensor_emulation = True
            else:
                self._second_sensor_emulation = True
            return None

    def _update_custom_status(self):
        """
        Update the custom status to sensors:vl53:status
        """
        self.redis.set(
            "sensors:vl53:status",
            json.dumps(
                {
                    "sensing_worker_alive": self._sensing_worker_alive,
                    "first_sensor_emulation": self._first_sensor_emulation,
                    "second_sensor_emulation": self._second_sensor_emulation,
                }
            ),
        )
        self.ipc_node.send(
            "sensors:vl53:status",
            {
                "sensing_worker_alive": self._sensing_worker_alive,
                "first_sensor_emulation": self._first_sensor_emulation,
                "second_sensor_emulation": self._second_sensor_emulation,
            },
        )

    @staticmethod
    def _get_emulated_range(offset: int = 50) -> int:
        """
        Get emulated range
        :param offset: The offset to add to the range
        """
        return 100 + int((time.time() + 50) % 500)

    @staticmethod
    def _parse_range(_range: int) -> int:
        """
        Parse the range
        :param _range: The range to parse
        """
        return _range if _range <= 1100 else 0

    def _sensing_worker(self):
        # Clear eventual previous data
        self.redis.set("sensors:vl53:ranges", "")

        # Update the new alive state
        self._update_custom_status()

        with ExitStack() as stack:
            try:
                if self._first_vl53 is not None:
                    stack.enter_context(self._first_vl53.continuous_mode())
                if self._second_vl53 is not None:
                    stack.enter_context(self._second_vl53.continuous_mode())

                while self._sensing_worker_alive:
                    if not self._first_sensor_emulation and not self._second_sensor_emulation:
                        # No emulation, use both sensors
                        data = {
                            "first_range": self._parse_range(self._first_vl53.range),
                            "second_range": self._parse_range(self._second_vl53.range),
                        }

                    elif self._first_sensor_emulation and self._second_sensor_emulation:
                        # Both sensors are emulated, different ranges for each sensor
                        data = {"first_range": self._get_emulated_range(0), "second_range": self._get_emulated_range()}

                    else:
                        # Only the first sensor is emulated, it will take the same range as the second sensor
                        r = self._second_vl53.range if self._first_sensor_emulation else self._first_vl53.range
                        r = self._parse_range(r)
                        data = {"first_range": r, "second_range": r}

                    self.redis.set("sensors:vl53:ranges", json.dumps(data))
                    self.ipc_node.send("sensors:vl53:ranges", data)

            except Exception as e:
                self.logger.error(f"vl53 sensing worker stopped unexpectedly: {e}", self.NAME)
                self._sensing_worker_alive = False

            self._update_custom_status()

    def start(self):
        self._sensing_worker_alive = True
        self._sensing_worker_thread.start()

    def stop(self):
        self._sensing_worker_alive = False
        self._sensing_worker_thread.join()
