"""Abstracts Redis pub/sub to provide a simple IPC system allowing node to node communication through routes defined
using regular expressions and implemented with a simple decorator.

:class:`IpcTimeoutError` raised when a blocking call times out.

:class:`CallData` represents the data of an IPC function call.

:class:`Route` represents an IPC route used to route IPC function calls.

:class:`IpcNode` represents an IPC node used to communicate with other IPC nodes through redis pub/sub.
"""
import inspect
import pickle
import re
import threading
import traceback
import typing
import uuid

import redis

from utilities import abstracts
from utilities import logger as lg


VERBOSE_PAYLOAD_LOGGING = False


class IpcTimeoutError(Exception):
    """Raised when a blocking call times out."""

    pass


class CallData:
    """Call data of an IPC function call.

    :attr:`channel` The channel the call was sent on.
    :attr:`sender` The sender of the call (ipc node id).
    :attr:`loopback` Whether the call is meant to be received by the sender or not.
    :attr:`payload` The payload of the call.
    :attr:`concurrent` Whether the call is concurrent or not. If set to True, will run the function in a separate
        thread. If set to False, will run the function in the listener thread, the listener will be blocked until the
        function returns.
    :attr:`blocking_response_channel` The channel to send the blocking response on if applicable.
    :attr:`blocking` Whether the call is blocking or not.

    :meth:`dumps` Serialize the calldata into bytes.
    :meth:`loads` Deserialize the calldata from bytes.

    """

    def __init__(
        self,
        channel: str,
        sender: str,
        loopback: bool,
        payload: dict,
        concurrent: bool = None,
        blocking_response_channel: typing.Union[str, None] = None,
    ):
        """Create a new calldata.

        :param channel: The channel the call was sent on.
        :param sender: The sender of the call (ipc node id).
        :param loopback: Whether the call is meant to be received by the sender or not.
        :param payload: The payload of the call.
        :param concurrent: Whether the call is concurrent or not. If set to True, will run the function in a separate
            thread. If set to False, will run the function in the listener thread, the listener will be blocked until
            the function returns.
        :param blocking_response_channel: The channel to send the blocking response on if applicable, defaults to None.
        """

        # Fields are accessed through the properties to ensure immutability.
        self._channel = channel
        self._sender = sender
        self._loopback = loopback
        self._payload = payload
        self._concurrent = concurrent
        self._blocking_response_channel = blocking_response_channel

    @property
    def channel(self) -> str:
        """Get the channel the call was sent on."""
        return self._channel

    @property
    def sender(self) -> str:
        """Get the sender of the call (ipc node id)."""
        return self._sender

    @property
    def loopback(self) -> bool:
        """Get whether the call is meant to be received by the sender or not."""
        return self._loopback

    @property
    def payload(self) -> dict:
        """Get the payload of the call."""
        return self._payload

    @property
    def concurrent(self) -> typing.Union[bool, None]:
        """Whether the call is concurrent or not. If set to True, will run the function in a separate thread. If set to
        False, will run the function in the listener thread, the listener will be blocked until the function returns.
        """
        return self._concurrent

    @property
    def blocking_response_channel(self) -> typing.Union[str, None]:
        """The channel to send the blocking response on if applicable."""
        return self._blocking_response_channel

    @property
    def blocking(self) -> bool:
        """Whether the call is blocking or not."""
        return self._blocking_response_channel is not None

    def dumps(self) -> bytes:
        """Serialize the calldata into bytes through pickle.

        :return: The serialized calldata as bytes.
        """
        return pickle.dumps(
            {
                "channel": self._channel,
                "sender": self._sender,
                "loopback": self._loopback,
                "payload": self._payload,
                "concurrent": self._concurrent,
                "blocking_response_channel": self._blocking_response_channel,
            }
        )

    @staticmethod
    def loads(data: bytes) -> "CallData":
        """Deserialize the calldata from bytes through pickle.

        :param data: The serialized calldata as bytes.

        :return: The deserialized calldata as a :class:`CallData` instance.
        """

        data = pickle.loads(data)

        return CallData(
            channel=data["channel"],
            sender=data["sender"],
            loopback=data["loopback"],
            payload=data["payload"],
            concurrent=data["concurrent"],
            blocking_response_channel=data["blocking_response_channel"],
        )

    def __str__(self):
        return (
            f"CallData(channel={self._channel}, sender={self._sender}, loopback={self._loopback}, "
            f"payload={self._payload}, concurrent={self._concurrent}, "
            f"blocking_response_channel={self._blocking_response_channel})"
        )


