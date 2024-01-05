import json
import socket
import threading
import os
from typing import Union, Generic, TypeVar, List
from utilities import component as component, ipc
from utilities.ipc import route
import time
from dataclasses import dataclass


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


T = TypeVar('T')


@dataclass
class SensorEvent:
    """
    This class is used to measure the time between two sensor same events to avoid spamming the base station
    """

    name: str
    time_between_events: float
    last_time: float
    necessary_data: Union[None, List[str]] = None

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
        if self.necessary_data is not None and type(payload) == dict:
            return {key: payload[key] for key in self.necessary_data}
        return payload


class CommunicationComponent(component.Component):
    """
    This component is responsible for forwarding messages from redis IPC to the base station and vice-versa.
    """

    NAME = "communication"

    def __init__(self, host: str, port: int):
        super().__init__()

        self.host = host
        self.port = port
        self.alive = False
        self.stop_threads = False

        self.waiting_time_before_reconnection = 0.5
        self.client_socket: Union[socket.socket, None] = None
        self.emission_thread = None
        self.reception_thread = None
        self.heartbeat_emission_thread = None
        self.time_between_heartbeats = 1.5

        self.sensors = {
            "sensors:gps": SensorEvent("gps", 1, 0),
            "sensors:speed": SensorEvent("speed", 1, 0),
            "sensors:altitude": SensorEvent("altitude", 1, 0),
            "sensors:battery": SensorEvent("battery", 1, 0),
            "sensors:full": SensorEvent("full", 0.2, 0, ["roll", "pitch", "yaw"]),
        }

        self.log("Communication component initialized")

    def start(self):
        self.alive = True

        return self

    def connection_jobs(self):
        """
        Method used to manage the connection to the server.
        """
        self.log("Communication component started")
        if not self.alive:
            return

        retry = 1
        while self.alive:
            self.log(f"Trying to connect to {self.host}:{self.port} (attempt {retry})")

            # Close the socket if it is already open
            if self.client_socket:
                self.client_socket.close()

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)

            try:
                self.client_socket.connect((self.host, self.port))
                self.log("Drone connected to server")
                self.stop_threads = False

                self.create_threads()

            except Exception as e:
                self.log(f"Connection error: {e}")
                self.log(
                    f"Retrying in {self.waiting_time_before_reconnection} seconds (retry {retry})"
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
                        self.send(data["route"], data["data"])

            except Exception as e:
                self.log(f"Reception error: {e}")
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
                self.log(f"Heartbeat emission error: {e}")
                self.stop_threads = True

    @route(
        "sensors:full",
        "sensors:speed",
        "sensors:altitude",
        "sensors:battery",
        "sensors:gps",
        "log:INFO:*",
        "log:WARNING:*",
        "log:ERROR:*",
        "log:CRITICAL:*",
        "state:*",
        get_route=True,
    )
    def handle_emission(self, payload, _route):
        """
        Method used to handle the emission of messages to the server.
        """
        if not self.client_socket or self.stop_threads:
            return

        try:
            _route = clear_route(_route)
            data = payload
            if _route in self.sensors:
                if not self.sensors[_route].can_send():
                    return

                data = self.sensors[_route].sanitize_data(payload)

            message = {
                "type": _route,
                "data": data
            }

            data = str(json.dumps(message))
            self.client_socket.send(len(data).to_bytes(4, byteorder="big"))
            self.client_socket.send(data.encode())

        except Exception as e:
            self.log(f"Emission error: {e}")
            self.stop_threads = True

    def stop(self):
        self.alive = False
        self.stop_threads = True
        self.log("Communication component stopped")


def run():
    compo = CommunicationComponent(
        host=os.environ.get("COMMUNICATION_BASE_HOST"),
        port=int(os.environ.get("COMMUNICATION_BASE_PORT")),
    ).start()
    compo.connection_jobs()


# Only for testing purposes
if __name__ == "__main__":
    run()
