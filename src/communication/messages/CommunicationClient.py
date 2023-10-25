"""
The communication client is used to connect to the base station and send/receive messages.
"""
import socket
import threading
import time
import redis
import os
import pickle
from typing import Union
import re
import json
import logging

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

r = redis.Redis(host=os.environ.get("REDIS_HOST"), port=os.environ.get("REDIS_PORT"), db=0)

"""
Channel regexes to listen to, and send them to the base station
"""

LISTENING_ROUTES = [
    # "log:DEBUG:.*",
    "log:INFO:.*",
    "log:WARNING:.*",
    "log:ERROR:.*",
    "log:CRITICAL:.*",
    "ping",
    "sensor:.*",
]


class CommunicationClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.stop_threads = False

        self.client_socket: Union[socket.socket, None] = None
        self.connect()

        self.thread_emission = None
        self.thread_reception = None

        self.create_threads()

        self.client_socket.close()

    def connect(self):
        """
        Method used to connect the drone to the server.
        If the connection fails, it will retry every 3 seconds.
        """
        retry = 1
        while True:
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.host, self.port))
                logging.info("Drone connected to server")
                break
            except Exception as e:
                logging.warning(f"Connection error: {e}")
                logging.warning(f"Retrying in 3 seconds (retry {retry})")
                retry += 1
                time.sleep(3)

    def reconnect(self):
        """
        Method used to reconnect the client to the server and restart the threads.
        """
        self.stop_threads = True
        self.client_socket.close()
        self.connect()
        time.sleep(1)
        self.stop_threads = False
        self.create_threads()

    def create_threads(self):
        """
        Method used to create the threads for the reception and emission of messages.
        """
        self.thread_reception = threading.Thread(
            target=self.handle_reception,
            daemon=True,
        )
        self.thread_reception.start()

        self.thread_emission = threading.Thread(
            target=self.handle_emission,
            daemon=True,
        )
        self.thread_emission.start()

        self.thread_reception.join()
        self.thread_emission.join()

    def handle_reception(self):
        """
        Method used to handle the reception of messages from the server.
        """
        while not self.stop_threads:
            try:
                received_data = self.client_socket.recv(2048).decode()

                if not received_data:
                    continue

                # Handle the case when multiple message are received at the same time
                # The messages are separated by a ~
                messages = received_data.split('~')
                print(messages)

            except Exception as e:
                logging.error(f"Reception error: {e}")
                self.reconnect()
                break

    def handle_emission(self):
        pubsub = r.pubsub()
        pubsub.subscribe("ipc")

        while not self.stop_threads:
            try:
                message = pubsub.get_message(ignore_subscribe_messages=True)

                if message:
                    message = pickle.loads(message["data"])

                    """
                    Test if the route is matching a REGEXES.
                    If it does, send the data to the base station.
                    """
                    for regex in LISTENING_ROUTES:
                        if re.match(regex, message["route"]):
                            """
                            For the "log:*:*" route, we only send the "log" part.
                            """
                            message_route = message["route"]
                            if message["route"].split(":")[0] == "log":
                                message_route = "log"

                            payload = {
                                "type": message_route,
                                "data": pickle.loads(message["data"])
                            }

                            """
                            To send the data, we first send the length of the data, then the data itself.
                            """
                            data = str(json.dumps(payload))
                            logging.debug(f"Payload sent {data}")
                            self.client_socket.send(len(data).to_bytes(4, byteorder='big'))
                            self.client_socket.send(data.encode())
                            break

            except Exception as e:
                logging.error(f"Sending error: {e}")
                self.reconnect()
                break


if __name__ == "__main__":
    client = CommunicationClient(os.environ.get("COMMUNICATION_BASE_HOST"), int(os.environ.get("COMMUNICATION_BASE_PORT")))
