"""
Overview & Usage
----------------
This module implements a component, a component represents and handle a microservice running in its own process.
Components are managed by the manager and are meant to be subclassed. The subclass should override the :meth:`start`
and :meth:`stop` methods and the :attr:`NAME` attribute.

.. code-block:: python

    class TestComponent(Component):
        NAME = "test"

        def __init__(self):
            super().__init__()  # Very important, do not forget this line

            # Do some init stuff here
            self.log("test init")

        def start(self):
            self.log("test start")
            time.sleep(1)

        def stop(self):
            self.log("test stop")
            time.sleep(1)


    test = TestComponent()
    test.start()
    time.sleep(2)
    test.stop()

    # Output without debug:
    # [15-10-2023 12:35:56] INFO@test: test start
    # [15-10-2023 12:35:59] INFO@test: test stop
"""
import dataclasses
import time

import utilities.ipc as ipc


@dataclasses.dataclass
class State:
    """
    Enumerations of all possible states of a component.
    """
    #: The component is starting up.
    STARTING = "starting"
    #: The component is running.
    STARTED = "started"
    #: The component is shutting down.
    STOPPING = "stopping"
    #: The component is not running.
    STOPPED = "stopped"


class Component(ipc.IpcNode):
    """
    Represent a component. Components are managed by the manager and represents a single process.

    .. note::
        Components are not meant to be used directly, but rather to be subclassed. The subclass should override the
        :meth:`start` and :meth:`stop` methods and the :attr:`NAME` attribute.
    """
    NAME = "component"

    def __init__(self):
        """
        Create a new component. The component will be in the :attr:`State.STOPPED` state.
        """
        super().__init__(ipc_id=self.__class__.NAME)
        #: The current state of the component, picked from the :class:`State <State>` class.
        self.state = State.STOPPED

        # Override start & stop methods
        self.start = self._start_method(self.start)
        self.stop = self._stop_method(self.stop)

    def _start_method(self, func):

        def wrapper():
            if self._set_starting():
                r = func()
                if not self._set_started():
                    raise RuntimeError("Component failed to start.")
                return r
            else:
                raise RuntimeError("Component is not stopped.")

        return wrapper

    def _stop_method(self, func):

        def wrapper():
            if self._set_stopping():
                r = func()
                if not self._set_stopped():
                    raise RuntimeError("Component failed to stop.")
                return r
            else:
                raise RuntimeError("Component is not started.")

        return wrapper

    def _set_starting(self) -> bool:
        """
        Low level method to set the component starting. Should be called by the :meth:`start` method when overriding.

        :return: True if the component started successfully, False otherwise.
        """
        if self.state != State.STOPPED:
            return False
        super().start()
        self.state = State.STARTING
        self.send(f"status.{self.__class__.NAME}.starting", {"component": self.__class__.NAME})
        self.log(f"component starting", ipc.LogLevels.DEBUG, "status")
        return True

    def _set_started(self) -> bool:
        """
        Low level method to set the component started. Should be called by the :meth:`start` method when overriding.
        """
        if self.state != State.STARTING:
            return False
        self.state = State.STARTED
        self.send(f"status.{self.__class__.NAME}.started", {"component": self.__class__.NAME})
        self.log(f"component started", ipc.LogLevels.DEBUG, "status")
        return True

    def _set_stopping(self) -> bool:
        """
        Low level method to set the component stopping. Should be called by the :meth:`stop` method when overriding.
        """
        if self.state != State.STARTED:
            return False
        self.state = State.STOPPING
        self.send(f"status.{self.__class__.NAME}.stopping", {"component": self.__class__.NAME})
        self.log(f"component stopping", ipc.LogLevels.DEBUG, "status")
        return True

    def _set_stopped(self) -> bool:
        """
        Low level method to set the component stopped. Should be called by the :meth:`stop` method when overriding.
        """
        if self.state != State.STOPPING:
            return False
        self.state = State.STOPPED
        self.send(f"status.{self.__class__.NAME}.stopped", {"component": self.__class__.NAME})
        self.log(f"component stopped", ipc.LogLevels.DEBUG, "status")
        super().stop()
        return True

    def start(self):
        """
        Start the component. Should be overridden by the component.

        .. danger::
            This method should never send ipc messages to itself using the loopback parameter as this will cause a
            deadlock.
        """
        pass

    def stop(self):
        """
        Stop the component. Should be overridden by the component.

        .. danger::
            This method should never send ipc messages to itself using the loopback parameter as this will cause a
            deadlock.
        """
        pass

    # We reimplement this method, ignore the signature warning
    # noinspection PyMethodOverriding
    def log(self, message: str, level: str = ipc.LogLevels.INFO, extra_route: str = None):
        """
        Log a message to stdout and to ipc system as "log.{level}.{component_name}" route.

        :param str message: The message to log.
        :param str level: The log level, pick it from :meth:`LogLevels <ipc.LogLevels>`, defaults to LogLevels.INFO.
        :param str extra_route: An additional extra route that will be appended to the route, for example, if I give
            `a.b.c` as extra route, the message will be sent to `log.{level}.{label}.a.b.c` route, defaults to "" (resulting in
            `log.{level}.{component_name}` route).
        """
        super().log(message, level, self.__class__.NAME, extra_route)


if __name__ == "__main__":
    class TestComponent(Component):
        NAME = "test"

        def __init__(self):
            super().__init__()  # Very important, do not forget this line

            # Do some init stuff here
            self.log("test init")

        def start(self):
            self.log("test start")
            time.sleep(1)

        def stop(self):
            self.log("test stop")
            time.sleep(1)


    test = TestComponent()
    test.start()
    time.sleep(2)
    test.stop()

    # Output without debug:
    # [15-10-2023 12:35:56] INFO@test: test start
    # [15-10-2023 12:35:59] INFO@test: test stop

