import json
import os
import pickle
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar, Union

from air.utilities import component, ipc


def clear_route(_route: str) -> str:
    """
    This method is used to clear route of IPC message for base station
    For instance : log:* -> log
    """
    splitted_route = _route.split(":")
    if len(splitted_route) > 1:
        if splitted_route[0] == "log":
            return splitted_route[0]
    return _route


def sanitize_log_data(data: dict) -> dict:
    """
    This method is used to sanitize data of IPC log message for base station
    """
    return pickle.loads(data)


T = TypeVar("T")


@dataclass
class SensorEvent:
    """
    This class is used to measure the time between two sensor same events to avoid spamming the base station
    """

    name: str
    time_between_events: float
    last_time: float
    necessary_data: Union[None, List[str]] = None
    sanitize_method: Callable = None

    def can_send(self) -> bool:
        """
        This method is used to check if the sensor event can be sent to the base station
        """
        if time.time() - self.last_time > self.time_between_events:
            self.last_time = time.time()
            return True
        return False

    def sanitize_data(self, payload: Generic[T]) -> Generic[T]:
        """
        This method is used to sanitize data of IPC message for base station. To send only the necessary data
        """
        data = payload
        if self.necessary_data is not None and isinstance(payload, dict):
            data = {key: payload[key] for key in self.necessary_data}

        if self.sanitize_method is not None:
            data = self.sanitize_method(data)

        return data


class CommunicationComponent(component.Component):
    """
    This component is responsible for forwarding messages from redis IPC to the base station and vice-versa.
    """

    NAME = "communication"

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        self.host = os.environ.get("COMMUNICATION_BASE_HOST")
        self.port = int(os.environ.get("COMMUNICATION_BASE_PORT"))
        self.alive = False
        self.stop_threads = False

        self.waiting_time_before_reconnection = 0.5
        self.client_socket: Union[socket.socket, None] = None
        self.emission_thread = None
        self.reception_thread = None
        self.heartbeat_emission_thread = None
        self.time_between_heartbeats = 1.5

        self.sensors = {
            # "sensors:sim7600:gnss": SensorEvent("gps", 1, 0),
            "sensors:speed": SensorEvent("speed", 1, 0),
            "sensors:altitude": SensorEvent("altitude", 1, 0),
            "sensors:battery": SensorEvent("battery", 1, 0),
            "sensors:sense_hat:data": SensorEvent(
                "sense_hat",
                0.5,
                0,
                ["roll", "pitch", "yaw"],
                lambda x: {
                    "roll": round(x["roll"], 2),
                    "pitch": round(x["pitch"], 2),
                    "yaw": round(x["yaw"], 2),
                },
            ),
        }

    def start(self):
        self.alive = True
        threading.Thread(target=self.connection_jobs, daemon=True).start()

    def connection_jobs(self):
        """
        Method used to manage the connection to the server.
        """
        if not self.alive:
            return

        retry = 1
        while self.alive:
            self.logger.info(f"Trying to connect to {self.host}:{self.port} (attempt {retry})", self.NAME)

            # Close the socket if it is already open
            if self.client_socket:
                self.client_socket.close()

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)

            try:
                self.client_socket.connect((self.host, self.port))
                self.logger.info("Drone connected to server", self.NAME)
                self.stop_threads = False

                self.create_threads()

            except Exception as e:
                self.logger.info(f"Connection error: {e}", self.NAME)
                self.logger.info(
                    f"Retrying in {self.waiting_time_before_reconnection} seconds (retry {retry})",
                    self.NAME,
                )
                retry += 1

                time.sleep(self.waiting_time_before_reconnection)

    def create_threads(self):
        """
        Method used to create the threads for the reception and emission of messages.
        """
        self.heartbeat_emission_thread = threading.Thread(
            target=self.handle_heartbeat_emission,
            daemon=True,
        )
        self.heartbeat_emission_thread.start()

        self.reception_thread = threading.Thread(
            target=self.handle_reception,
            daemon=True,
        )
        self.reception_thread.start()

        # Wait for the threads to be finished
        self.heartbeat_emission_thread.join()
        self.reception_thread.join()

    def handle_reception(self):
        """
        Method used to handle the reception of messages from the server.
        """
        while not self.stop_threads:
            try:
                message_length_bytes = self.client_socket.recv(4)
                message_length = int.from_bytes(message_length_bytes, byteorder="big")
                message = self.client_socket.recv(message_length).decode()

                if message:
                    if message == "heartbeat":
                        # TODO: handle heartbeat
                        continue

                    # TODO: refacto this piece of shit
                    data = json.loads(json.loads(message))
                    if "route" in data and "data" in data:
                        self.ipc_node.send(data["route"], data["data"])

            except Exception as e:
                self.logger.error(f"Reception error: {e}", self.NAME)
                self.stop_threads = True
                break

    def handle_heartbeat_emission(self):
        """
        Method used to handle the emission of heartbeat messages to the server.
        Every {time_between_heartbeats} seconds, a heartbeat message is sent to the server.
        """
        while not self.stop_threads:
            try:
                self.client_socket.send(len("heartbeat").to_bytes(4, byteorder="big"))
                self.client_socket.send("heartbeat".encode())

                time.sleep(self.time_between_heartbeats)
            except Exception as e:
                self.logger.error(f"Heartbeat emission error: {e}", self.NAME)
                self.stop_threads = True

    @ipc.Route(
        [
            "sensors:sense_hat:data",
            # "sensors:sim7600:gnss",
            "log:CRITICAL:*",
            "log:WARNING:*",
            "log:ERROR:*",
            "log:INFO:*",
            "state:*",
            "config:get",
            "config:objectives:get",
        ],
        True,
    ).decorator
    def handle_emission(self, call_data: ipc.CallData, payload: dict):
        """
        Method used to handle the emission of messages to the server.
        """
        if not self.client_socket or self.stop_threads:
            return

        try:
            _channel = call_data.channel
            data = payload
            if _channel in self.sensors:
                if not self.sensors[_channel].can_send():
                    return

                data = self.sensors[_channel].sanitize_data(payload)

            if _channel.startswith("log"):
                _channel = clear_route(_channel)
                data = sanitize_log_data(data)

            message = {"type": _channel, "data": data}

            data = str(json.dumps(message))
            self.client_socket.send(len(data).to_bytes(4, byteorder="big"))
            self.client_socket.send(data.encode())

        except Exception as e:
            self.logger.error(f"Emission error: {e}", self.NAME)
            self.stop_threads = True

    def stop(self):
        self.alive = False
        self.stop_threads = True
