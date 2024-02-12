import datetime
import json
import random
import threading
import time
import typing

import serial

from air.utilities import component, ipc


GNSS_POLL_SLEEP_TIME = 0.05


class Sim7600:
    GPS_TOGGLE_TIMEOUT = 2

    @staticmethod
    def _serial_setup():
        """
        Setup serial interface for sim7600H
        """
        try:
            ser = serial.Serial("/dev/ttyS0", 115200, timeout=2)
        except Exception:
            # For RPI 2
            try:
                ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=2)
            except Exception as e:
                raise RuntimeError(f"Could not open serial interface ttyS0 or ttyAMA0: {e}")

        ser.flushInput()
        ser.flushOutput()
        return ser

    def __init__(self):
        """
        Initialize sim7600H
        """
        self._ser = self._serial_setup()

    def _send_command(self, command):
        self._ser.write((command + "\r\n").encode())

    def _flush_output(self, timeout: float = 1.0):
        now = time.time()
        buff = ""
        while "OK" not in buff and "ERROR" not in buff:
            if time.time() - now > timeout:
                raise RuntimeError(f"Unable to flush output, timeout, sim7600H may not be recognized: {buff}")
            buff += self._ser.readline().decode()
        return buff

    def toggle_gps(self, enable: bool = True):
        self._send_command("AT+CGPS=0")
        self._flush_output()
        self._send_command("AT+CGPSHOR=1")
        self._flush_output()
        self._send_command("AT+CGPSNMEARATE=1")
        self._flush_output()
        if enable:
            self._send_command("AT+CGPS=1,2")
            r = self._flush_output()
            while "OK" not in r:
                time.sleep(0.25)
                self._send_command("AT+CGPS=1,2")
                r = self._flush_output()

    def get_gnss_info(self) -> typing.Union[typing.Dict[str, typing.Union[int, float, str, tuple[int, float]]], None]:
        self._send_command("AT+CGNSSINFO")
        r = self._flush_output()

        try:
            if "ERROR" in r:
                raise RuntimeError(f"Unable to get GNSS info: {r}")

            r = r.split("+CGNSSINFO: ")[1].split("\r\n")[0]
            r = r.split(",")

            # Check raw data
            for i in range(len(r)):
                if i != 12 and r[i] == "":
                    return None

            labels = [
                "fixMode",
                "gpsSat",
                "gloSat",
                "beiSat",
                "lat",
                "latInd",
                "lon",
                "lonInd",
                "date",
                "time",
                "alt",
                "speed",
                "course",
                "pdop",
                "hdop",
                "vdop",
            ]
            str_labels = ["latInd", "lonInd", "date", "time", "course", "lat", "lon"]

            data: typing.Dict[str, typing.Union[int, float, str, tuple[int, float]]] = {
                labels[i]: float(r[i]) if labels[i] not in str_labels else r[i] for i in range(len(r))
            }

            data["lat"] = (int(data["lat"][:2]), float(data["lat"][2:]))
            data["lon"] = (int(data["lon"][:3]), float(data["lon"][3:]))
            data["timestamp"] = time.time()

            # Data validation
            if data["fixMode"] != 2:
                raise RuntimeError(f"Invalid GNSS data: {r}\n\tData: {data}")

        except Exception as e:
            raise RuntimeError(f"Unable to get GNSS info: {e}\n\tData: {r}")

        return data


class Sim7600Component(component.Component):
    NAME = "sim7600"

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        #: Is the gnss worker alive
        self._gnss_worker_alive = False
        #: The gnss worker thread
        self._gnss_worker_thread = threading.Thread(target=self._gnss_worker, daemon=True)
        #: Is the gnss worker data valid or is it emulated data
        self._gnss_emulation = False

        try:
            self._sim = Sim7600()
            self._sim.toggle_gps()
        except Exception as e:
            self.logger.warning(f"Could not initialize SIM7600, defaulting to emulated data: {e}", self.NAME)
            self._gnss_emulation = True

        self._update_custom_status()

    def _update_custom_status(self):
        """
        Update the custom status to sensors:sim7600:status
        """
        self.redis.set(
            "sensors:sim7600:status",
            json.dumps({"gnss_worker_alive": self._gnss_worker_alive, "gnss_emulation": self._gnss_emulation}),
        )
        self.ipc_node.send(
            "sensors:sim7600:status",
            {"gnss_worker_alive": self._gnss_worker_alive, "gnss_emulation": self._gnss_emulation},
        )

    def _update_gnss_data(self):
        """
        Update the GNSS data to sensors:sim7600:gnss

        :raises RuntimeError: If the GNSS data is unavailable
        """
        assert not self._gnss_emulation
        data = self._sim.get_gnss_info()
        if isinstance(data, dict):
            self.ipc_node.send("sensors:sim7600:gnss", data)
            self.redis.set("sensors:sim7600:gnss", json.dumps(data))

    def _update_emulated_gnss_data(self):
        data = {
            "fixMode": 2,
            "gpsSat": 5,
            "gloSat": 6,
            "beiSat": 2,
            "lat": (48, 03.843334 + random.uniform(-0.01, 0.01)),
            "latInd": "N",
            "lon": (0, 45.382674 + random.uniform(-0.01, 0.01)),
            "lonInd": "W",
            "date": datetime.datetime.now().strftime("%d%m%Y"),
            "time": datetime.datetime.now().strftime("%H%M%S"),
            "alt": 60.3 + random.uniform(-0.1, 0.1),
            "speed": 0.0,
            "course": "",
            "pdop": 1.0,
            "hdop": 0.7,
            "vdop": 0.7,
        }

        self.redis.set("sensors:sim7600:gnss", json.dumps(data))
        self.ipc_node.send("sensors:sim7600:gnss", data)

    def _gnss_worker(self):
        # Clear eventual previous data
        self.redis.set("sensors:sim7600:gnss", "")

        # Update the new alive state
        self._update_custom_status()

        try:
            while self._gnss_worker_alive:
                if not self._gnss_emulation:
                    self._update_gnss_data()
                    time.sleep(GNSS_POLL_SLEEP_TIME)

                else:
                    self._update_emulated_gnss_data()
                    time.sleep(GNSS_POLL_SLEEP_TIME)

        except Exception as e:
            self.logger.error(f"GNSS worker stopped unexpectedly: {e}", self.NAME)
            self._gnss_worker_alive = False

        self._update_custom_status()

    def start(self):
        self._gnss_worker_alive = True
        self._gnss_worker_thread.start()

    def stop(self):
        self._gnss_worker_alive = False
        self._gnss_worker_thread.join()
