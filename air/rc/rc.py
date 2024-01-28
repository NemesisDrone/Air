import json
import threading
from typing import Tuple

from air.utilities import component, ipc

from .rc_ibus import RcIbus


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
            self.logger.warning(f"Could not initialize radio command", self.NAME)

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

    def _update_channels(self, data: Tuple[int]) -> None:
        """
        Update the rc channels to rc:channels redis key
        """
        channels = {
            "ch1": self._normalize_rc_channel(data[2]),
            "ch2": self._normalize_rc_channel(data[3]),
            "ch3": self._normalize_rc_channel(data[4]),
            "ch4": self._normalize_rc_channel(data[5]),
            "ch5": self._normalize_rc_channel(data[6]),
            "ch6": self._normalize_rc_channel(data[7]),
            "ch7": self._normalize_rc_channel(data[8]),
            "ch8": self._normalize_rc_channel(data[9]),
            "ch9": self._normalize_rc_channel(data[10]),
            "ch10": self._normalize_rc_channel(data[11]),
        }
        self.redis.set("rc:channels", json.dumps(channels))

    def _rc_worker(self) -> None:
        """
        The rc worker
        """
        # Clear eventual previous data
        self.redis.set("rc:channels", "")
        self._update_custom_status()

        try:
            while self._worker_alive:
                data = self._ibus.read()
                # If data checksum is valid
                if data:
                    self._update_channels(data)

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
