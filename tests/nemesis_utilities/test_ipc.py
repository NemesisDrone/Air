import time
import unittest.mock

import pytest
from unittest.mock import Mock

import redis
from utilities import ipc
from utilities import logger as lg


# --- Call Data --- #
@pytest.fixture
def calldata_kwargs():
    return {
        "channel": "test_channel",
        "sender": "test_sender",
        "loopback": True,
        "payload": {"key": "value"},
        "concurrent": True,
        "blocking_response_channel": "response_channel"
    }


@pytest.fixture
def calldata(calldata_kwargs):
    return ipc.CallData(**calldata_kwargs)


def test_calldata_properties_with_blocking(calldata_kwargs, calldata):
    assert calldata.channel == calldata_kwargs["channel"]
    assert calldata.sender == calldata_kwargs["sender"]
    assert calldata.loopback == calldata_kwargs["loopback"]
    assert calldata.payload == calldata_kwargs["payload"]
    assert calldata.concurrent == calldata_kwargs["concurrent"]
    assert calldata.blocking_response_channel == calldata_kwargs["blocking_response_channel"]
    assert calldata.blocking


def test_calldata_properties_without_blocking(calldata_kwargs, calldata):
    calldata._blocking_response_channel = None
    assert not calldata.blocking


def test_calldata_dumps_and_loads(calldata_kwargs, calldata):
    dumps = calldata.dumps()
    loads = ipc.CallData.loads(dumps)
    assert loads.channel == calldata_kwargs["channel"]
    assert loads.sender == calldata_kwargs["sender"]
    assert loads.loopback == calldata_kwargs["loopback"]
    assert loads.payload == calldata_kwargs["payload"]
    assert loads.concurrent == calldata_kwargs["concurrent"]
    assert loads.blocking_response_channel == calldata_kwargs["blocking_response_channel"]
    assert loads.blocking


# --- Route --- #
@pytest.fixture
def route_kwargs():
    return {
        "regexes": ["a:b:c", "a:b:d:*"],
        "concurrent": False
    }


@pytest.fixture
def route(route_kwargs):
    return ipc.Route(**route_kwargs)


def test_route_init(route_kwargs, route):
    assert route._regexes == ["^a:b:c$", "^a:b:d:.*$"]
    assert route._concurrent == route_kwargs["concurrent"]
    assert route._decorator == route._wrap
    assert route._wrapped_function is None
    assert route._ipc_node is None
    assert route._object is None


def test_route_match(route):
    assert route.match("a:b:c")
    assert route.match("a:b:d:e")
    assert not route.match("a:b:e")
    assert not route.match("a:b:d")
    assert route.match("a:b:d:e:f")


def test_route_bind(route):
    mock_ipc_node = Mock()
    mock_object = Mock()

    route.bind(mock_ipc_node, mock_object)

    assert route._ipc_node == mock_ipc_node
    assert route._object == mock_object


def test_route_decorator(route):
    @route.decorator
    def example_function(self, call_data, payload):
        pass

    with pytest.raises(ValueError):
        @route.decorator
        def invalid_function(self, payload):  # Missing 'call_data' parameter
            pass

    assert route._wrapped_function is not None

    with pytest.raises(RuntimeError):
        example_function(None, None, None)


def test_route_call(route):
    mock_ipc_node = Mock()
    mock_ipc_node.logger = Mock()
    mock_function = Mock()
    call_data = ipc.CallData("a:b:c", "sender", False, {"a": "b"}, False, None)

    def function(self, call_data, payload):
        mock_function(self, call_data, payload)

    route.decorator(function)
    route.bind(mock_ipc_node, mock_ipc_node)

    # Test basic call
    route.call(call_data)

    mock_function.assert_called_once_with(
        mock_ipc_node,
        call_data,
        {"a": "b"}
    )

    # Test basic call with exception
    mock_function.reset_mock()
    mock_function.side_effect = Exception("test")

    route.call(call_data)
    mock_function.assert_called_once_with(
        mock_ipc_node,
        call_data,
        {"a": "b"}
    )
    mock_ipc_node.logger.error.assert_called_once()

    # Test blocking call
    mock_function.reset_mock()
    call_data._blocking_response_channel = "response_channel"

    route.call(call_data)
    mock_function.assert_called_once_with(
        mock_ipc_node,
        call_data,
        {"a": "b"}
    )
    mock_ipc_node.send.assert_called_once()

    # Test blocking call with exception
    mock_function.reset_mock()
    mock_function.side_effect = Exception("test")

    route.call(call_data)
    mock_function.assert_called_once_with(
        mock_ipc_node,
        call_data,
        {"a": "b"}
    )

    # test concurrent call
    mock_function.reset_mock()
    call_data._concurrent = True

    route.call(call_data)
    mock_function.assert_called_once_with(
        mock_ipc_node,
        call_data,
        {"a": "b"}
    )


