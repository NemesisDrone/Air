from socket import AF_INET, socket, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY
from threading import Thread
from dataclasses import dataclass
from typing import List, Union
from enum import Enum

import numpy as np
import math

"""
Install Modified picaSim before running this code

PICASIM Port: 7777
-> Options 2 -> Advanced.
    -> Enable socket controller

Pause
Unpause
Reset
Exit

Agent 0 [or 1, 2 if multiple planes]
TakeControl -> before sending commands to control the plane
ReleaseControl
Control 1 0.3 [Sets channel 1 to 0.3]
Control 0 -1 [Sets channel 0 to -1]
RequestTelemetry 0.1 [Requests data every 0.1 seconds. Send 0 to stop it.]
"""


class Channels(Enum):
    AILERON = 0
    ELEVATOR = 1
    THROTTLE = 3
    RUDDER = 2


@dataclass
class TelemetryData:
    """
    Data class for PicaSim telemetry data
    """

    time: float

    position_x: float = 0
    position_y: float = 0
    position_z: float = 0

    roll: float = 0
    pitch: float = 0
    yaw: float = 0

    altitude: float = 0


class PicaSimConnectorClass:
    """
    Connects to the PicaSim server, sends and receives data.
    """
    instance = None

    def __init__(self):
        self.BUFSIZ = 1024
        self.HOST = "127.0.0.1"
        self.PORT = 7777
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.sock.connect((self.HOST, self.PORT))

        receive_thread = Thread(target=self._data_receiver, daemon=True)
        receive_thread.start()

        # Request telemetry data
        self.sock.send(bytes("requesttelemetry 0.1\n", "utf8"))

        self._last_telemetry: Union[TelemetryData, None] = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def get_last_telemetry(self) -> TelemetryData:
        """
        Returns the last telemetry data received from the PicaSim server
        :return:
        """
        return self._last_telemetry

    def _data_receiver(self) -> None:
        """
        Receives data from the PicaSim server
        :return:
        """
        while True:
            try:
                _data = self.sock.recv(self.BUFSIZ).decode("utf8")
                if not _data:
                    print("No data received, connection closed\n")
                    break

                if _data.split(" ")[2] == "Telemetry":
                    self._last_telemetry = self._parse_telemetry(_data)

            except Exception as e:
                print("receive error\n", e)
                break

    @staticmethod
    def calculate_roll(
            face_dir_x: float,
            face_dir_y: float,
            face_dir_z: float,
            up_dir_x: float,
            up_dir_y: float,
            up_dir_z: float,
    ) -> float:
        """
        Calculates the roll angle from the face and up direction vectors
        :param face_dir_x:
        :param face_dir_y:
        :param face_dir_z:
        :param up_dir_x:
        :param up_dir_y:
        :param up_dir_z:
        :return:
        """
        face_dir = np.array([face_dir_x, face_dir_y, face_dir_z])
        up_dir = np.array([up_dir_x, up_dir_y, up_dir_z])
        left_dir = np.cross(up_dir, face_dir)
        # world_up_dir = np.array([0, 0, 1])
        # hor_left_dir = np.cross(world_up_dir, face_dir)
        # hor_left_dir /= np.linalg.norm(hor_left_dir)

        roll = math.degrees(math.atan2(left_dir[2], up_dir_z))
        return roll

    def _parse_telemetry(self, _data: str) -> TelemetryData:
        """
        Parses telemetry data from the PicaSim server
        :param _data: Telemetry data
        :return:
        """
        _data = _data.split(" ")

        face_dir_x = round(float(_data[10]), 2)
        face_dir_y = round(float(_data[11]), 2)
        face_dir_z = round(float(_data[12]), 2)

        up_dir_x = round(float(_data[14]), 2)
        up_dir_y = round(float(_data[15]), 2)
        up_dir_z = round(float(_data[16]), 2)

        pitch = round(math.degrees(math.asin(face_dir_z)), 2)
        yaw = round(math.degrees(math.atan2(face_dir_y, face_dir_x)), 2)
        roll = round(
            self.calculate_roll(
                face_dir_x, face_dir_y, face_dir_z, up_dir_x, up_dir_y, up_dir_z
            ),
            2,
        )

        telemetry = TelemetryData(
            time=float(_data[4]),
            position_x=float(_data[6]),
            position_y=float(_data[7]),
            position_z=float(_data[8]),
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            altitude=round(float(_data[18]), 2),
        )

        return telemetry

    def send_data(self, _data: str):
        """
        Sends data to the PicaSim server
        :param _data: Data to send to PicaSim
        :return:
        """
        _data += "\n"
        self.sock.send(bytes(_data, "utf8"))

    def close(self):
        """
        Closes the connection to the PicaSim server
        :return:
        """
        self.sock.close()


class Plane(PicaSimConnectorClass):
    def __init__(self, agent=0):
        """
        :param agent: The numeros of the plane. Don't change it if you don't know what you are doing
        """
        super().__init__()
        self._agent = agent

    def take_control(self) -> None:
        """
        Takes control of the plane
        :return:
        """
        self.send_data(f"takecontrol")

    def release_control(self) -> None:
        """
        Releases control of the plane
        :return:
        """
        self.send_data(f"releasecontrol")

    def control(self, channel: Union[int, Channels], value: float) -> None:
        if isinstance(channel, Channels):
            channel = channel.value
        self.send_data(f"control {channel} {value}")

    def get_telemetry(self) -> Union[TelemetryData, None]:
        return self.get_last_telemetry()