class Route:
    """IPC route used to route IPC function calls.

    :attr:`regexes` A list of regular expressions to match against.
    :attr:`decorator` The decorator to wrap the function with.

    :meth:`match` Check if the route matches the given channel.
    :meth:`bind` Bind the route to an IpcNode instance and an object.
    :meth:`call` Call the wrapped function.
    """

    def __init__(self, regexes: typing.List[str], concurrent: bool):
        """Create a new IPC route.

        :param regexes: A list of regular expressions to match against. e.g. ["a:b:c", "a:b:d:*", "a:*:c"]

        .. warning::
            Separators must be ':' and regexes must not contain special characters that would interfere with the
            regex matching.

        :param concurrent: Whether the route is concurrent or not. If the route is concurrent, the function will be
            called in a separate thread. If not, the function will be called in the listener thread, the listener will
            be blocked until the function returns. This parameter can be overridden by the call data.

        .. warning::
            If the route is not concurrent, the function must not send loopback blocking calls to itself as this will
            cause a deadlock.
        """

        # A list of regular expressions to match against. e.g. ["a:b:c", "a:b:d:*", "a:*:c"]
        self._regexes = self._parse_regexes(regexes)

        # The wrapped function. Set when the decorator is called.
        self._wrapped_function = None

        # The Ipc Node instance.
        self._ipc_node = None

        # The Object associated with the self argument of the function.
        self._object = None

        # Accessible through property to ensure immutability.
        self._concurrent = concurrent
        self._decorator = self._wrap

    @staticmethod
    def _parse_regexes(regexes: typing.List[str]) -> typing.List[str]:
        """Parse the given regexes to allow for simple from of given regexes."""
        return [f"^{r.replace('*', '.*')}$" for r in regexes]

    @property
    def regexes(self) -> typing.List[str]:
        """Get the regexes."""
        return self._regexes

    def match(self, channel: str) -> bool:
        """Check if the route matches the channel.

        :param channel: The channel to match against.

        :return: True if the route matches the channel, False otherwise.
        """
        return any([re.match(r, channel) for r in self._regexes])

    def bind(self, ipc_node: "IpcNode", route_object: object) -> None:
        """Bind the route to an IpcNode instance and an object.

        :param ipc_node: The :class:`IpcNode` instance.
        :param route_object: The object associated with the self argument of the function.
        """
        self._ipc_node = ipc_node
        self._object = route_object

    @staticmethod
    def _check_function_signature(function: typing.Callable) -> typing.Union[None, str]:
        """Check the function signature. The function signature must have 3 named parameters: `self`, `calldata`,
        `payload`.

        :param function: The function to check.

        :return: None if the function signature is valid, an error message otherwise.
        """
        signature = inspect.signature(function)

        if len(signature.parameters) != 3 or not all(
            [p in signature.parameters for p in ["self", "call_data", "payload"]]
        ):
            return (
                f"Function must have 3 named parameters: self, call_data, payload. Your function has only "
                f"{len(signature.parameters)} parameters: {', '.join(signature.parameters.keys())}"
            )

        return None

    def _wrap(self, function: typing.Callable) -> typing.Callable:
        """Disable direct function calls and save the wrapped function.

        :param function: The function to wrap.

        .. warning::
            The function signature must have 3 named parameters: `self`, `call_data`, `payload`.

        :return: The dead wrapper used to disable direct function calls.

        :raises ValueError: If the function signature is invalid.
        """
        error = self._check_function_signature(function)
        if error is not None:
            raise ValueError(error)

        self._wrapped_function = function

        def dead_wrapper(_self, call_data: CallData, payload: dict) -> typing.Union[None, typing.Any]:
            raise RuntimeError(
                f"You can no longer call this function directly, call it using the following ipc routes "
                f"instead: {', '.join(self._regexes)}"
            )

        dead_wrapper.__setattr__("route", self)

        return dead_wrapper

    @property
    def decorator(self) -> typing.Callable:
        """Get the route decorator.

        :return: The route decorator.
        """
        return self._decorator

    def _call(self, call_data: CallData) -> None:
        """Call the wrapped function.

        :param call_data: The call data.
        """
        try:
            self._wrapped_function(self._object, call_data, call_data.payload)
        except Exception as e:
            self._ipc_node.logger.error(
                f"IPC Node, an error occurred when calling a function.\n"
                f"Call Data: {call_data}\n"
                f"Exception: {''.join(traceback.format_exception(type(e), e, e.__traceback__))}",
                label=self._ipc_node.ipc_id,
            )

    def _call_blocking(self, call_data: CallData) -> None:
        """Call the wrapped function and send the response.

        :param call_data: The call data.
        """
        try:
            r = self._wrapped_function(self._object, call_data, call_data.payload)
        except Exception as e:
            r = e

        try:
            self._ipc_node.send(call_data.blocking_response_channel, {"response": r}, loopback=True, _nolog=True)
        except pickle.PicklingError as e:
            self._ipc_node.logger.error(
                f"IPC Node failed to pickle blocking request return value.\nReturn value: {r}\nException: {e}\n"
                f"Initial Call Data: {call_data}",
                label=self._ipc_node.ipc_id,
            )
            r = None
            self._ipc_node.send(call_data.blocking_response_channel, {"response": r}, loopback=True, _nolog=True)

    def call(self, call_data: CallData) -> None:
        """Call the wrapped function.

        :param call_data: The call data.
        """
        # Not bound yet.
        assert self._ipc_node is not None
        assert self._object is not None

        if self._concurrent or call_data.concurrent:
            thread = threading.Thread(
                target=self._call_blocking if call_data.blocking else self._call, args=(call_data,)
            )
            thread.start()
        else:
            self._call(call_data) if not call_data.blocking else self._call_blocking(call_data)


