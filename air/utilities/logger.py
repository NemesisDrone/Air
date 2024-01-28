"""Logging system to log messages to ipc and to pretty print them to stdout.

:class:`Colors` terminal colors enum.

:class:`Log` log object allowing serialization and deserialization, allowing formatting.

:class:`Logger` logger class, allowing to log messages to ipc and to pretty print them to stdout.
"""

import os
import pickle
import time
from datetime import datetime

from air.utilities import abstracts


class Colors:
    """
    Terminal colors enum.

    :cvar RESET: Reset color.
    :cvar BOLD: Bold text.
    :cvar UNDERLINE: Underlined text.
    :cvar BLACK: Black text.
    :cvar RED: Red text.
    :cvar GREEN: Green text.
    :cvar YELLOW: Yellow text.
    :cvar BLUE: Blue text.
    :cvar PURPLE: Purple text.
    :cvar CYAN: Cyan text.
    :cvar WHITE: White text.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


class Log:
    """Log object allowing serialization and deserialization, allowing formatting.

    :attr message: The message to log.
    :attr level: The log level, one of Logger.DEBUG, Logger.INFO, Logger.WARNING, Logger.ERROR, Logger.CRITICAL.
    :attr label: A label, generally the name of the service or the component that is logging the message.
    :attr timestamp: The timestamp of the log.
    :attr printable: Whether the log is printable or not, depending on the log level and the DEBUG environment variable.

    :meth dumps: Serialize the log object.
    :meth loads: Deserialize the log object.
    """

    def __init__(self, message: str, level: str, label: str):
        """Initialize a log object.

        :param message: The message to log.
        :param level: The log level, one of Logger.DEBUG, Logger.INFO, Logger.WARNING, Logger.ERROR, Logger.CRITICAL.
        :param label: A label, generally the name of the service or the component that is logging the message.
        """

        # Accessible through properties
        self._message = message
        self._level = level
        self._label = label
        self._timestamp = time.time()

    @property
    def message(self) -> str:
        """The message to log."""
        return self._message

    @property
    def level(self) -> str:
        """The log level, one of Logger.DEBUG, Logger.INFO, Logger.WARNING, Logger.ERROR, Logger.CRITICAL."""
        return self._level

    @property
    def label(self) -> str:
        """A label, generally the name of the service or the component that is logging the message."""
        return self._label

    @property
    def timestamp(self) -> float:
        """The timestamp of the log."""
        return self._timestamp

    @property
    def printable(self) -> bool:
        """Whether the log is printable or not, depending on the log level and the DEBUG environment variable."""
        return self.level != Logger.DEBUG or os.environ.get("DEBUG") == "1"

    def dumps(self) -> bytes:
        """Serialize the log object.

        Serialization is achieved using pickle.

        :return: The serialized log object.
        """
        return pickle.dumps(
            {"message": self.message, "level": self.level, "label": self.label, "timestamp": self.timestamp}
        )

    @staticmethod
    def loads(data: bytes) -> "Log":
        """Deserialize the log object.

        Deserialization is achieved using pickle.

        :param data: The serialized log object.

        :return: The deserialized log object.
        """

        data = pickle.loads(data)
        log = Log(message=data["message"], level=data["level"], label=data["label"])
        log._timestamp = data["timestamp"]
        return log

    def __str__(self):
        color = ""
        match self.level:
            case Logger.DEBUG:
                color = Colors.WHITE
            case Logger.INFO:
                color = Colors.GREEN
            case Logger.WARNING:
                color = Colors.YELLOW
            case Logger.ERROR:
                color = Colors.RED
            case Logger.CRITICAL:
                color = Colors.RED + Colors.BOLD

        return (
            f"{Colors.RESET}{datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')} "
            f"{Colors.PURPLE + Colors.BOLD + Colors.UNDERLINE}{self.label}{Colors.RESET + color + Colors.BOLD}"
            f" {self.level}{Colors.RESET}{color}: {self.message}{Colors.RESET}\n"
        )


class Logger:
    """Logger class, allowing to log messages to ipc and to pretty print them to stdout.

    :cvar DEBUG: Debug log level.
    :cvar INFO: Info log level.
    :cvar WARNING: Warning log level.
    :cvar ERROR: Error log level.
    :cvar CRITICAL: Critical log level.

    :meth log: Log a message to stdout and to ipc system as "log.{level}.{label}" route.
    :meth debug: Log a message to stdout and to ipc system as "log.DEBUG.{label}" route.
    :meth info: Log a message to stdout and to ipc system as "log.INFO.{label}" route.
    :meth warning: Log a message to stdout and to ipc system as "log.WARNING.{label}" route.
    :meth error: Log a message to stdout and to ipc system as "log.ERROR.{label}" route.
    :meth critical: Log a message to stdout and to ipc system as "log.CRITICAL.{label}" route.
    """

    DEBUG: str = "DEBUG"
    INFO: str = "INFO"
    WARNING: str = "WARNING"
    ERROR: str = "ERROR"
    CRITICAL: str = "CRITICAL"

    def __init__(self, ipc_node: abstracts.IIpcNode):
        """Initialize a logger object.

        :param ipc_node: The ipc node to use to send messages to ipc system.
        """

        self._ipc_node = ipc_node

    def log(self, message: str, label: str = None, level: str = INFO, extra_channel: str = None) -> None:
        """Log a message to stdout and to ipc system as "log.{level}.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str level: The log level, e.g Logger.DEBUG, Logger.INFO, Logger.WARNING, Logger.ERROR, Logger.CRITICAL.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log:{level}:{label}:a:b:c` channel, defaults to ""
        (resulting in `log:{level}:{label}` route).
        """
        channel = f"log:{level}:{label}:{extra_channel}" if extra_channel else f"log:{level}:{label}"

        log = Log(message, level, label)
        self._ipc_node.send(channel, log.dumps(), loopback=True, _nolog=True)

        if log.printable:
            print(log, flush=True, end="")

    def debug(self, message: str, label: str = None, extra_channel: str = None) -> None:
        """Log a message to stdout and to ipc system as "log.DEBUG.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.DEBUG:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.DEBUG:{label}` route).
        """
        self.log(message, label, Logger.DEBUG, extra_channel)

    def info(self, message: str, label: str = None, extra_channel: str = None) -> None:
        """Log a message to stdout and to ipc system as "log.INFO.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.INFO:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.INFO:{label}` route).
        """
        self.log(message, label, Logger.INFO, extra_channel)

    def warning(self, message: str, label: str = None, extra_channel: str = None) -> None:
        """Log a message to stdout and to ipc system as "log.WARNING.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.WARNING:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.WARNING:{label}` route).
        """
        self.log(message, label, Logger.WARNING, extra_channel)

    def error(self, message: str, label: str = None, extra_channel: str = None) -> None:
        """Log a message to stdout and to ipc system as "log.ERROR.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.ERROR:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.ERROR:{label}` route).
        """
        self.log(message, label, Logger.ERROR, extra_channel)

    def critical(self, message: str, label: str = None, extra_channel: str = None) -> None:
        """Log a message to stdout and to ipc system as "log.CRITICAL.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.CRITICAL:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.CRITICAL:{label}` route).
        """
        self.log(message, label, Logger.CRITICAL, extra_channel)
