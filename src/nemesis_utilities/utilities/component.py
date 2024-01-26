"""Abstraction to create reusable microservices as components managed by the manager

:class:`ComponentState` enum of possible component states

:class:`Component` base class for components

:meth:`run_component` called by the manager to run a component
"""

import traceback
import os
import redis
from utilities import ipc, logger


class ComponentState:
    """Enum of possible component states

    :cvar STOPPED: The component is stopped
    :cvar STARTING: The component is starting
    :cvar STARTED: The component is started
    :cvar STOPPING: The component is stopping
    """

    STOPPED = "stopped"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"


class Component:
    """Base class for components

    :cvar NAME: The name of the component, cannot be None, defaults to None

    :attr:`logger` the logger instance
    :attr:`redis` the redis instance
    :attr:`ipc_node` the ipc node instance

    :meth:`get_state` get the current redis state of a component
    :meth:`init_state` set the redis state of a component to stopped
    :meth:`start_component` start the component
    :meth:`start` do some stuff when starting the component
    :meth:`stop` do some stuff when stopping the component
    """

    NAME = None

    @staticmethod
    def get_state(_redis: redis.Redis, component: str) -> str:
        """Get the current redis state of a component

        :param _redis: The redis instance to use
        :param component: The component name to get the state of

        :return: The state of the component, one of :class:`ComponentState`
        """
        return _redis.get(f"state:{component}").decode()

    @staticmethod
    def init_state(_redis: redis.Redis, component: str) -> None:
        """Set the redis state of a component to stopped

        :param _redis: The redis instance to use
        :param component: The component name to set the state of
        """
        _redis.set(f"state:{component}", ComponentState.STOPPED)

    def __init__(self, ipc_node: ipc.IpcNode):
        """Initialize the component
        Do some initialization stuff, starting stuff is done in :meth:`start`.

        :param ipc_node: The ipc node instance to use
        """
        assert self.__class__.NAME is not None

        #: The current state of the component, one of :class:`ComponentState`
        self._state = ComponentState.STOPPED

        #: The ipc node instance to use
        self._ipc_node = ipc_node

        #: The ipc route to stop the component
        self._stop_component = ipc.Route([f"state:{self.NAME}:stop"], False).decorator(Component._stop_component)

        # Route binding and ipc node start
        self._ipc_node.bind_routes(self)
        self._ipc_node.start()

    @property
    def logger(self) -> logger.Logger:
        """The logger instance"""
        return self._ipc_node.logger

    @property
    def redis(self) -> redis.Redis:
        """The redis instance"""
        return self._ipc_node.redis

    @property
    def ipc_node(self) -> ipc.IpcNode:
        """The ipc node instance"""
        return self._ipc_node

    def _update_state(self, state: str, from_state: str) -> None:
        """Update the state of the component

        :param state: The new state of the component, one of :class:`ComponentState`
        :param from_state: The state the component must be in to update the state, one of :class:`ComponentState`
        """
        # Check current state is correct
        assert self._state == from_state

        # Local update
        self._state = state

        # Redis update
        self._ipc_node.redis.set(f"state:{self.NAME}", state)
        self._ipc_node.send(f"state:{self.NAME}:{state}", {"component": self.NAME})
        self._ipc_node.logger.info(f"component is {state}", self.NAME, "state")

    def _set_starting(self) -> None:
        """Set the component state to starting"""
        self._update_state(ComponentState.STARTING, ComponentState.STOPPED)

    def _set_started(self) -> None:
        """Set the component state to started"""
        self._update_state(ComponentState.STARTED, ComponentState.STARTING)

    def _set_stopping(self) -> None:
        """Set the component state to stopping"""
        self._update_state(ComponentState.STOPPING, ComponentState.STARTED)

    def _set_stopped(self) -> None:
        """Set the component state to stopped"""
        self._update_state(ComponentState.STOPPED, ComponentState.STOPPING)
        self._ipc_node.stop()

    def start_component(self) -> None:
        """Start the component"""
        self._set_starting()
        self.start()
        self._set_started()

    def _stop_component(self, call_data, payload) -> None:
        """Stop the component

        :param call_data: The call data of the call
        :param payload: The payload of the call
        """
        self._set_stopping()
        self.stop()
        self._set_stopped()

    def start(self) -> None:
        """Do some stuff when starting the component"""
        raise NotImplementedError()

    def stop(self) -> None:
        """Do some stuff when stopping the component"""
        raise NotImplementedError()


def run_component(component_type: Component) -> None:
    """Run a component

    :param component_type: The component class to run
    """
    # Ipc node setup
    strict_redis = redis.StrictRedis(os.environ.get("REDIS_HOST"))
    ipc_node = ipc.IpcNode(
        ipc_id=component_type.NAME,
        strict_redis=strict_redis,
        pubsub=strict_redis.pubsub(),
    )
    ipc_node.set_logger(logger.Logger(ipc_node))

    try:
        comp = component_type(ipc_node)
        comp.start_component()
    except Exception as e:
        ipc_node.logger.error(f"Could not start component: {e}\n{traceback.format_exc()}", component_type.NAME)
        ipc_node.stop()
        return
