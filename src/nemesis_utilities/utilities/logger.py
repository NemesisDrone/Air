from datetime import datetime
import os
import pickle
import time

import utilities.abstracts as abstracts  # TODO: fix import


class Colors:
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

    def __init__(self, message: str, level: str, label: str):
        self._message = message
        self._level = level
        self._label = label

        self._timestamp = time.time()

    @property
    def message(self) -> str:
        return self._message

    @property
    def level(self) -> str:
        return self._level

    @property
    def label(self) -> str:
        return self._label

    @property
    def timestamp(self) -> float:
        return self._timestamp

    @property
    def printable(self) -> bool:
        return self.level != Logger.DEBUG or os.environ.get("DEBUG") == "1"

    def dumps(self) -> bytes:
        return pickle.dumps({
            "message": self.message,
            "level": self.level,
            "label": self.label,
            "timestamp": self.timestamp
        })

    @staticmethod
    def loads(data: bytes) -> "Log":
        data = pickle.loads(data)
        log = Log(
            message=data["message"],
            level=data["level"],
            label=data["label"]
        )
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

        return (f"{Colors.RESET}{datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')} "
                f"{Colors.PURPLE + Colors.BOLD + Colors.UNDERLINE}{self.label}{Colors.RESET + color + Colors.BOLD}"
                f" {self.level}{Colors.RESET}{color}: {self.message}{Colors.RESET}\n")


class Logger:
    """
    Implementation of the logger.
    """
    DEBUG: str = "DEBUG"
    INFO: str = "INFO"
    WARNING: str = "WARNING"
    ERROR: str = "ERROR"
    CRITICAL: str = "CRITICAL"

    def __init__(self, ipc_node: abstracts.IIpcSender):
        self._ipc_node = ipc_node

    def log(
            self,
            message: str,
            label: str = None,
            level: str = INFO,
            extra_channel: str = None):
        """
        Log a message to stdout and to ipc system as "log.{level}.{label}" route.

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

    def debug(
            self,
            message: str,
            label: str = None,
            extra_channel: str = None):
        """
        Log a message to stdout and to ipc system as "log.DEBUG.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.DEBUG:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.DEBUG:{label}` route).
        """
        self.log(message, label, Logger.DEBUG, extra_channel)

    def info(
            self,
            message: str,
            label: str = None,
            extra_channel: str = None):
        """
        Log a message to stdout and to ipc system as "log.INFO.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.INFO:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.INFO:{label}` route).
        """
        self.log(message, label, Logger.INFO, extra_channel)

    def warning(
            self,
            message: str,
            label: str = None,
            extra_channel: str = None):
        """
        Log a message to stdout and to ipc system as "log.WARNING.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.WARNING:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.WARNING:{label}` route).
        """
        self.log(message, label, Logger.WARNING, extra_channel)

    def error(
            self,
            message: str,
            label: str = None,
            extra_channel: str = None):
        """
        Log a message to stdout and to ipc system as "log.ERROR.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.ERROR:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.ERROR:{label}` route).
        """
        self.log(message, label, Logger.ERROR, extra_channel)

    def critical(
            self,
            message: str,
            label: str = None,
            extra_channel: str = None):
        """
        Log a message to stdout and to ipc system as "log.CRITICAL.{label}" route.

        :param str message: The message to log.
        :param str label: A label, generally the name of the service or the component that is logging the message.
        :param str extra_channel: An additional extra channel that will be appended to the channel, for example, if I
        give `a:b:c` as extra channel, the message will be sent to `log.CRITICAL:{label}:a:b:c` channel, defaults to ""
        (resulting in `log.CRITICAL:{label}` route).
        """
        self.log(message, label, Logger.CRITICAL, extra_channel)
