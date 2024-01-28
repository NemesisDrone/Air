import os
import threading
import unittest.mock
from unittest.mock import Mock

import pytest
import redis
from utilities import component as component_module
from utilities import ipc, logger


# --- Component States ---
def test_component_states():
    assert component_module.ComponentState.STOPPED == "stopped"
    assert component_module.ComponentState.STARTING == "starting"
    assert component_module.ComponentState.STARTED == "started"
    assert component_module.ComponentState.STOPPING == "stopping"


# --- Component ---
def test_component_init_no_name():
    mock_ipc_node = Mock()

    with pytest.raises(AssertionError):
        component_module.Component(mock_ipc_node)


@pytest.fixture
def named_component():
    class NamedComponent(component_module.Component):
        NAME = "component"

    return NamedComponent


def test_component_init(named_component):
    mock_ipc_node = Mock()
    mock_logger = Mock()
    mock_ipc_node.logger = mock_logger
    mock_redis = Mock()
    mock_ipc_node.redis = mock_redis

    component = named_component(mock_ipc_node)

    assert component._state == component_module.ComponentState.STOPPED
    assert component._ipc_node == mock_ipc_node
    mock_ipc_node.bind_routes.assert_called_once_with(component)
    mock_ipc_node.start.assert_called_once()

    assert component.ipc_node == mock_ipc_node
    assert component.redis == mock_redis
    assert component.logger == mock_logger


def test_component_get_state(named_component):
    mock_ipc_node = Mock()
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=component_module.ComponentState.STOPPED.encode())

    component = named_component(mock_ipc_node)

    assert component.get_state(mock_redis, component.NAME) == component_module.ComponentState.STOPPED
    mock_redis.get.assert_called_once_with(f"state:component")


# -- State update --
def test_component_update_state(named_component):
    mock_ipc_node = Mock()
    mock_redis = Mock()
    mock_ipc_node.redis = mock_redis
    mock_logger = Mock()
    mock_ipc_node.logger = mock_logger

    component = named_component(mock_ipc_node)
    component._state = component_module.ComponentState.STOPPED

    for state in [
        {"to": component_module.ComponentState.STARTING, "from": component_module.ComponentState.STOPPED},
        {"to": component_module.ComponentState.STARTED, "from": component_module.ComponentState.STARTING},
        {"to": component_module.ComponentState.STOPPING, "from": component_module.ComponentState.STARTED},
        {"to": component_module.ComponentState.STOPPED, "from": component_module.ComponentState.STOPPING},
    ]:
        component._update_state(state["to"], state["from"])

        assert component._state == state["to"]
        mock_ipc_node.send.assert_called_once_with(f"state:component:{state['to']}", {"component": "component"})
        mock_ipc_node.redis.set.assert_called_once_with("state:component", state["to"])
        mock_ipc_node.logger.info.assert_called_once_with(f"component is {state['to']}", "component", "state")
        mock_ipc_node.logger.reset_mock()
        mock_ipc_node.redis.reset_mock()
        mock_ipc_node.send.reset_mock()


def test_component_update_state_wrong_state(named_component):
    mock_ipc_node = Mock()
    component = named_component(mock_ipc_node)
    component._state = component_module.ComponentState.STOPPED

    for state in [
        {"to": component_module.ComponentState.STARTING, "from": component_module.ComponentState.STOPPED},
        {"to": component_module.ComponentState.STARTED, "from": component_module.ComponentState.STARTING},
        {"to": component_module.ComponentState.STOPPING, "from": component_module.ComponentState.STARTED},
        {"to": component_module.ComponentState.STOPPED, "from": component_module.ComponentState.STOPPING},
    ]:
        wrong_states = [
            component_module.ComponentState.STOPPED,
            component_module.ComponentState.STARTING,
            component_module.ComponentState.STARTED,
            component_module.ComponentState.STOPPING,
        ]
        wrong_states.remove(state["from"])

        for wrong_state in wrong_states:
            component._state = wrong_state
            with pytest.raises(AssertionError):
                component._update_state(state["to"], state["from"])
            assert component._state == wrong_state


