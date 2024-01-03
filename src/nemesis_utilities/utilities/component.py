import time
import traceback

import redis
from utilities import ipc, logger


class ComponentState:
    STOPPED = "stopped"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"


class Component:
    NAME = None

    @staticmethod
    def get_state(_redis: redis.Redis, component: str) -> str:
        """
        Get the current state of the component
        :param _redis: The redis instance to use
        :param component: The component to get the state of
        """
        return _redis.get(f"state:{component}").decode()

    @staticmethod
    def init_state(_redis: redis.Redis, component: str):
        """
        Initialize the state of the component
        :param _redis: The redis instance to use
        :param component: The component to initialize the state of
        """
        _redis.set(f"state:{component}", ComponentState.STOPPED)

    def __init__(self, ipc_node: ipc.IpcNode):
        assert self.__class__.NAME is not None

        self._state = ComponentState.STOPPED

        self._ipc_node = ipc_node

        # Stop route
        self._stop_component = ipc.Route([f"state:{self.NAME}:stop"], False).decorator(Component._stop_component)

        self._ipc_node.bind_routes(self)
        self._ipc_node.start()

    @property
    def logger(self) -> logger.Logger:
        return self._ipc_node.logger

    @property
    def redis(self) -> redis.Redis:
        return self._ipc_node.redis

    @property
    def ipc_node(self) -> ipc.IpcNode:
        return self._ipc_node

    def _update_state(self, state: str, from_state: str):
        assert self._state == from_state
        self._state = state

        self._ipc_node.redis.set(f"state:{self.NAME}", state)
        self._ipc_node.send(f"state:{self.NAME}:{state}", {"component": self.NAME})
        self._ipc_node.logger.info(f"component is {state}", self.NAME, "state")

    def _set_starting(self):
        self._update_state(ComponentState.STARTING, ComponentState.STOPPED)

    def _set_started(self):
        self._update_state(ComponentState.STARTED, ComponentState.STARTING)

    def _set_stopping(self):
        self._update_state(ComponentState.STOPPING, ComponentState.STARTED)

    def _set_stopped(self):
        self._update_state(ComponentState.STOPPED, ComponentState.STOPPING)
        self._ipc_node.stop()

    def start_component(self):
        self._set_starting()
        self.start()
        self._set_started()

    def _stop_component(self, call_data, payload):
        self._set_stopping()
        self.stop()
        self._set_stopped()

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()


def run_component(component_type: Component):
    strict_redis = redis.StrictRedis("redis")
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
