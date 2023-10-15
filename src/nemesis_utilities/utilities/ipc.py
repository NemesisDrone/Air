"""
Overview & Usage
----------------
This module implements a simple IPC and logging system based on Redis.

The :meth:`IpcNode <IpcNode>` class allow you to communicate with other nodes with
a route based system and to log messages. A route is a function decorated with
:meth:`route <route>`, this function will be called when a message is
received on the channel matching the regexes provided in the decorator.

.. code-block:: python

    class PingPongNode(IpcNode):

        # I register a ping route, all messages sent to `ping` route will be received by this function
        @route("ping")
        def ping(self, payload: dict):
            self.log("Ping!")
        
            # I send a message to the `pong` route, since I want this node to receive it, I set `loopback` to True.
            self.send("pong", {"extra_message": "Hello World!"}, loopback=True)

        # I register a pong route, all messages sent to `pong` route will be received by this function
        @route("pong")
        def pong(self, payload: dict):
            self.log("Pong!")
            # I can access the data sent by the ping function
            self.log(payload["extra_message"])

        # I register a blocking route, all messages sent to `return_pi` route will be received by this function
        # Value will be sent back to the sender
        @route("return_pi", blocking=True, thread=True)
        def return_pi(self, payload: dict):
            return 3.14159265359


    # I create a new node called `ipc-node-test`
    n = PingPongNode("ipc-node-test")
    # I start the node
    n.start()
    # I send a message to the `ping` route and use `loopback` since I want to receive it with the same node
    n.send("ping", {}, loopback=True)
    # I send a message to the `return_pi`  blocking route, this will wait for the response
    n.log(n.send_blocking("return_pi", {}, loopback=True), level=LogLevels.DEBUG)
    # I don't forget to stop the node !
    n.stop()

    '''
    Output:
    [15-10-2023 13:06:51] INFO@PingPongNode: Ping!
    [15-10-2023 13:06:51] INFO@PingPongNode: Pong!
    [15-10-2023 13:06:51] INFO@PingPongNode: Hello World!
    '''

.. tip::
    For more advanced usage, see the documentation of :meth:`route <route>`
    decorator and :meth:`IpcNode <IpcNode>` class bellow.
"""
import dataclasses
import datetime
import os
import pickle
import re
import threading
import sys
import time
import traceback
import uuid

import redis

IPC_BLOCKING_RESPONSE_ROUTE = "IPC_BLOCKING_RESPONSE_ROUTE_IGNORE_IT"


def route(regex: str, *args, thread: bool = False, blocking: bool = False):
    """
    Decorate a method with this decorator to register it as a route.

    .. warning::
        The decorated method must have a single parameter called `payload` to receive the data sent by the sender.

    :param regex: A regex to match the route. For example, if a message is sent to `a.b.c`, I can receive it by giving
        `a.*.c` as regex to this function, this will also work by giving `a.*`, `a.b.*`, `a.b.c` and more.
    :param args: Additional regexes, to listen to multiple routes.
    :param thread: If True, the decorated function will be called in a new thread. If this parameter is set to False,
        when the decorated function is called, the IPC node will not be able to receive new messages until the function
        returns.
    :param blocking: If true, the decorated function return value will be sent back to the sender, the sender will
        wait for the response before continuing.

    .. warning::
        With blocking mode, your function has to return None or a json serializable object only, otherwise a
        warning will be printed and the function will return None.

        Be also sure that your blocking route is registered ONLY ONCE. If you register it multiple times, the sender
        will receive only the first response, but multiple callbacks will be called.
    .. note::
        If your function raises an exception, the exception will be automatically raised on the sender side.
    """

    def decorator(func):

        def wrapper(self, payload):
            if blocking:
                if IPC_BLOCKING_RESPONSE_ROUTE not in payload:
                    print(f"IpcNode[{self.ipc_id}][{self.__class__.__name__}] ERROR, blocking route {regex} "
                          f"received a request that was not sent with blocking mode, ignoring request", flush=True)
                    return
                else:
                    blocking_route = payload.pop(IPC_BLOCKING_RESPONSE_ROUTE)

                try:
                    r = func(self, payload)
                except Exception as e:
                    r = e
                try:
                    self.send(blocking_route, r, loopback=True)
                except Exception as e:
                    print(f"IpcNode[{self.ipc_id}][{self.__class__.__name__}] ERROR, blocking route {regex} "
                          f"failed to send response: {e}", flush=True)
            else:
                func(self, payload)

        wrapper.regexes = [regex, *args]
        wrapper.thread = thread

        return wrapper

    return decorator


