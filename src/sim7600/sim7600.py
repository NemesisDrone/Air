import json
import random

import serial
from utilities import component as component, ipc
import time


class Sim7600:
    def __init__(self):
        self.ser = serial.Serial("/dev/ttyS0", 115200)
        self.ser.flushInput()
        self.ser.flushOutput()

    def _send_at(self, command):
        self.ser.write((command + "\r\n").encode())
        buff = ""
        while "OK" not in buff and "ERROR" not in buff:
            buff += self.ser.readline().decode()
        return buff

    def toggle_gps(self, enable: bool = True):
        self._send_at("AT+CGPS=0")
        self._send_at("AT+CGPSHOR=1")
        self._send_at("AT+CGPSNMEA=1")
        if enable:
            r = self._send_at("AT+CGPS=1,2")
            while "OK" not in r:
                time.sleep(0.25)
                r = self._send_at("AT+CGPS=1,2")

    def get_gnss_info(self):
        r = self._send_at("AT+CGNSSINFO")
        try:
            if "ERROR" in r:
                raise Exception("Could not get GPS info")
            r = r.split("+CGNSSINFO: ")[1].split("\r\n")[0]
            r = r.split(",")
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
            r = {labels[i]: r[i] for i in range(len(r))}

            r["lat"] = (int(r["lat"][:2]), float(r["lat"][2:]))
            r["lon"] = (int(r["lon"][:3]), float(r["lon"][3:]))

            # Data validation
            if r["fixMode"] != "2":
                raise Exception()

        except Exception as e:
            return False  # Not valid
        return r


class Sim7600Component(component.Component):
    NAME = "sim7600"

    def __init__(self):
        super().__init__()

        self.alive = False
        self.valid = True

        try:
            self.sim = Sim7600()
            self.sim.toggle_gps()
        except Exception as e:
            self.log(f"Could not initialize sim7600: {e}", level=ipc.LogLevels.WARNING)
            self.valid = False

        self.r.set(
            "state:sim7600:custom",
            json.dumps({"valid": self.valid, "alive": self.alive}),
        )
        self.send("state:sim7600:custom", {"valid": self.valid, "alive": self.alive})

        self.log("GPS component initialized")

    def start(self):
        self.alive = True

        self.log("GPS component started")
        return self

    def do_work(self):
        self.r.set(
            "state:sim7600:custom",
            json.dumps({"valid": self.valid, "alive": self.alive}),
        )
        self.send("state:sim7600:custom", {"valid": self.valid, "alive": self.alive})

        try:
            while self.alive:
                if self.valid:
                    data = self.sim.get_gnss_info()
                    if type(data) == dict:
                        self.send("sensors:sim7600:gnss", data)
                        self.r.set("sensors:sim7600:gnss", json.dumps(data))
                    time.sleep(0.05)

                else:
                    data = {
                        "fixMode": 2,
                        "gpsSat": 0,
                        "gloSat": 0,
                        "beiSat": 0,
                        "lat": (48, 03.843334 + random.uniform(-0.01, 0.01)),
                        "latInd": "N",
                        "lon": (0, 45.382674 + random.uniform(-0.01, 0.01)),
                        "lonInd": "W",
                        "date": "191123",
                        "time": "172039",
                        "alt": "60.3",
                        "speed": "0.0",
                        "course": "",
                        "pdop": "1.0",
                        "hdop": "0.7",
                        "vdop": "0.7",
                    }

                    self.send("sensors:sim7600:gnss", data)
                    self.r.set("sensors:sim7600:gnss", json.dumps(data))
                    time.sleep(0.1)

        except Exception as e:
            self.log(
                "GPS component stopped unexpectedly: " + str(e),
                level=ipc.LogLevels.ERROR,
            )
            self.alive = False
            self.valid = False

        self.r.set(
            "state:sim7600:custom",
            json.dumps({"valid": self.valid, "alive": self.alive}),
        )
        self.send("state:sim7600:custom", {"valid": self.valid, "alive": self.alive})

    def stop(self):
        self.alive = False
        self.log("GPS component stopped")


def run():
    compo = Sim7600Component().start()
    compo.do_work()
