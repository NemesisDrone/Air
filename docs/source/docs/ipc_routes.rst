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
      - - "label": The log label
        - "level": The log level
        - "message": The log message
        - "timestamp": The log timestamp
      - Used to send a log message from <label> to the log system using <level> as log level, this route can be
        completed with any additional filter. This route is used by the
        :meth:`src.nemesis_utilities.utilities.ipc.IpcNode.log` method.

    * - stdout
      - - "message": The log message
      - Every single messages sent to the terminal (stdout) is sent to this route.
        This route is used by the :meth:`src.nemesis_utilities.utilities.ipc._StdOverrider` class.

    * - stderr
      - - "message": The log message
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
      - - "component": The component name
      - Ask the manager to start the component <component>. If the component is already started, nothing happens.

    * - state:stop:<component>
      - - "component": The component name
      - Ask the manager to stop the component <component>. If the component is already stopped, nothing happens.

    * - state:restart:<component>
      - - "component": The component name
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
      - - "component": The component name
      - Sent by the component when it is starting.

    * - state:<component>:started
      - - "component": The component name
      - Sent by the component when it is started.

    * - state:<component>:stopping
      - - "component": The component name
      - Sent by the component when it is stopping.

    * - state:<component>:stopped
      - - "component": The component name
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
      - The state
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
      - - "component": The component name
      - Sent by the manager to the component to ask it to stop.

Custom States
~~~~~~~~~~~~~

.. note::
    Custom states depends on the component and are used to give more accurate information about the component state.

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - state:laser:custom
      - - "alive": True/False (If the component is reading data)
        - "valid": True/False (If the component is working/detected)
      - Sent by the laser component when its custom state is updated.

    * - state:sensors:custom
      - - "alive": True/False (If the component is reading data)
        - "valid": True/False (If the component is working/detected)
      - Sent by the sensors component when its custom state is updated.

    * - state:sim7600:custom
      - - "alive": True/False (If the component is reading data)
        - "valid": True/False (If the component is working/detected)
      - Sent by the sim7600 component when its custom state is updated.

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Key
      - Data structure
      - Purpose

    * - state:laser:custom
      - - "alive": True/False (If the component is reading data)
        - "valid": True/False (If the component is working/detected)
      - Set by the laser component when its custom state is updated.

    * - state:sensors:custom
      - - "alive": True/False (If the component is reading data)
        - "valid": True/False (If the component is working/detected)
      - Set by the sensors component when its custom state is updated.

    * - state:sim7600:custom
      - - "alive": True/False (If the component is reading data)
        - "valid": True/False (If the component is working/detected)
      - Set by the sim7600 component when its custom state is updated.

Sensors
-------

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - sensors:full
      - - "timestamp": The timestamp
        - "roll": The roll angle (-180° to +180°)
        - "pitch": The pitch angle (-180° to +180°)
        - "yaw": The yaw angle (-180° to +180°)
        - "gyroRoll": The roll gyroscope value (Radians/s)
        - "gyroPitch": The pitch gyroscope value (Radians/s)
        - "gyroYaw": The yaw gyroscope value (Radians/s)
        - "accelX": The X accelerometer value (G)
        - "accelY": The Y accelerometer value (G)
        - "accelZ": The Z accelerometer value (G)
        - "compassX": The X compass value (uT Micro Teslas)
        - "compassY": The Y compass value (uT Micro Teslas)
        - "compassZ": The Z compass value (uT Micro Teslas)
        - "pressure": The pressure value (Millibars /!\ Broken)
        - "temperature": The temperature value (Celcius /!\ Broken)
        - "humidity": The humidity value (Percentage /!\ Broken)
      - Sensors data

    * - sensors:laser:distance
      - The distance (in ??)
      - Used by the laser sensor to send the distance measured.

    * - sensors:sim7600:gnss
      - - "fixMode": the fix mode (useless)
        - "gpsSat": the number of GPS satellites
        - "gloSat": the number of GLONASS satellites
        - "beiSat": the number of BEIDOU satellites
        - "lat": the latitude of format (degrees, minutes)
        - "latInd": the latitude indicator (N or S) WARNING, multiply lat degrees by -1 if latInd is S
        - "lon": the longitude of format (degrees, minutes)
        - "lonInd": the longitude indicator (E or W) WARNING, multiply lon degrees by -1 if lonInd is W
        - "date": the date of format DDMMYY
        - "time": the time of format HHMMSS
        - "alt": the altitude in meters
        - "speed": the speed in km/h (not tested)
        - "course": the course in degrees (not tested)
        - "pdop": the pdop
        - "hdop": the hdop
        - "vdop": the vdop

      - Used by the sim7600 sensor to send the GNSS data.

.. note::
    Sensors data is also stored as key/value in the Redis db.

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Key
      - Data structure
      - Purpose

    * - sensors:full
      - - "timestamp": The timestamp
        - "roll": The roll angle (-180° to +180°)
        - "pitch": The pitch angle (-180° to +180°)
        - "yaw": The yaw angle (-180° to +180°)
        - "gyroRoll": The roll gyroscope value (Radians/s)
        - "gyroPitch": The pitch gyroscope value (Radians/s)
        - "gyroYaw": The yaw gyroscope value (Radians/s)
        - "accelX": The X accelerometer value (G)
        - "accelY": The Y accelerometer value (G)
        - "accelZ": The Z accelerometer value (G)
        - "compassX": The X compass value (uT Micro Teslas)
        - "compassY": The Y compass value (uT Micro Teslas)
        - "compassZ": The Z compass value (uT Micro Teslas)
        - "pressure": The pressure value (Millibars /!\ Broken)
        - "temperature": The temperature value (Celcius /!\ Broken)
        - "humidity": The humidity value (Percentage /!\ Broken)
      - Sensors data

    * - sensors:laser:distance
      - The distance (in ??)
      - Used by the laser sensor to send the distance measured.

    * - sensors:sim7600:gnss
      - - "fixMode": the fix mode (useless)
        - "gpsSat": the number of GPS satellites
        - "gloSat": the number of GLONASS satellites
        - "beiSat": the number of BEIDOU satellites
        - "lat": the latitude of format (degrees, minutes)
        - "latInd": the latitude indicator (N or S) WARNING, multiply lat degrees by -1 if latInd is S
        - "lon": the longitude of format (degrees, minutes)
        - "lonInd": the longitude indicator (E or W) WARNING, multiply lon degrees by -1 if lonInd is W
        - "date": the date of format DDMMYY
        - "time": the time of format HHMMSS
        - "alt": the altitude in meters
        - "speed": the speed in km/h (not tested)
        - "course": the course in degrees (not tested)
        - "pdop": the pdop
        - "hdop": the hdop
        - "vdop": the vdop

      - Used by the sim7600 sensor to send the GNSS data.

