"""
Overview & Usage
----------------
This module implements a simple IPC system based on Redis.

The :meth:`IpcNode <IpcNode>` class allow you to communicate with other nodes with
an endpoint based system. An endpoint is a function decorated with
:meth:`endpoint <endpoint>`, this function will be called when a message is
received on the channel matching the regexes provided in the decorator.

.. code-block:: python

    class PingPongNode(IpcNode):

        # I register a ping endpoint, all messages sent to `ping` channel will be received by this function
        @endpoint("ping")
        def ping(self, payload: dict):
            print("Ping!")

            # I send a message to the `pong` channel, since I want this node to receive it, I set `loopback` to True.
            self.send("pong", {"extra_message": "Hello World!"}, loopback=True)

        # I register a pong endpoint, all messages sent to `pong` channel will be received by this function
        @endpoint("pong")
        def pong(self, payload: dict):
            print("Pong!")
            # I can access the data sent by the ping function
            print(payload["extra_message"])


    # I create a new node called `ipc-node-test`
    n = PingPongNode("ipc-node-test")
    # I start the node
    n.start()
    # I send a message to the `ping` channel and use `loopback` since I want to receive it with the same node
    n.send("ping", {}, loopback=True)

    '''
    Output:
    Ping!
    Pong!
    Hello World!
    '''

.. tip::
    For more advanced usage, see the documentation of :meth:`endpoint <endpoint>`
    decorator and :meth:`IpcNode <IpcNode>` class bellow.
"""
import dataclasses
import json
import os
import re
import threading
import time
import uuid

import redis


def endpoint(regex: str, *args, thread: bool = False):
    """
    Decorate a method with this decorator to register it as an endpoint.

    .. warning::
        The decorated method must have a single parameter called `payload` of type :meth:`dict` to receive the
        message extra data.

    :param regex: A regex to match the route. For example, if a message is sent to `a.b.c`, I can receive it by giving
        `a.*.c` as regex to this function, this will also work by giving `a.*`, `a.b.*`, `a.b.c` and more.
    :param args: Additional regexes, to listen to multiple routes.
    :param thread: If True, the decorated function will be called in a new thread. If this parameter is set to False,
        when the decorated function is called, the IPC node will not be able to receive new messages until the function
        returns.
    """

    def decorator(func):
        func.regexes = [regex, *args]
        func.thread = thread
        return func

    return decorator


class IpcNode:
    """
    An IPC node used to communicate with other nodes.

    .. note::
        This class is not meant to be used directly except if you just need to send messages,
        you should inherit from it and implement your own endpoints.
    """

    def __init__(self, ipc_id: str = None, host: str = 'redis-ipc',
                 port=6379, db=0, **kwargs):
        """
        Create a new IPC node used to communicate with other nodes.

        :param str ipc_id: IPC node id, if default value is used, a random uuid will be generated, defaults to None.
        :param str host: Redis server hostname, when using IPC from container to container, use the container name,
            defaults to 'redis-ipc'.
        :param int port: Redis server port, defaults to 6379.
        :param int db: Redis server db, defaults to 0.
        """
        super().__init__(**kwargs)  # Kwargs forwarding to allow multiple inheritance

        #: :meth:`str` IPC node id
        self.ipc_id = ipc_id if ipc_id is not None else "ipc-node-" + str(uuid.uuid4())

        #: :meth:`redis.StrictRedis` Redis client
        self.r = redis.StrictRedis(host=host, port=port, db=db)
        #: :meth:`redis.client.PubSub` Redis pubsub client
        self.pubsub = self.r.pubsub()

        #: :meth:`bool` Flag for the listen thread, while True, the listen thread will continue
        #: to listen for new messages.
        self.subscribed = False
        #: :meth:`bool` Listening flag, while True, the listen thread is listening for new messages.
        self.listening = False

        #: :meth:`dict` A dict mapping all regexes to their callbacks.
        self.regexes = {}
        for func in dir(self):
            if hasattr(getattr(self, func), "regexes"):
                for regex in getattr(getattr(self, func), "regexes"):
                    self.regexes[regex] = (getattr(self, func), getattr(getattr(self, func), "thread"))

    def _listen(self):
        """
        Listener thread, this thread will listen for new messages and call the appropriate callbacks.
        """
        self.listening = True
        while self.subscribed:
            message = self.pubsub.get_message()

            # No message
            if message is None or message["type"] != "message":
                time.sleep(0.001)
                continue

            if message["channel"].decode() != "ipc":
                continue

            # print("MESSAGE RECEIVED", message, flush=True)

            try:
                payload = json.loads(message["data"].decode())
                if "sender" not in payload or "loopback" not in payload or "data" not in payload or "route" not in payload:
                    raise Exception("Malformed request")
            except Exception as e:
                print(f"IpcNode[{self.ipc_id}] ERROR, malformed request: {message}", flush=True)
                continue

            if not payload["loopback"] and payload["sender"] == self.ipc_id:
                continue

            for regex in self.regexes:
                if re.match(regex, payload["route"]) is not None:
                    try:
                        self.regexes[regex][0](payload["data"]) if not self.regexes[regex][1] else threading.Thread(
                            target=self.regexes[regex][0], args=(payload["data"],)).start()
                    except Exception as e:
                        print(f"IpcNode[{self.ipc_id}] ERROR, callback raised exception {regex} {payload['data']}: {e}", flush=True)

        self.listening = False

    def start(self):
        """
        Start the ipc node.

        .. warning::
            Ensure this method is called when the node is stopped.
        """
        self.pubsub.subscribe("ipc")
        self.subscribed = True
        threading.Thread(target=self._listen).start()
        while not self.listening:
            time.sleep(0.001)

    def stop(self):
        """
        Stop the ipc node.

        .. warning::
            Ensure this method is called when the node is started.
        """
        self.subscribed = False
        self.pubsub.unsubscribe("ipc")
        self.pubsub.close()
        self.r.close()

    def send(self, route: str, data: dict, loopback: bool = False):
        """
        Send a message to a route.

        :param str route: The route that will be matched with regexes given in :meth:`endpoint <endpoint>` decorator.
        :param dict data: Extra data to send as a dict, this data will be passed to the callback function.
        :param bool loopback: If True, this node will be able to receive the message. defaults to False.
        """
        req = {"route": route, "sender": self.ipc_id, "loopback": loopback, "data": data}
        self.r.publish("ipc", json.dumps(req).encode())

if __name__ == '__main__':
    class PingPongNode(IpcNode):

        # I register a ping endpoint, all messages sent to `ping` channel will be received by this function
        @endpoint("ping")
        def ping(self, payload: dict):
            print("Ping!")

            # I send a message to the `pong` channel, since I want this node to receive it, I set `loopback` to True.
            self.send("pong", {"extra_message": "Hello World!"}, loopback=True)

        # I register a pong endpoint, all messages sent to `pong` channel will be received by this function
        @endpoint("pong")
        def pong(self, payload: dict):
            print("Pong!")
            # I can access the data sent by the ping function
            print(payload["extra_message"])


    # I create a new node called `ipc-node-test`
    n = PingPongNode("ipc-node-test")
    # I start the node
    n.start()
    # I send a message to the `ping` channel and use `loopback` since I want to receive it with the same node
    n.send("ping", {}, loopback=True)