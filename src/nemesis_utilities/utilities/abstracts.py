import abc


class IIpcSender(abc.ABC):
    """
    Partial IPC Node interface.
    """

    @abc.abstractmethod
    def send(self,
             channel: str,
             payload: dict,
             concurrent: bool = None,
             loopback: bool = False,
             _nolog: bool = False
             ):
        """
        Send a message to the IPC.

        :param channel: The channel to send the message on.
        :param payload: The payload to send as a dict.

        .. warning::
            The payload must be picklable, so it must be a dict with only picklable values.

        :param concurrent: Whether the request is concurrent or not. If set, will override the route concurrent
            parameter. If set to True, will run the function in a separate thread. If set to False, will run the
            function in the listener thread, the listener will be blocked until the function returns.
        :param loopback: Whether the message is a loopback or not. If True, the node who sent the message will be able
            to receive it. Defaults to False.
        :param _nolog: Whether to log the request or not. Defaults to False.
        """

        raise NotImplementedError


class IIpcNode(IIpcSender, abc.ABC):

    @property
    @abc.abstractmethod
    def logger(self):
        """
        The logger instance.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def ipc_id(self):
        """
        The IPC ID.
        """
        raise NotImplementedError