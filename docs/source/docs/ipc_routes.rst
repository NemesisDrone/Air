IPC Routes
==========

Redis in-memory db is used as IPC mechanism, all IpcNode subscribes to pubsub "ipc" channel, the messages routing to the
good nodes is abstracted by the Route system.

.. tip:: See :ref:`ipc <docs/components/nemesis_utilities/ipc>` for more details about the IPC system.

This page describes and references all IPC Routes used by components.

Logs
----

.. list-table::
    :widths: 20 30 50
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - log.<level>.<label>
      - {"label": <label>, "level": <level>, "message": <message>}
      - Used to send a log message from <label> to the log system using <level> as log level.
        This route is used by the :meth:`src.nemesis_utilities.utilities.ipc.IpcNode.log` method.

    * - stdout
      - {"message": <message>}
      - Every single messages sent to the terminal (stdout) is sent to this route.
        This route is used by the :meth:`src.nemesis_utilities.utilities.ipc._StdOverrider` class.

    * - stderr
      - {"message": <message>}
      - Every single messages sent to the terminal (stderr) is sent to this route.
        This route is used by the :meth:`src.nemesis_utilities.utilities.ipc._StdOverrider` class.
