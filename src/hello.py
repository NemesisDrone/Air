import threading

from utilities import component, ipc
import time


class HelloComponent(component.Component):
    NAME = "hello"

    def __init__(self, ipc_node: ipc.IpcNode):
        """
        :param ipc_node: The IPCNode.
        """
        super().__init__(ipc_node)

        self._alive = False
        self._thread = None
        self.logger.info("Hello component initialized", self.NAME)

    def _job(self):
        i = 0
        while self._alive:
            self.logger.info(f"Hello component saying hello for the {i}th time", self.NAME)
            i += 1
            time.sleep(2)

    def start(self):
        self._alive = True
        self._thread = threading.Thread(target=self._job)
        self._thread.start()

    def stop(self):
        self._alive = False
        self._thread.join()
