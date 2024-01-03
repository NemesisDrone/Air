import multiprocessing
import os
import signal
import threading
import typing

import redis
from utilities import ipc, component as component_module, logger

import hello as hello
import sim7600.sim7600 as sim7600
import vl53.vl53 as vl53
import pi_sense_hat.pi_sense_hat as pi_sense_hat

#: The time in seconds to wait for the components to stop before killing them
STOP_TIMOUT = 15

# ----------------------------------------------------------------------------------------------------------------------
#                                             Components Configuration
# ----------------------------------------------------------------------------------------------------------------------
components = {
    # name: class
    # Be careful to *always* use the name that you've used in your Component-inheriting class too!
    #"test": testcomp.TestComponent,
    "hello": hello.HelloComponent,
    "sim7600": sim7600.Sim7600Component,
    "sense_hat": pi_sense_hat.SenseHatComponent,
    "vl53": vl53.Vl53Component,
}

# ----------------------------------------------------------------------------------------------------------------------
#                                              Profiles Configuration
# ----------------------------------------------------------------------------------------------------------------------
profiles = {
    # name: [list of components]
    "default": ["vl53"],
    # "dev": ["test"],
}


class Manager:

    def __init__(self, ipc_node: ipc.IpcNode):
        """d
        :param ipc_node: The IPC node to use
        """
        self._ipc_node = ipc_node
        self._ipc_node.bind_routes(self)
        for c in components:
            component_module.Component.init_state(self._ipc_node.redis, c)

        self._ipc_node.start()

        self._components: (
            typing.Dict)[str, typing.Dict[str, typing.Union[multiprocessing.Process, None, threading.Lock]]] = \
            {c: {"process": None, "lock": threading.Lock(), "timeout_lock": threading.Lock()} for c in components}

    def stop(self):
        """
        Stop the manager
        """
        self._stop_all_components()
        self._ipc_node.stop()

    def _check_state(self, component: str, state: str) -> bool:
        """
        Check the state of a component
        :param component: The component to check
        :param state: The state to check
        :return: True if the component is in the given state, False otherwise
        """
        return component_module.Component.get_state(self._ipc_node.redis, component) == state

    def _timout_state_update(self, component: str):
        """
        Timeout the state update of a component
        """
        r = self._components[component]["timeout_lock"].acquire(timeout=STOP_TIMOUT)
        if r:
            self._components[component]["timeout_lock"].release()
        else:
            state = component_module.Component.get_state(self._ipc_node.redis, component)
            self._ipc_node.logger.error(f"Timout reached for {component} component witch is still {state}, "
                                        f"killing process.", "manager")

            # Timeout reached, kill the process
            self._components[component]["process"].kill()

            # Force his state
            self._ipc_node.redis.set(f"state:{component}", component_module.ComponentState.STOPPED)
            self._ipc_node.send(f"state:{component}:{component_module.ComponentState.STOPPED}",
                                {"component": component}, loopback=True)
            self._ipc_node.logger.info(f"component is {component_module.ComponentState.STOPPED}", component,
                                       "state")

    def _start_component(self, component: str):
        """
        Start a component
        :param component: The component to start
        """
        self._components[component]["lock"].acquire()
        if not self._check_state(component, component_module.ComponentState.STOPPED):
            self._components[component]["lock"].release()
            return

        assert self._components[component]["timeout_lock"].acquire(timeout=1)

        self._components[component]["process"] = multiprocessing.Process(target=component_module.run_component,
                                                                         args=(components[component],))
        self._components[component]["process"].start()

        self._timout_state_update(component)

    def _stop_component(self, component: str):
        """
        Stop a component
        :param component: The component to stop
        """
        self._components[component]["lock"].acquire()
        if not self._check_state(component, component_module.ComponentState.STARTED):
            self._components[component]["lock"].release()
            return

        assert self._components[component]["timeout_lock"].acquire(timeout=1)

        self._ipc_node.send(f"state:{component}:stop", {"component": component})

        self._timout_state_update(component)

    def _restart_component(self, component: str):
        """
        Restart a component
        :param component: The component to restart
        """
        self._stop_component(component)
        self._start_component(component)

    def _stop_all_components(self):
        """
        Stop all components
        """
        threads = []
        for c in self._components:
            t = threading.Thread(target=self._stop_component, args=(c,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    def _start_all_components(self):
        """
        Start all components
        """
        threads = []
        for c in self._components:
            t = threading.Thread(target=self._start_component, args=(c,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    def _restart_all_components(self):
        """
        Restart all components
        """
        threads = []
        for c in self._components:
            t = threading.Thread(target=self._restart_component, args=(c,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    # --- Callback ---
    @ipc.Route(["state:*:started", "state:*:stopped"], False).decorator
    def _state_update(self, call_data: ipc.CallData, payload: dict):
        """
        Callback for state updates
        """
        self._components[payload["component"]]["lock"].release()
        self._components[payload["component"]]["timeout_lock"].release()

    # --- IPC Bindings ---
    @ipc.Route(["state:start:*"], True).decorator
    def _start_component_route(self, call_data: ipc.CallData, payload: dict):
        """
        Start a component
        """
        component = payload["component"]
        self._start_component(component)

    @ipc.Route(["state:stop:*"], True).decorator
    def _stop_component_route(self, call_data: ipc.CallData, payload: dict):
        """
        Stop a component
        """
        component = payload["component"]
        self._stop_component(component)

    @ipc.Route(["state:restart:*"], True).decorator
    def _restart_component_route(self, call_data: ipc.CallData, payload: dict):
        """
        Restart a component
        """
        component = payload["component"]
        self._restart_component(component)

    @ipc.Route(["state:start_all"], True).decorator
    def _start_all_components_route(self, call_data: ipc.CallData, payload: dict):
        """
        Start all components
        """
        self._start_all_components()

    @ipc.Route(["state:stop_all"], True).decorator
    def _stop_all_components_route(self, call_data: ipc.CallData, payload: dict):
        """
        Stop all components
        """
        self._stop_all_components()

    @ipc.Route(["state:restart_all"], True).decorator
    def _restart_all_components_route(self, call_data: ipc.CallData, payload: dict):
        """
        Restart all components
        """
        self._restart_all_components()


if __name__ == "__main__":
    r = redis.StrictRedis(host="redis", port=6379, db=0)
    _ipc_node = ipc.IpcNode(
        "manager",
        r,
        r.pubsub()
    )
    _ipc_node.set_logger(logger.Logger(_ipc_node))
    manager = Manager(_ipc_node)

    init_profile = (
        "default"
        if (
                os.environ.get("NEMESIS_PROFILE") == ""
                or os.environ.get("NEMESIS_PROFILE") is None
        )
        else os.environ.get("NEMESIS_PROFILE")
    )
    for c in profiles[init_profile]:
        manager._start_component(c)

    class ManagerKiller:
        def __init__(self, manager):
            self.manager = manager
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)

        def stop(self, sig, frame):
            self.manager.stop()

    ManagerKiller(manager)
