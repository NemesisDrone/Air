"""
Functional tests for the nemesis_utilities.ipc module.
"""
import time

import pytest
from unittest.mock import Mock

from utilities import ipc


def test_ipc_node_creation():
    """
    Test the creation of an IPC node.
    """
    node1 = ipc.IpcNode("test_node1")
    node2 = ipc.IpcNode("test_node2")

    # Check ipc node id
    assert node1.ipc_id == "test_node1"
    assert node2.ipc_id == "test_node2"

    # Check redis connection
    node1.r.set("test_key", "test_value")
    assert node1.r.get("test_key") == b"test_value"
    assert node2.r.get("test_key") == b"test_value"

    # Check redis pubsub
    node2.pubsub.subscribe("test_channel")
    node1.r.publish("test_channel", "test_message")
    node2.pubsub.get_message()
    assert node2.pubsub.get_message()["data"] == b"test_message"


def test_route():
    mock_func = Mock()
    mock_func.return_value = "test_return_value"
    mock_func_exception = Mock()
    mock_func_exception.side_effect = Exception("test_exception")
    mock_ipc_node = Mock()

    non_blocking_dec = ipc.route("test_channel", "test_channel:*", blocking=False, thread=True)
    blocking_dec = ipc.route("test_channel", "test_channel:*", blocking=True, thread=False)

    wrap = non_blocking_dec(mock_func)
    wrap_exception = non_blocking_dec(mock_func_exception)
    wrap_blocking = blocking_dec(mock_func)
    wrap_blocking_exception = blocking_dec(mock_func_exception)

    # Test non-blocking decorator
    assert wrap.regexes == ["^test_channel$", "^test_channel:.*$"]
    assert wrap.thread
    wrap(mock_ipc_node, {"payload": "payload"})
    mock_ipc_node.send.assert_not_called()
    mock_func.assert_called_once_with(mock_ipc_node, {"payload": "payload"})

    # catch exception using pytest.raises
    with pytest.raises(Exception) as e:
        wrap_exception(mock_ipc_node, {"payload": "payload"})
    assert str(e.value) == "test_exception"
    mock_ipc_node.send.assert_not_called()
    mock_func_exception.assert_called_once_with(mock_ipc_node, {"payload": "payload"})

    # Test blocking decorator
    assert wrap_blocking.regexes == ["^test_channel$", "^test_channel:.*$"]
    assert not wrap_blocking.thread
    wrap_blocking(mock_ipc_node, {"payload": "payload", ipc.IPC_BLOCKING_RESPONSE_ROUTE: "resp_route"})
    mock_ipc_node.send.assert_called_once_with("resp_route", "test_return_value", loopback=True)

    assert wrap_blocking_exception.regexes == ["^test_channel$", "^test_channel:.*$"]
    assert not wrap_blocking_exception.thread
    wrap_blocking_exception(mock_ipc_node, {"payload": "payload", ipc.IPC_BLOCKING_RESPONSE_ROUTE: "resp_route"})
    mock_ipc_node.send.assert_called_with("resp_route", mock_func_exception.side_effect, loopback=True)


def test_ipc_node():
    class Node(ipc.IpcNode):
        @ipc.route("t:a", "t:b", blocking=False, thread=False)
        def _cb1(self, payload):
            self.r.set(payload["key"], payload["value"])

        @ipc.route("t:*", blocking=False, thread=False)
        def _cb2(self, payload):
            self.r.set(payload["key"] + "all", payload["value"])

        @ipc.route("t2", blocking=True, thread=False)
        def _cb3(self, payload):
            self.r.set(payload["key"], payload["value"])
            return payload

        @ipc.route("t2ex", blocking=True, thread=False)
        def _cb4(self, payload):
            raise Exception("test_exception")

    node1 = Node("test_node1")
    node1.start()
    node2 = Node("test_node2")
    node2.start()

    # Test basic functionality
    node1.send("t:a", {"key": "test_key2", "value": "test_value2"})
    time.sleep(0.1)
    assert node2.r.get("test_key2") == b"test_value2"
    # Test additional route
    node1.send("t:b", {"key": "test_key3", "value": "test_value3"})
    time.sleep(0.1)
    assert node1.r.get("test_key3") == b"test_value3"
    # Test generic route
    assert node2.r.get("test_key2all") == b"test_value2"
    assert node2.r.get("test_key3all") == b"test_value3"
    # Test FaF on blocking route
    node1.send("t2", {"key": "test_key4", "value": "test_value4"})
    time.sleep(0.1)
    assert node2.r.get("test_key4") == b"test_value4"
    # Test blocking on blocking route
    assert node1.send_blocking("t2", {"key": "test_key5", "value": "test_value5"}) == {"key": "test_key5", "value": "test_value5"}
    assert node2.r.get("test_key5") == b"test_value5"
    # Test exception on blocking route
    with pytest.raises(Exception) as e:
        node2.send_blocking("t2ex", {"key": "test_key6", "value": "test_value6"})
    assert str(e.value) == "test_exception"
    assert node1.r.get("test_key6") is None

    # Tear down
    node1.stop()
    node2.stop()
