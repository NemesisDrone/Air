The Sense Hat component
=======================

Integration of the raspberry pi sense hat for sensing various data such as orientation, acceleration, temperature,
humidity, pressure, etc.
Component name: `sense_hat`

Custom Status
-------------

The component publishes and set a custom status message to `sensors:sense_hat:status`.

.. code-block::

    {
    "sense_hat_worker_alive": boolean,
    "sense_hat_emulation": boolean
    }

The `sense_hat_worker_alive` field indicates if the sensing worker is alive or not.

The `sense_hat_emulation` field indicates if the sensing worker is emulating its data or not.
If this field is set to `true`, the sense_hat is not recognized and data is emulated.

Data
----

The component publishes and set the data to `sensors:sense_hat:data`.

.. code-block::

    {
    "timestamp": float,  # some tests need to be done to check the timestamp returned for raw data
    "roll": float,
    "pitch": float,
    "yaw": float,
    "q1": float,
    "q2": float,
    "q3": float,
    "q4": float,
    "gyroRoll": float,
    "gyroPitch": float,
    "gyroYaw": float,
    "accelX": float,
    "accelY": float,
    "accelZ": float,
    "compassX": float,
    "compassY": float,
    "compassZ": float,
    "pressure": float,
    "temperature": float,
    "humidity": float,
    }


The `timestamp` field is the timestamp of the data. Obtained using time.time() for emulated data, the format
for raw data is not currently known.

The `roll`, `pitch` and `yaw` fields are the orientation of the sense hat in degrees from +180 to -180.

The `q1`, `q2`, `q3` and `q4` fields are the quaternion representation of the orientation of the sense hat.

The `gyroRoll`, `gyroPitch` and `gyroYaw` fields are the raw gyroscopic data in radians per second.

The `accelX`, `accelY` and `accelZ` fields are the raw accelerometer data in Gs.

The `compassX`, `compassY` and `compassZ` fields are the raw compass data in microteslas.

The `pressure` field is the pressure in millibars.

.. danger::
    This field is currently broken, do not use it.

The `temperature` field is the temperature in degrees Celsius.

.. danger::
    This field is currently broken, do not use it.

The `humidity` field is the humidity in percent.

.. danger::
    This field is currently broken, do not use it.
