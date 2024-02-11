import json
import threading
from typing import Tuple

from air.utilities import component, ipc
from air.utilities.enums import FlightMode

from .rc_ibus import RcIbus


class RcComponent(component.Component):
    """
    This component is responsible for receiving the channels value from the RC to control the drone
    """
    NAME = "rc"

    def __init__(self, ipc_node: ipc.IpcNode) -> None:
        super().__init__(ipc_node)

        #: Is the rc alive
        self._worker_alive = False
        #: The rc thread
        self._worker_thread = threading.Thread(target=self._rc_worker, daemon=True)
        self._rc_data = None
        # The update channels worker thread
        self._update_channels_worker_thread = threading.Thread(target=self._update_channels_worker, daemon=True)

        try:
            self._ibus = RcIbus("/dev/serial0")
            self._worker_alive = True
        except Exception as e:
            self.logger.warning(f"Could not initialize radio command: {e}", self.NAME)

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
        self.redis.set("rc:channels", "")
        self._update_custom_status()

        try:
            while self._worker_alive:
                data = self._ibus.read()
                # If data checksum is valid
                if data:
                    self._rc_data = data

        except Exception as e:
            self.logger.error(f"Rc worker stopped unexpectedly: {e}", self.NAME)
            self._worker_alive = False

        self._update_custom_status()

    def _update_channels_worker(self) -> None:
        """
        Update the rc channels to rc:channels redis key
        It only update when flight mode is manual
        """

        try:
            while self._worker_alive:
                if not self._rc_data:
                    continue

                flight_mode_channel = str(json.loads(self.redis.get("config:switch:flight_mode_channel")))

                channels = {
                    "1": self._normalize_rc_channel(self._rc_data[2]),
                    "2": self._normalize_rc_channel(self._rc_data[3]),
                    "3": self._normalize_rc_channel(self._rc_data[4]),
                    "4": self._normalize_rc_channel(self._rc_data[5]),
                    "5": self._normalize_rc_channel(self._rc_data[6]),
                    "6": self._normalize_rc_channel(self._rc_data[7]),
                    "7": self._normalize_rc_channel(self._rc_data[8]),
                    "8": self._normalize_rc_channel(self._rc_data[9]),
                    "9": self._normalize_rc_channel(self._rc_data[10]),
                    "10": self._normalize_rc_channel(self._rc_data[11]),
                }
                pipe = self.redis.pipeline()

                """
                When flight mode is manual, then channels are updated from the RC
                """
                if channels[flight_mode_channel] > 50:
                    pipe.set("flight_mode", FlightMode.MANUAL.value)
                    self.redis.set("channels", json.dumps(channels))
                else:
                    pipe.set("flight_mode", FlightMode.AUTONOMOUS.value)

                pipe.execute()

        except Exception as e:
            self.logger.error(f"Rc worker stopped unexpectedly: {e}", self.NAME)
            self._worker_alive = False

    def start(self) -> None:
        self._worker_alive = True
        self._worker_thread.start()
        self._update_channels_worker_thread.start()

    def stop(self) -> None:
        self._worker_alive = False
        self._worker_thread.join()
        self._update_channels_worker_thread.join()
