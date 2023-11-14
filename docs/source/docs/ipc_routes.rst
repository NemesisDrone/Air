IPC Routes
==========

Redis in-memory db is used as IPC mechanism, all IpcNode subscribes to pubsub "ipc" channel, the messages routing to the
good nodes is abstracted by the Route system.

.. tip:: See :doc:`ipc <./components/nemesis_utilities/ipc>` for more details about the IPC system.

.. danger:: Never use other characters than letters and ':' in routes, it will break the routing system.

This page describes and references all IPC Routes used by components.

Logs
----

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - log:<level>:<label>:*
      - {"label": <label>, "level": <level>, "message": <message>, "timestamp": <timestamp>}
      - Used to send a log message from <label> to the log system using <level> as log level, this route can be
        completed with any additional filter. This route is used by the
        :meth:`src.nemesis_utilities.utilities.ipc.IpcNode.log` method.

    * - stdout
      - {"message": <message>}
      - Every single messages sent to the terminal (stdout) is sent to this route.
        This route is used by the :meth:`src.nemesis_utilities.utilities.ipc._StdOverrider` class.

    * - stderr
      - {"message": <message>}
      - Every single messages sent to the terminal (stderr) is sent to this route.
        This route is used by the :meth:`src.nemesis_utilities.utilities.ipc._StdOverrider` class.

State
------

Set
~~~

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - state:start:<component>
      - {"component": <component>}
      - Ask the manager to start the component <component>. If the component is already started, nothing happens.

    * - state:stop:<component>
      - {"component": <component>}
      - Ask the manager to stop the component <component>. If the component is already stopped, nothing happens.

    * - state:restart:<component>
      - {"component": <component>}
      - Ask the manager to restart the component <component>. If the component is already stopped, it will be started.
          If the component is already started, it will be stopped and started again.

    * - state:stop_all
      - {}
      - Ask the manager to stop all components.

    * - state:restart_all
      - {}
      - Ask the manager to restart all components.

Events
~~~~~~

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - state:<component>:starting
      - {"component": <component>}
      - Sent by the component when it is starting.

    * - state:<component>:started
      - {"component": <component>}
      - Sent by the component when it is started.

    * - state:<component>:stopping
      - {"component": <component>}
      - Sent by the component when it is stopping.

    * - state:<component>:stopped
      - {"component": <component>}
      - Sent by the component when it is stopped.

Current state
~~~~~~~~~~~~~

.. note::
    Current states are stored as key/value in the Redis db.

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Key
      - Data structure
      - Purpose

    * - state:<component>:state
      - "<state>"
      - Sent by the component when it is started or stopped to update its current state.

Other
~~~~~

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - state:<component>:stop
      - {"component": <component>}
      - Sent by the manager to the component to ask it to stop.

Sensors
-------

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - sensors:full
      - {'timestamp': raw['timestamp'],
        'roll': <-180° | +180°>,
        'pitch': <-180° | +180°>,
        'yaw': <-180° | +180°>,
        'gyroRoll': <Radians/s>,
        'gyroPitch': <Radians/s>,
        'gyroYaw': <Radians/s>,
        'accelX': <G>,
        'accelY': <G>,
        'accelZ': <G>,
        'compassX': <uT Micro Teslas>,
        'compassY': <uT Micro Teslas>,
        'compassZ': <uT Micro Teslas>,
        'pressure': <Millibars /!\ Broken>,
        'temperature': <Celcius /!\ Broken>,
        'humidity': <Percentage /!\ Broken>,
        }
      - Sensors data