# --- IpcNode --- #
@pytest.fixture
def ipc_node_kwargs():
    return {
        "ipc_id": "test_ipc_id",
        "strict_redis": Mock(),
        "pubsub": Mock(),
    }


def test_ipc_node_init(ipc_node_kwargs):
    with unittest.mock.patch("utilities.ipc.IpcNode.bind_routes") as mock_bind_routes:
        ipc_node = ipc.IpcNode(**ipc_node_kwargs)

        assert mock_bind_routes.called
        assert ipc_node._ipc_id == ipc_node_kwargs["ipc_id"]
        assert ipc_node._redis == ipc_node_kwargs["strict_redis"]
        assert ipc_node._pubsub == ipc_node_kwargs["pubsub"]
        assert ipc_node._logger is None
        assert ipc_node._routes == []
        assert ipc_node._blocking_responses == {}


def test_ipc_node_properties(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)

    assert ipc_node.ipc_id == ipc_node_kwargs["ipc_id"]
    assert ipc_node.logger is None
    assert ipc_node.redis == ipc_node_kwargs["strict_redis"]


def test_ipc_node_fetch_routes(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)

    mock_generic_object = Mock()
    ipc_node.generic_object = mock_generic_object
    ipc_node.bind_routes(ipc_node)
    assert mock_generic_object not in ipc_node._routes

    ipc_node._routes = []
    route = ipc.Route(["a:b:c"], False)
    mock_route = Mock()
    mock_route.route = route
    ipc_node.mock_route = mock_route
    ipc_node.bind_routes(ipc_node)
    assert route in ipc_node._routes


def test_ipc_node_logger(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)

    logger_obj = Mock()
    ipc_node.set_logger(logger_obj)

    assert ipc_node._logger == logger_obj


