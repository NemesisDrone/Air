import json
import threading
from .rc_ibus import RcIbus

from utilities import component, ipc


class RcComponent(component.Component):
    NAME = "rc"

    def __init__(self, ipc_node: ipc.IpcNode) -> None:
        super().__init__(ipc_node)

        #: Is the rc alive
        self._worker_alive = False
        #: The rc thread
        self._worker_thread = threading.Thread(target=self._rc_worker, daemon=True)

        try:
            self._ibus = RcIbus("/dev/serial0")
            self._worker_alive = True
        except Exception:
            self.logger.warning(f"Could not initialize radio command")

        self._update_custom_status()

    def _update_custom_status(self) -> None:
        """
        Update the custom status to rc:status
        """
        self.redis.set(
            "rc:status",
            json.dumps({"rc_worker_alive": self._worker_alive}),
        )
        self.ipc_node.send("rc:status", {"rc_worker_alive": self._worker_alive})

    @staticmethod
    def _normalize_rc_channel(value: int) -> float:
        """
        Normalize the rc channel value (1000-2000) to a float between 0 and 100
        """
        return (value - 1000) / 10

    def _rc_worker(self) -> None:
        """
        The rc worker
        """
        # Clear eventual previous data
        self.redis.set("rc:data", "")
        self._update_custom_status()

        try:
            while self._worker_alive:
                data = self._ibus.read()
                if len(data) > 0:
                    print(str(data), flush=True)

        except Exception as e:
            self.logger.error(f"Rc worker stopped unexpectedly: {e}", self.NAME)
            self._worker_alive = False

        self._update_custom_status()

    def start(self) -> None:
        self._worker_alive = True
        self._worker_thread.start()

    def stop(self) -> None:
        self._worker_alive = False
        self._worker_thread.join()