def test_component_set_starting(named_component):
    mock_ipc_node = Mock()

    component = named_component(mock_ipc_node)
    component._state = component_module.ComponentState.STOPPED

    with unittest.mock.patch.object(component, "_update_state") as mock_update_state:
        component._set_starting()

        mock_update_state.assert_called_once_with(
            component_module.ComponentState.STARTING, component_module.ComponentState.STOPPED
        )


def test_component_set_started(named_component):
    mock_ipc_node = Mock()
    component = named_component(mock_ipc_node)
    component._state = component_module.ComponentState.STARTING

    with unittest.mock.patch.object(component, "_update_state") as mock_update_state:
        component._set_started()

        mock_update_state.assert_called_once_with(
            component_module.ComponentState.STARTED, component_module.ComponentState.STARTING
        )


def test_component_set_stopping(named_component):
    mock_ipc_node = Mock()
    component = named_component(mock_ipc_node)
    component._state = component_module.ComponentState.STARTED

    with unittest.mock.patch.object(component, "_update_state") as mock_update_state:
        component._set_stopping()

        mock_update_state.assert_called_once_with(
            component_module.ComponentState.STOPPING, component_module.ComponentState.STARTED
        )


def test_component_set_stopped(named_component):
    mock_ipc_node = Mock()
    component = named_component(mock_ipc_node)
    component._state = component_module.ComponentState.STOPPING

    with unittest.mock.patch.object(component, "_update_state") as mock_update_state:
        component._set_stopped()

        mock_update_state.assert_called_once_with(
            component_module.ComponentState.STOPPED, component_module.ComponentState.STOPPING
        )
        mock_ipc_node.stop.assert_called_once()


def test_component_has_stop_and_start(named_component):
    mock_ipc_node = Mock()
    component = named_component(mock_ipc_node)

    assert hasattr(component, "start")
    assert hasattr(component, "stop")

    with pytest.raises(NotImplementedError):
        component.start()

    with pytest.raises(NotImplementedError):
        component.stop()


def test_start_and_stop_component(named_component):
    mock_ipc_node = Mock()
    component = named_component(mock_ipc_node)

    with unittest.mock.patch.object(component, "_set_starting") as mock_set_starting:
        with unittest.mock.patch.object(component, "_set_started") as mock_set_started:
            with unittest.mock.patch.object(component, "_set_stopping") as mock_set_stopping:
                with unittest.mock.patch.object(component, "_set_stopped") as mock_set_stopped:
                    with unittest.mock.patch.object(component, "start") as mock_start:
                        with unittest.mock.patch.object(component, "stop") as mock_stop:
                            component.start_component()

                            mock_set_starting.assert_called_once()
                            mock_start.assert_called_once()
                            mock_set_started.assert_called_once()

                            with pytest.raises(RuntimeError):
                                component._stop_component(component, None, None)


# --- Integration ---
def test_component_integration():
    class TestComponent(component_module.Component):
        NAME = "component"

        def __init__(self, ipc_node: ipc.IpcNode):
            super().__init__(ipc_node)

            self._alive = False
            self._flag = False

        def _run(self):
            self._flag = True

            while self._alive:
                pass

            self._flag = True

        def start(self):
            self._alive = True
            threading.Thread(target=self._run).start()

        def stop(self):
            self._alive = False

    r = redis.StrictRedis(host=os.environ.get("REDIS_HOST"), port=os.environ.get("REDIS_PORT"), db=0)
    node = ipc.IpcNode("node", r, r.pubsub())
    node.set_logger(logger.Logger(node))

    component = TestComponent(node)
    component.start_component()
    while not component._flag:
        pass
    component._flag = False
    node.send("state:component:stop", {"component": "component"}, loopback=True)
    while not component._flag:
        pass