class IpcNode(abstracts.IIpcSender):
    """An IPC node, communicates with other IPC nodes through redis pub/sub.

    :attr:`logger` The :class:`Logger` instance.
    :attr:`ipc_id` The IPC node unique id.
    :attr:`redis` The redis client.

    :meth:`set_logger` Set the logger instance.
    :meth:`start` Start the IPC node.
    :meth:`stop` Stop the IPC node.
    :meth:`send` Send a message to the IPC.
    :meth:`send_blocking` Send a blocking message to the IPC, wait for the response and return it.
    """

    def __init__(
        self,
        ipc_id: str,
        strict_redis: redis.client.StrictRedis,
        pubsub: redis.client.PubSub,
    ):
        """Create a new IPC node.

        :param ipc_id: The IPC node unique id.
        :param strict_redis: The redis client.
        :param pubsub: The pubsub client.
        """

        #: pubsub client.
        self._pubsub = pubsub

        #: alive flag to kill the listener thread.
        self._alive = False

        #: blocking responses dict.
        self._blocking_responses = {}

        # Accessible through property to ensure immutability.
        self._ipc_id = ipc_id
        self._logger = None
        self._redis = strict_redis

        #: routes.
        self._routes = []
        self.bind_routes(self)

    def bind_routes(self, route_object: object) -> None:
        """Fetch every method of the given object with a route attribute and add the associated route to the routes
            list.

        :param route_object: The object to fetch the routes from.
        """
        routes = [
            route_object.__getattribute__(attr).route
            for attr in dir(route_object)
            if hasattr(getattr(route_object, attr), "route") and isinstance(getattr(route_object, attr).route, Route)
        ]
        for route in routes:
            route.bind(self, route_object)

        self._routes += routes

    @property
    def logger(self) -> lg.Logger:
        """Get the logger."""
        return self._logger

    @property
    def ipc_id(self) -> str:
        """Get the IPC node unique id."""
        return self._ipc_id

    @property
    def redis(self) -> redis.client.StrictRedis:
        """Get the redis client."""
        return self._redis

    def set_logger(self, logger: lg.Logger) -> None:
        """Set the logger instance.

        :param logger: The logger.
        """
        self._logger = logger

    def _fetch_ipc(self) -> typing.Union[None, dict]:
        """Fetch a message from redis pubsub.

        :return: The message or None if no message was received.
        """
        try:
            msg = self._pubsub.get_message(True, timeout=0.1)
        except redis.exceptions.ConnectionError as e:
            self._logger.warning(
                f"IPC Node failed to fetch message from redis pubsub: '{e}'. "
                f"Ignore this warning if it doesn't persist.",
                label=self._ipc_id,
            )
            return None

        if msg is None or msg["type"] != "message":
            return None
        return msg

    def _parse_ipc(self, msg: typing.Union[None, dict]) -> typing.Union[None, CallData]:
        """Cast a message received from redis pubsub into CallData.

        :param msg: The message.

        :return CallData: The CallData if the message is valid, None otherwise.

        :raises Exception: If the message is malformed.
        """
        if msg is None:
            return None

        try:
            call_data = CallData.loads(msg["data"])
            if call_data.sender == self._ipc_id and not call_data.loopback:
                return None
        except Exception as e:
            raise Exception(f"Failed to decode message: '{e}', raw message data is: '{msg['data']}'")

        return call_data

    def _fetch_call_data(self) -> typing.Union[None, CallData]:
        """Run the messages pipeline and return call data or None if no message was received.

        :return CallData: The CallData if the message is valid, None otherwise.
        """
        message = self._fetch_ipc()
        call_data = None
        try:
            call_data = self._parse_ipc(message)
        except Exception as e:
            self._logger.error(
                f"IPC Node error when parsing a message.\nMessage: {message}\nException: {e}", label=self._ipc_id
            )

        return call_data

    def _handle_blocking_response(self, call_data: CallData) -> bool:
        """Handle a blocking response.

        :param call_data: The call data.
        """
        if call_data.channel in self._blocking_responses:
            self._log_received_message(call_data)
            self._blocking_responses[call_data.channel]["response"] = call_data
            self._blocking_responses[call_data.channel]["lock"].release()
            return True
        return False

    def _handle_message(self, call_data: CallData) -> None:
        """Handle a message by matching it against the routes and calling the route if it matches.

        :param call_data: The call data.
        """
        for route in self._routes:
            if route.match(call_data.channel):
                self._log_received_message(call_data)
                route.call(call_data)

    def _log_received_message(self, call_data: CallData) -> None:
        """Log a received message.

        :param call_data: The call data.
        """
        self._logger.debug(f"IPC Node received message.\n\tCall data: {call_data}", label=self._ipc_id)

    def _listener(self) -> None:
        """Listen for incoming messages and handle them."""

        self.logger.debug("Starting IPC Node listener thread.", label=self._ipc_id)

        while self._alive:
            try:
                call_data = self._fetch_call_data()
            except ValueError as e:
                # Silent exception, ipc is closed.
                self._alive = False
                continue

            if call_data is None:
                continue

            if self._handle_blocking_response(call_data):
                continue

            self._handle_message(call_data)

    def start(self) -> None:
        """Start the IPC node."""
        self._logger.debug("Starting IPC node.", label=self._ipc_id)
        self._pubsub.subscribe("ipc")
        self._alive = True
        threading.Thread(target=self._listener).start()

    def stop(self) -> None:
        """Stop the IPC node."""
        self._logger.debug("Stopping IPC node.", label=self._ipc_id)
        self._alive = False
        self._pubsub.unsubscribe("ipc")
        self._pubsub.close()
        self._redis.close()

    def send(
        self, channel: str, payload: dict, concurrent: bool = None, loopback: bool = False, _nolog: bool = False
    ) -> None:
        """Send a message to the IPC.

        :param channel: The channel to send the message on.
        :param payload: The payload to send as a dict.
        :param concurrent: Whether the message is concurrent or not. If set, will override the route concurrent
            parameter. If set to True, will run the function in a separate thread. If set to False, will run the
            function in the listener thread, the listener will be blocked until the function returns.
        :param loopback: Whether the message is a loopback or not.
        :param _nolog: Whether to log the message or not.
        """

        call_data = CallData(
            channel=channel, sender=self._ipc_id, loopback=loopback, payload=payload, concurrent=concurrent
        )

        self._redis.publish("ipc", call_data.dumps())

        if not _nolog:
            pass
            self._logger.debug(f"Sent message, call data: {call_data}", label=self._ipc_id)

    def _create_blocking_request_response_placeholder(self, call_data: CallData) -> None:
        """Create a blocking request response placeholder.

        :param call_data: The call data.
        """
        self._blocking_responses[call_data.blocking_response_channel] = {
            "response": None,
            "lock": threading.Semaphore(0),
        }

    def _wait_for_blocking_response(self, call_data: CallData, timeout: float = 5.0) -> typing.Union[None, CallData]:
        """Wait for a blocking response.

        :param call_data: The call data.
        :param timeout: The timeout in seconds.

        :return: The response call data / None.

        :raises Exception: Any exception raised by the function.
        """
        r = self._blocking_responses[call_data.blocking_response_channel]["lock"].acquire(timeout=timeout)
        if r:
            response = self._blocking_responses[call_data.blocking_response_channel]["response"].payload["response"]
            del self._blocking_responses[call_data.blocking_response_channel]

            if isinstance(response, Exception):
                raise response

            return response
        else:
            raise TimeoutError(
                f"Timeout when waiting for blocking response, try to increase timeout, " f"call data: {call_data}"
            )

    def send_blocking(
        self,
        channel: str,
        payload: dict,
        concurrent: bool = None,
        loopback: bool = False,
        timeout: float = 5.0,
        _nolog: bool = False,
    ) -> typing.Union[None, CallData]:
        """Send a blocking message to the IPC, wait for the response and return it.

        :param channel: The channel to send the message on.
        :param payload: The payload to send as a dict.
        :param concurrent: Whether the message is concurrent or not. If set, will override the route concurrent
            parameter. If set to True, will run the function in a separate thread. If set to False, will run the
            function in the listener thread, the listener will be blocked until the function returns.
        :param loopback: Whether the message is a loopback or not.
        :param timeout: The timeout in seconds.
        :param _nolog: Whether to log the message or not.

        :return: The response call data / raise the exception.

        :raises TimeoutError: If the timeout is reached.
        :raises Exception: Any exception raised by the function.
        """
        call_data = CallData(
            channel=channel,
            sender=self._ipc_id,
            loopback=loopback,
            payload=payload,
            concurrent=concurrent,
            blocking_response_channel=f"{channel}:{self._ipc_id}:{str(uuid.uuid4())}",
        )

        self._create_blocking_request_response_placeholder(call_data)

        self._redis.publish("ipc", call_data.dumps())

        if not _nolog:
            pass
            self._logger.debug(f"Sent blocking message, call data: {call_data}", label=self._ipc_id)

        return self._wait_for_blocking_response(call_data, timeout=timeout)
