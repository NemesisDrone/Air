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

State
------

Update component state
~~~~~~~~~~~~~~~~~~~~~~

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

    * - state:start_all
      - {}
      - Ask the manager to start all components.

    * - state:stop_all
      - {}
      - Ask the manager to stop all components.

    * - state:restart_all
      - {}
      - Ask the manager to restart all components.

State changes event
~~~~~~~~~~~~~~~~~~~

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
      - Set by the component when it is started or stopped to update its current state.

Other
~~~~~

.. note::
    This route is not meant to be used directly.

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - state:<component>:stop
      - - "component": The component name
      - Sent by the manager to the component to ask it to stop.

Sensors
-------

Sensors custom status
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

    * - sensors:sim7600:status
      - - "gnss_worker_alive": if the gnss worker is currently fetching gps position
        - "gnss_emulation": if the data is emulated or not (real data)
      - Used by the sim7600 sensor to send its status.

    * - sensors:sense_hat:status
      - - "sense_hat_worker_alive": if the sense worker is currently fetching sense_hat data
        - "sense_hat_emulation": if the data is emulated or not (real data)
      - Used by the sense_hat sensor to send its status.

    * - sensors:vl53:status
      - - "vl53_worker_alive": if the vl53 worker is currently fetching vl53 data
        - "first_sensor_emulation": if the first sensor data is emulated or not (real data)
        - "second_sensor_emulation": if the second sensor data is emulated or not (real data)
      - Used by the vl53 sensor to send its status.

Sensors data
~~~~~~~~~~~~

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Route
      - Data structure
      - Purpose

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
        - "time": the time of format HHMMSS.XX
        - "alt": the altitude in meters
        - "speed": the speed in km/h (not tested), may be empty
        - "course": the course in degrees (not tested), may be empty
        - "pdop": the pdop
        - "hdop": the hdop
        - "vdop": the vdop
        - "timestamp": The timestamp (time.time())
      - GNSS data uploaded by the GNSS worker of the sim7600 sensor.

    * - sensors:sense_hat:data
      - - "timestamp": The timestamp (time.time() for emulated data, currently unknown for real data, make some tests)
        - "roll": The roll angle (-180° to +180°)
        - "pitch": The pitch angle (-180° to +180°)
        - "yaw": The yaw angle (-180° to +180°)
        - "q1": The quaternion X value
        - "q2": The quaternion Y value
        - "q3": The quaternion Z value
        - "q4": The quaternion W value
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
      - Sense hat data

    * - sensors:vl53:ranges
      - - "first_range": The first range in mm
        - "second_range": The second range in mm
      - VL53L0X data


.. note::
    Sensors data is also stored as key/value in the Redis db.
