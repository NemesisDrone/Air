import os
import multiprocessing
import threading
import time
import signal

from utilities import ipc
from utilities.component import State as State

# --- Components Imports ---
# import ...
import hello
import sensors.sensors as sensors

# --------------------------

#: The time in seconds to wait for the components to stop before killing them
STOP_TIMOUT = 5

# ----------------------------------------------------------------------------------------------------------------------
#                                             Components Configuration
# ----------------------------------------------------------------------------------------------------------------------
components = {
    # name: function_to_call
    "hello": hello.run,
    "sensors": sensors.run
}

# ----------------------------------------------------------------------------------------------------------------------
#                                              Profiles Configuration
# ----------------------------------------------------------------------------------------------------------------------
profiles = {
    # name: [list of components]
    "default": ["hello", "sensors"]
}


class Manager(ipc.IpcNode):

    def __init__(self):
        super().__init__(ipc_id="manager")

        # First profile to load, caught from the "NEMESIS_PROFILE" environment variable, defaults to "default"
        self.init_profile = "default" if (os.environ.get("NEMESIS_PROFILE") == "" or
                                          os.environ.get("NEMESIS_PROFILE") is None) \
            else os.environ.get("NEMESIS_PROFILE")

        #: A :class:`dict` mapping a component name to a list of :class:`multiprocessing.Process` instance, a lock and
        # a restart flag
        self.components = {}
        for k in components:
            self.components[k] = [None, threading.Lock(), False]
            self.r.set(f"state:{k}:state", State.STOPPED)

    def start(self):
        super().start()
        self.log(f"Starting profile {self.init_profile}", ipc.LogLevels.INFO)

        for component in profiles[self.init_profile]:
            self.send(f"state:start:{component}", {"component": component}, loopback=True)

        self.log("profile started", ipc.LogLevels.DEBUG)

    def stop(self):
        self.log("Stopping manager and all components", ipc.LogLevels.INFO)

        self.send_blocking("state:stop_all", {}, loopback=True)
        for component in self.components:
            while self.r.get(f"state:{component}:state").decode() != State.STOPPED:
                time.sleep(0.1)

        self.log("manager stopped", ipc.LogLevels.DEBUG)
        super().stop()

    def _timeout(self, component: str):
        """
        Called to timeout when a component does not stop in time
        """
        now = time.time()
        while self.r.get(f"state:{component}:state").decode() != State.STOPPED and time.time() - now < STOP_TIMOUT:
            time.sleep(0.1)

        if self.r.get(f"state:{component}:state").decode() != State.STOPPED:
            self.log(f"component {component} did not stop in time, killing it", ipc.LogLevels.WARNING)
            if self.r.get(f"state:{component}:state").decode() == State.STARTED:
                self.send(f"state:{component}:stopping", {"component": component}, loopback=True)
            self.components[component][0].terminate()
            self.components[component][0].join()
            self.send(f"state:{component}:stopped", {"component": component}, loopback=True)

    # ------------------------------------------------------------------------------------------------------------------
    #                                                 Set state
    # ------------------------------------------------------------------------------------------------------------------
    @ipc.route("state:start:*", thread=True, blocking=True)
    def _start(self, data):
        self.components[data["component"]][1].acquire()
        if self.r.get(f"state:{data['component']}:state").decode() == State.STOPPED:
            self.components[data["component"]][0] = multiprocessing.Process(target=components[data["component"]])
            self.components[data["component"]][0].start()

        self.components[data["component"]][1].release()

    @ipc.route("state:stop:*", thread=False, blocking=True)
    def _stop(self, data):
        self.components[data["component"]][1].acquire()

        if self.r.get(f"state:{data['component']}:state").decode() == State.STARTED:
            self.send(f"state:{data['component']}:stop", {"component": data["component"]})
            threading.Thread(target=self._timeout, args=(data["component"],)).start()

        self.components[data["component"]][1].release()

    @ipc.route("state:restart:*", thread=True, blocking=True)
    def _restart(self, data):
        self.components[data["component"]][1].acquire()

        if self.r.get(f"state:{data['component']}:state").decode() == State.STARTED:
            self.send(f"state:{data['component']}:stop", {"component": data["component"]})
            threading.Thread(target=self._timeout, args=(data["component"],)).start()

            self.components[data["component"]][1].release()

        while self.r.get(f"state:{data['component']}:state").decode() != State.STOPPED:
            time.sleep(0.001)

        self.components[data["component"]][1].acquire()

        self.send(f"state:start:{data['component']}", {"component": data["component"]}, loopback=True)

        self.components[data["component"]][1].release()

    @ipc.route("state:stop_all", thread=True, blocking=True)
    def _stop_all(self, data):
        for component in self.components:
            self.components[component][1].acquire()
            if self.r.get(f"state:{component}:state").decode() == State.STARTED:
                self.send(f"state:stop:{component}", {"component": component}, loopback=True)
                threading.Thread(target=self._timeout, args=(component,)).start()
            self.components[component][1].release()

    @ipc.route("state:restart_all", thread=True, blocking=True)
    def _restart_all(self, data):
        for component in self.components:
            self.components[component][1].acquire()
            if self.r.get(f"state:{component}:state").decode() == State.STARTED:
                self.send(f"state:restart:{component}", {"component": component}, loopback=True)
            self.components[component][1].release()


    # ------------------------------------------------------------------------------------------------------------------
    #                                                Update State
    # ------------------------------------------------------------------------------------------------------------------
    @ipc.route("state:*:starting", thread=True, blocking=True)
    def _on_starting(self, data):
        self.components[data["component"]][1].acquire()

        if self.r.get(f"state:{data['component']}:state").decode() != State.STOPPED:
            self.log(f"inconsistency detected, this should never happen, component {data['component']} "
                     f"is starting but it is not stopped", ipc.LogLevels.CRITICAL)
        self.r.set(f"state:{data['component']}:state", State.STARTING)
        self.log(f"component {data['component']} set to starting", ipc.LogLevels.DEBUG)

        self.components[data["component"]][1].release()

    @ipc.route("state:*:started", thread=True, blocking=True)
    def _on_started(self, data):
        self.components[data["component"]][1].acquire()

        if self.r.get(f"state:{data['component']}:state").decode() != State.STARTING:
            self.log(f"inconsistency detected, this should never happen, component {data['component']} "
                     f"is started but it is not starting", ipc.LogLevels.CRITICAL)
        self.r.set(f"state:{data['component']}:state", State.STARTED)
        self.log(f"component {data['component']} set to started", ipc.LogLevels.DEBUG)

        self.components[data["component"]][1].release()

    @ipc.route("state:*:stopping", thread=True, blocking=True)
    def _on_stopping(self, data):
        self.components[data["component"]][1].acquire()

        if self.r.get(f"state:{data['component']}:state").decode() != State.STARTED:
            self.log(f"inconsistency detected, this should never happen, component {data['component']} "
                     f"is stopping but it is not started", ipc.LogLevels.CRITICAL)
        self.r.set(f"state:{data['component']}:state", State.STOPPING)
        self.log(f"component {data['component']} set to stopping", ipc.LogLevels.DEBUG)

        self.components[data["component"]][1].release()

    @ipc.route("state:*:stopped", thread=True, blocking=True)
    def _on_stopped(self, data):
        self.components[data["component"]][1].acquire()

        if self.r.get(f"state:{data['component']}:state").decode() != State.STOPPING:
            self.log(f"inconsistency detected, this should never happen, component {data['component']} "
                     f"is stopped but it is not stopping", ipc.LogLevels.CRITICAL)
        self.r.set(f"state:{data['component']}:state", State.STOPPED)
        self.log(f"component {data['component']} set to stopped", ipc.LogLevels.DEBUG)

        self.components[data["component"]][1].release()


if __name__ == "__main__":
    class ManagerKiller:
        def __init__(self, manager):
            self.manager = manager
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)

        def stop(self, sig, frame):
            self.manager.stop()

    _manager = Manager()
    _manager.start()
    ManagerKiller(_manager)