def test_ipc_node_fetch_ipc(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    # None message
    mock_pubsub = ipc_node_kwargs["pubsub"]
    mock_pubsub.get_message.return_value = None
    assert ipc_node._fetch_ipc() is None

    # Wrong type message
    mock_pubsub.get_message.return_value = {"type": "wrong_type"}
    assert ipc_node._fetch_ipc() is None

    # Connection error
    mock_pubsub.get_message.side_effect = redis.exceptions.ConnectionError("test")
    assert ipc_node._fetch_ipc() is None
    ipc_node.logger.warning.assert_called_once()

    # Valid message
    mock_pubsub.get_message.side_effect = None
    mock_pubsub.get_message.return_value = {"type": "message"}
    assert ipc_node._fetch_ipc() == {"type": "message"}


def test_ipc_node_parse_ipc(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    # None message
    assert ipc_node._parse_ipc(None) is None

    # Invalid message
    with pytest.raises(Exception):
        ipc_node._parse_ipc({"data": "invalid"})

    # Non Loopback message
    call_data = ipc.CallData("channel", ipc_node.ipc_id, False, {"a": "b"}, False, None)
    assert ipc_node._parse_ipc({"data": call_data.dumps()}) is None

    # Loopback message
    call_data = ipc.CallData("channel", ipc_node.ipc_id, True, {"a": "b"}, False, None)
    assert type(ipc_node._parse_ipc({"data": call_data.dumps()})) is ipc.CallData


def test_ipc_node_fetch_call_data(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    mock_fetch_ipc = Mock()
    mock_parse_ipc = Mock()

    with unittest.mock.patch("utilities.ipc.IpcNode._fetch_ipc", mock_fetch_ipc):
        with unittest.mock.patch("utilities.ipc.IpcNode._parse_ipc", mock_parse_ipc):
            # Valid message
            mock_message = Mock()
            mock_fetch_ipc.return_value = mock_message
            mock_parse_ipc.return_value = None

            assert ipc_node._fetch_call_data() is None
            mock_fetch_ipc.assert_called_once()
            mock_parse_ipc.assert_called_once_with(mock_message)

            # Error when casting
            mock_fetch_ipc.reset_mock()
            mock_parse_ipc.reset_mock()
            mock_parse_ipc.side_effect = Exception("test")

            assert ipc_node._fetch_call_data() is None
            ipc_node.logger.error.assert_called_once()


def test_ipc_node_handle_blocking_response(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    mock_call_data = Mock()
    mock_call_data.channel = "response_channel"

    # Test response channel not in blocking responses
    assert not ipc_node._handle_blocking_response(mock_call_data)
    ipc_node.logger.assert_not_called()

    # Test response channel in blocking responses
    ipc_node._blocking_responses["response_channel"] = {"response": None, "lock": Mock()}
    assert ipc_node._handle_blocking_response(mock_call_data)
    ipc_node.logger.debug.assert_called_once()
    assert mock_call_data == ipc_node._blocking_responses["response_channel"]["response"]
    ipc_node._blocking_responses["response_channel"]["lock"].release.assert_called_once()


def test_ipc_node_handle_message(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    mock_routes = [Mock(), Mock()]
    mock_routes[0].match.return_value = False
    mock_routes[1].match.return_value = True
    mock_routes[1].call.return_value = None

    ipc_node._routes = mock_routes

    mock_call_data = Mock()
    mock_call_data.channel = "channel"

    ipc_node._handle_message(mock_call_data)
    mock_routes[0].match.assert_called_once_with("channel")
    mock_routes[1].match.assert_called_once_with("channel")
    mock_routes[0].call.assert_not_called()
    mock_routes[1].call.assert_called_once_with(mock_call_data)
    ipc_node.logger.debug.assert_called_once()


def test_ipc_log_received_message(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())
    mock_call_data = Mock()
    mock_call_data.payload = "payload"

    ipc_node._log_received_message(mock_call_data)
    ipc_node.logger.debug.assert_called_once()


def test_ipc_node_listener(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    with unittest.mock.patch("utilities.ipc.IpcNode._fetch_call_data") as mock_fetch_call_data:
        with unittest.mock.patch("utilities.ipc.IpcNode._handle_blocking_response") as mock_handle_blocking_response:
            with unittest.mock.patch("utilities.ipc.IpcNode._handle_message") as mock_handle_message:
                with unittest.mock.patch("utilities.ipc.IpcNode._log_received_message") as mock_log_msg:
                    mock_call_data = Mock()

                    # test not alive
                    ipc_node._alive = False
                    ipc_node._listener()
                    mock_fetch_call_data.assert_not_called()
                    mock_handle_blocking_response.assert_not_called()
                    mock_handle_message.assert_not_called()
                    ipc_node.logger.debug.reset_mock()

                    # test fetch call data returns None
                    def side_effect():
                        ipc_node._alive = False
                        return None

                    ipc_node._alive = True
                    mock_fetch_call_data.side_effect = side_effect

                    ipc_node._listener()

                    mock_fetch_call_data.assert_called_once()
                    mock_handle_blocking_response.assert_not_called()
                    mock_handle_message.assert_not_called()

                    # test fetch call data returns call data and handle blocking response returns True
                    ipc_node._alive = True
                    mock_fetch_call_data.reset_mock()
                    mock_call_data = Mock()

                    def side_effect():
                        ipc_node._alive = False
                        return mock_call_data

                    mock_fetch_call_data.side_effect = side_effect
                    mock_handle_blocking_response.return_value = True

                    ipc_node._listener()

                    mock_fetch_call_data.assert_called_once()
                    mock_handle_blocking_response.assert_called_once_with(mock_call_data)
                    mock_handle_message.assert_not_called()

                    mock_handle_blocking_response.reset_mock()

                    # test fetch call data returns call data and handle blocking response returns False
                    ipc_node._alive = True
                    mock_fetch_call_data.reset_mock()
                    mock_call_data = Mock()

                    def side_effect():
                        ipc_node._alive = False
                        return mock_call_data

                    mock_fetch_call_data.side_effect = side_effect
                    mock_handle_blocking_response.return_value = False

                    ipc_node._listener()

                    mock_fetch_call_data.assert_called_once()
                    mock_handle_blocking_response.assert_called_once_with(mock_call_data)
                    mock_handle_message.assert_called_once_with(mock_call_data)


def test_ipc_node_start(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    with unittest.mock.patch("threading.Thread") as mock_thread:
        mock_thread.return_value = Mock()

        ipc_node.start()

        ipc_node.logger.debug.assert_called_once()
        ipc_node._pubsub.subscribe.assert_called_once()
        assert ipc_node._alive
        mock_thread.assert_called_once_with(target=ipc_node._listener)
        mock_thread.return_value.start.assert_called_once()


def test_ipc_node_stop(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    ipc_node.stop()

    ipc_node.logger.debug.assert_called()
    assert not ipc_node._alive
    ipc_node._pubsub.unsubscribe.assert_called_once()
    ipc_node._pubsub.close.assert_called_once()


def test_ipc_node_send(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    channel = "channel"
    payload = {"a": "b"}
    concurrent = True
    loopback = True

    with unittest.mock.patch("utilities.ipc.CallData") as mock_call_data:
        mock_call_data.return_value = Mock()
        mock_call_data.return_value.dumps.return_value = "dumps"

        ipc_node.send(channel, payload, concurrent, loopback)

        mock_call_data.assert_called_once_with(channel=channel, sender=ipc_node.ipc_id, loopback=loopback,
                                               payload=payload, concurrent=concurrent)
        mock_call_data.return_value.dumps.assert_called_once()
        ipc_node._redis.publish.assert_called_once_with("ipc", "dumps")
        ipc_node.logger.debug.assert_called_once()


def test_ipc_node_create_blocking_request_response_placeholder(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    with unittest.mock.patch("threading.Semaphore") as mock_semaphore:
        mock_semaphore.return_value = Mock()
        mock_call_data = Mock()
        mock_call_data.blocking_response_channel = "channel"

        ipc_node._create_blocking_request_response_placeholder(mock_call_data)

        mock_semaphore.assert_called_once_with(0)
        assert ipc_node._blocking_responses["channel"] == {"response": None, "lock": mock_semaphore.return_value}


def test_ipc_node_wait_for_blocking_response(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    mock_call_data = Mock()
    mock_call_data.blocking_response_channel = "channel"
    mock_call_data.payload = {"response": "test"}

    placeholder = {"response": mock_call_data, "lock": Mock()}
    ipc_node._blocking_responses["channel"] = placeholder

    r = ipc_node._wait_for_blocking_response(mock_call_data, 1)

    placeholder["lock"].acquire.assert_called_once_with(timeout=1)
    assert mock_call_data.blocking_response_channel not in ipc_node._blocking_responses
    assert r == mock_call_data.payload["response"]

    mock_call_data.payload = {"response": Exception("test")}

    with pytest.raises(Exception):
        ipc_node._wait_for_blocking_response(mock_call_data, 1)


def test_ipc_node_send_blocking(ipc_node_kwargs):
    ipc_node = ipc.IpcNode(**ipc_node_kwargs)
    ipc_node.set_logger(Mock())

    channel = "channel"
    payload = {"a": "b"}
    concurrent = True
    loopback = True
    timeout = 1

    with unittest.mock.patch("utilities.ipc.CallData") as mock_call_data:
        with unittest.mock.patch(
                "utilities.ipc.IpcNode._create_blocking_request_response_placeholder") as mock_create_blocking_request_response_placeholder:
            with unittest.mock.patch(
                    "utilities.ipc.IpcNode._wait_for_blocking_response") as mock_wait_for_blocking_response:
                mock_call_data.return_value = Mock()
                mock_call_data.return_value.dumps.return_value = "dumps"

                mock_wait_for_blocking_response.return_value = "response_channel"

                r = ipc_node.send_blocking(channel, payload, concurrent, loopback, timeout)

                # Assert was called with correct arguments, and blocking_response_channel can be anything
                mock_call_data.assert_called_once_with(channel=channel, sender=ipc_node.ipc_id, loopback=loopback,
                                                       payload=payload, concurrent=concurrent,
                                                       blocking_response_channel=unittest.mock.ANY)

                mock_call_data.return_value.dumps.assert_called_once()
                ipc_node._redis.publish.assert_called_once_with("ipc", "dumps")
                mock_create_blocking_request_response_placeholder.assert_called_once_with(mock_call_data.return_value)
                mock_wait_for_blocking_response.assert_called_once_with(mock_call_data.return_value, timeout=timeout)
                ipc_node.logger.debug.assert_called_once()
                assert r == mock_wait_for_blocking_response.return_value


# --- Integration --- #
def test_ipc_integration():
    class TestIpcNode(ipc.IpcNode):
        """
        A test IPC node.
        """

        @ipc.Route(["ping"], False).decorator
        def ping(self, call_data: ipc.CallData, payload: dict):
            self.send("pong", {"extra_message": "Hello World!"}, loopback=True)

        @ipc.Route(["pong"], False).decorator
        def pong(self, call_data: ipc.CallData, payload: dict):
            assert payload["extra_message"] == "Hello World!"

        @ipc.Route(["return_pi"], concurrent=True).decorator
        def return_pi(self, call_data: ipc.CallData, payload: dict):
            return 3.14159265359

    # Instantiate the IPC node
    r = redis.StrictRedis(host="redis", port=6379, db=0)
    node = TestIpcNode(
        "node",
        r,
        r.pubsub()
    )
    node.set_logger(lg.Logger(node))

    # Usage
    node.start()

    node.send("ping", {}, loopback=True)
    assert node.send_blocking('return_pi', {}, loopback=True) == 3.14159265359

    node.stop()


if __name__ == "__main__":
    pytest.main()
