import multiprocessing
import threading
import time
import typing
import unittest.mock

import pytest
from unittest.mock import Mock

import redis
from src import manager as manager_module
from utilities import component as component_module, logger, ipc, component


def test_manager_init():
    mock_ipc_node = Mock()
    manager = manager_module.Manager(mock_ipc_node)

    assert manager._ipc_node == mock_ipc_node
    mock_ipc_node.bind_routes.assert_called_once_with(manager)
    mock_ipc_node.start.assert_called_once()

    for comp in manager_module.components:
        assert comp in manager._components
        assert "process" in manager._components[comp] and manager._components[comp]["process"] is None
        assert "lock" in manager._components[comp]
        assert "timeout_lock" in manager._components[comp]
        manager._components[comp]["lock"].acquire()
        manager._components[comp]["lock"].release()
        manager._components[comp]["timeout_lock"].acquire()
        manager._components[comp]["timeout_lock"].release()


def test_manager_check_state():
    mock_ipc_node = Mock()
    mock_ipc_node.redis = Mock()
    manager = manager_module.Manager(mock_ipc_node)

    with unittest.mock.patch.object(component_module.Component, "get_state") as mock_get_state:
        mock_get_state.return_value = component_module.ComponentState.STOPPED
        assert manager._check_state("hello", component_module.ComponentState.STOPPED)
        mock_get_state.assert_called_once_with(mock_ipc_node.redis, "hello")
        assert not manager._check_state("hello", component_module.ComponentState.STARTED)


def test_manager_integration():
    # Components
    class BasicComponent(component.Component):
        NAME = "basic"

        def start(self):
            pass

        def stop(self):
            pass

    class AlsoBasicComponent(component.Component):
        NAME = "also_basic"

        def start(self):
            pass

        def stop(self):
            pass

    class NeverStartComponent(component.Component):
        NAME = "never_start"

        def start(self):
            time.sleep(1000)
            pass

        def stop(self):
            pass

    class NeverStopComponent(component.Component):
        NAME = "never_stop"

        def start(self):
            pass

        def stop(self):
            time.sleep(1000)
            pass

    manager_module.components = {
        "basic": BasicComponent,
        "also_basic": AlsoBasicComponent,
        "never_start": NeverStartComponent,
        "never_stop": NeverStopComponent,
    }

    # Init
    r = redis.StrictRedis(host="redis", port=6379, db=0)
    _ipc_node = ipc.IpcNode(
        "manager",
        r,
        r.pubsub()
    )
    _ipc_node.set_logger(logger.Logger(_ipc_node))
    manager = manager_module.Manager(_ipc_node)

    # Start single component
    _ipc_node.send_blocking("state:start:basic", {"component": "basic"}, loopback=True)
    assert manager._components["basic"]["process"] is not None
    assert manager._components["basic"]["process"].is_alive()
    assert component_module.Component.get_state(r, "basic") == component_module.ComponentState.STARTED

    # Stop single component
    _ipc_node.send_blocking("state:stop:basic", {"component": "basic"}, loopback=True)
    assert component_module.Component.get_state(r, "basic") == component_module.ComponentState.STOPPED

    # Start all components
    _ipc_node.send_blocking("state:start_all", {}, loopback=True, timeout=10)
    assert manager._components["basic"]["process"] is not None
    assert manager._components["basic"]["process"].is_alive()
    assert component_module.Component.get_state(r, "basic") == component_module.ComponentState.STARTED
    assert manager._components["also_basic"]["process"] is not None
    assert manager._components["also_basic"]["process"].is_alive()
    assert component_module.Component.get_state(r, "also_basic") == component_module.ComponentState.STARTED
    assert manager._components["never_start"]["process"] is not None
    assert component_module.Component.get_state(r, "never_start") == component_module.ComponentState.STOPPED
    assert manager._components["never_stop"]["process"] is not None
    assert manager._components["never_stop"]["process"].is_alive()
    assert component_module.Component.get_state(r, "never_stop") == component_module.ComponentState.STARTED

    # Restart all components
    _ipc_node.send_blocking("state:restart_all", {}, loopback=True, timeout=10)
    assert manager._components["basic"]["process"] is not None
    assert manager._components["basic"]["process"].is_alive()
    assert component_module.Component.get_state(r, "basic") == component_module.ComponentState.STARTED
    assert manager._components["also_basic"]["process"] is not None
    assert manager._components["also_basic"]["process"].is_alive()
    assert component_module.Component.get_state(r, "also_basic") == component_module.ComponentState.STARTED
    assert manager._components["never_start"]["process"] is not None
    assert component_module.Component.get_state(r, "never_start") == component_module.ComponentState.STOPPED
    assert manager._components["never_stop"]["process"] is not None
    assert manager._components["never_stop"]["process"].is_alive()
    assert component_module.Component.get_state(r, "never_stop") == component_module.ComponentState.STARTED

    # Stop all components
    _ipc_node.send_blocking("state:stop_all", {}, loopback=True, timeout=10)
    assert component_module.Component.get_state(r, "basic") == component_module.ComponentState.STOPPED
    assert component_module.Component.get_state(r, "also_basic") == component_module.ComponentState.STOPPED
    assert component_module.Component.get_state(r, "never_start") == component_module.ComponentState.STOPPED
    assert component_module.Component.get_state(r, "never_stop") == component_module.ComponentState.STOPPED

    manager.stop()