@dataclasses.dataclass
class LogLevels:
    """
    An enum containing all log levels.
    """
    DEBUG: str = "DEBUG"
    INFO: str = "INFO"
    WARNING: str = "WARNING"
    ERROR: str = "ERROR"
    CRITICAL: str = "CRITICAL"


class IpcNode:
    """
    An IPC node used to communicate with other nodes and to log messages.

    .. note::
        This class is not meant to be used directly except if you just need to send messages,
        you should inherit from it and implement your own routes.
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

        #: :class:`dict` A dict mapping a blocking_response_route` to a semaphore and a response field in a list.
        self.blocking_responses = {}

    def _listen(self):
        """
        Listener thread, this thread will listen for new messages and call the appropriate callbacks.
        """
        self.listening = True
        self.log(f"{self.__class__.__name__}(IpcNode) listening on {self.ipc_id}", level=LogLevels.DEBUG)
        while self.subscribed:
            message = self.pubsub.get_message()

            # No message
            if message is None or message["type"] != "message":
                time.sleep(0.001)
                continue

            try:
                payload = pickle.loads(message["data"])
                if "sender" not in payload or "loopback" not in payload or "data" not in payload or "route" not in payload:
                    raise Exception("Malformed request")
                data = pickle.loads(payload["data"])
            except Exception as e:
                self.log(f"{self.__class__.__name__}(IpcNode) received malformed request: {message}, "
                         f"Exception:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}",
                         level=LogLevels.ERROR)
                continue

            if not payload["loopback"] and payload["sender"] == self.ipc_id:
                continue

            if payload["route"] in self.blocking_responses:
                self.log(f"{self.__class__.__name__}(IpcNode) received blocking request {payload['route']}:"
                         f" {data}", level=LogLevels.DEBUG)
                self.blocking_responses[payload["route"]][1] = data
                self.blocking_responses[payload["route"]][0].release()
                continue

            for regex in self.regexes:
                if re.match(regex, payload["route"]) is not None:
                    try:
                        self.log(f"{self.__class__.__name__}(IpcNode) received request {payload['route']}:"
                                 f" {data}", level=LogLevels.DEBUG)
                        self.regexes[regex][0](data) if not self.regexes[regex][1] else threading.Thread(
                            target=self.regexes[regex][0], args=(data,)).start()
                    except Exception as e:
                        self.log(f"{self.__class__.__name__}(IpcNode) failed to process request {regex} "
                                 f"{payload['route']}:  {data}, "
                                 f"Exception:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}",
                                 level=LogLevels.ERROR)

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
        self.log(f"{self.__class__.__name__}(IpcNode) stopped listening on {self.ipc_id}", level=LogLevels.DEBUG)
        self.r.close()

    def send(self, route: str, data: object, loopback: bool = False, _nolog: bool = False):
        """
        Send a message to a route.

        :param str route: The route that will be matched with regexes given in :meth:`route <route>` decorator.
        :param object data: Extra data to send as a dict, this data will be passed to the callback function. This data
            must be pickle serializable.
        :param bool loopback: If True, this node will be able to receive the message. defaults to False.
        """
        req = {"route": route, "sender": self.ipc_id, "loopback": loopback, "data": pickle.dumps(data)}
        self.r.publish("ipc", pickle.dumps(req))
        if not _nolog:
            self.log(f"{self.__class__.__name__}(IpcNode) sent request {req}", level=LogLevels.DEBUG)

    def send_blocking(self, route: str, data: dict, loopback: bool = False, timeout: float = 5.0):
        """
        Send a message to a blocking route and wait for the response / raise the exception.

        :param str route: The route that will be matched with regexes given in :meth:`route <route>` decorator.

        .. warning::
            The given route has to match only one blocking route regex, see :meth:`route <route>` decorator.

        :param dict data: Extra data to send as a dict, this data will be passed to the callback function.
        :param bool loopback: If True, this node will be able to receive the message. defaults to False.
        :param float timeout: Timeout in seconds, defaults to 5.0, will return None if timeout is reached.

        :return: The response data of the blocking callback, None if this was returned by the callback or if timeout
            is reached or if an error occurred in the callback return value serialization.

        .. warning::
            Always correctly check the return value of this function and catch the exception if any.

        :raises: The exception raised by the callback if any.
        """
        blocking_route = f"ipc-blocking-{str(uuid.uuid4())}"
        req = {"route": route, "sender": self.ipc_id, "loopback": loopback,
               "data": pickle.dumps(data | {IPC_BLOCKING_RESPONSE_ROUTE: blocking_route})}
        self.pubsub.subscribe(blocking_route)
        self.blocking_responses[blocking_route] = [threading.Semaphore(0), None]
        self.r.publish("ipc", pickle.dumps(req))
        self.log(f"{self.__class__.__name__}(IpcNode) sent blocking request {req}", level=LogLevels.DEBUG)
        self.blocking_responses[blocking_route][0].acquire(timeout=timeout)
        self.pubsub.unsubscribe(blocking_route)
        r = self.blocking_responses[blocking_route][1]
        del self.blocking_responses[blocking_route]
        if isinstance(r, Exception):
            raise r
        else:
            return r

    def log(self, message: str, level: str = LogLevels.INFO, label: str = None, extra_route: str = ""):
        """
        Log a message to stdout and to ipc system as "log.{level}.{label}" route.

        :param str message: The message to log.
        :param str level: The log level, pick it from :meth:`LogLevels <LogLevels>`, defaults to LogLevels.INFO.
        :param str label: A label, generally the name of the service or the component that is logging the message,
            defaults to class name.
        :param str extra_route: An additional extra route that will be appended to the route, for example, if I give
            `a.b.c` as extra route, the message will be sent to `log.{level}.{label}.a.b.c` route, defaults to ""
            (resulting in `log.{level}.{label}` route).
        """
        label = label if label is not None else self.__class__.__name__
        route = f"log.{level}.{label}.{extra_route}" if extra_route != "" else f"log.{level}.{label}"
        log = {"label": label, "level": level, "message": message, "timestamp": time.time()}
        self.send(route, log, loopback=True, _nolog=True)
        if not level == LogLevels.DEBUG or os.environ["DEBUG"] == "1":
            print(f"[{datetime.datetime.fromtimestamp(log['timestamp']).strftime('%d-%m-%Y %H:%M:%S')}] "
                  f"{level.upper()}@{label}: {message}", flush=True)


# Override stdout & stderr
class _StdOverrider:

    def __init__(self, target):
        self.label = target
        self.bkp = sys.stdout if target == "stdout" else sys.stderr  # Backup
        self.r = redis.Redis(host='redis-ipc', port=6379, db=0)
        if target == "stdout":
            sys.stdout = self
        else:
            sys.stderr = self

    def write(self, message):
        req = {"route": self.label, "sender": "sys", "loopback": False, "data": pickle.dumps({"message": message})}
        self.r.publish("ipc", pickle.dumps(req))
        self.bkp.write(message)

    def flush(self):
        self.bkp.flush()


_StdOverrider("stdout")
_StdOverrider("stderr")

if __name__ == '__main__':
    class PingPongNode(IpcNode):

        # I register a ping route, all messages sent to `ping` route will be received by this function
        @route("ping")
        def ping(self, payload: dict):
            self.log("Ping!")

            # I send a message to the `pong` route, since I want this node to receive it, I set `loopback` to True.
            self.send("pong", {"extra_message": "Hello World!"}, loopback=True)

        # I register a pong route, all messages sent to `pong` route will be received by this function
        @route("pong")
        def pong(self, payload: dict):
            self.log("Pong!")
            # I can access the data sent by the ping function
            self.log(payload["extra_message"])

        # I register a blocking route, all messages sent to `return_pi` route will be received by this function
        # Value will be sent back to the sender
        @route("return_pi", blocking=True, thread=True)
        def return_pi(self, payload: dict):
            return 3.14159265359


    # I create a new node called `ipc-node-test`
    n = PingPongNode("ipc-node-test")
    # I start the node
    n.start()
    # I send a message to the `ping` route and use `loopback` since I want to receive it with the same node
    n.send("ping", {}, loopback=True)
    # I send a message to the `return_pi`  blocking route, this will wait for the response
    n.log(n.send_blocking("return_pi", {}, loopback=True), level=LogLevels.DEBUG)
    # I don't forget to stop the node !
    n.stop()
