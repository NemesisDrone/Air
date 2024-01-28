import json
import threading
import time
import traceback

import math
from utilities import component, ipc

import glob
import os
import typing

import RTIMU


class SenseHat:

    def __init__(self, config_file_path: str):
        """Initialises the Sense HAT.

        :param config_file_path: The path to the config file.
        :raises RuntimeError: If the IMU cannot be initialised.
        """
        self._config_file_path = config_file_path

        # Getting frame buffer device
        self._fb_device = self._get_fb_device()

        # Check device
        self._check_device()

        # Config file path check
        if not os.path.isfile(config_file_path):
            raise RuntimeError(f'Cannot find sense hat config file at {config_file_path}')

        # Load IMU settings
        self._imu_settings = self._load_imu_settings(config_file_path)

        # Instantiate IMU
        self._imu = RTIMU.RTIMU(self._imu_settings)
        self._pressure = RTIMU.RTPressure(self._imu_settings)
        self._pressure.pressureInit()
        self._humidity = RTIMU.RTHumidity(self._imu_settings)
        self._humidity.humidityInit()

        # IMU init
        self.imu_init()

    @staticmethod
    def _get_fb_device() -> typing.Union[str, None]:
        """Finds the correct frame buffer device for the sense HAT
        and returns its /dev name.
        """

        device = None

        for fb in glob.glob('/sys/class/graphics/fb*'):
            name_file = os.path.join(fb, 'name')
            if os.path.isfile(name_file):
                with open(name_file, 'r') as f:
                    name = f.read()
                if name.strip() == 'RPi-Sense FB':
                    fb_device = fb.replace(os.path.dirname(fb), '/dev')
                    if os.path.exists(fb_device):
                        device = fb_device
                        break

        return device

    def _check_device(self):
        """Check if the device is available.

        :raises RuntimeError: If the device is not available.
        """
        # Frame buffer device check
        if self._fb_device is None:
            raise OSError('Unable to detect sense hat device')
        # Check I2C
        if not glob.glob('/dev/i2c*'):
            raise OSError('Unable to detect sense hat device, you may enable I2C in raspi-config')

    @staticmethod
    def _load_imu_settings(config_file_path: str) -> RTIMU.Settings:
        """Loads the IMU settings from the given config file path.

        :param config_file_path: The path to the config file.
        :return: The loaded IMU settings.
        """
        return RTIMU.Settings(config_file_path.replace('.ini', ''))

    def dumps_settings(self) -> str:
        """Dumps the current settings to a string.

        :return: The dumped settings.
        """

        return f"IMU loaded\n" \
               f"Use IMU settings at {self._config_file_path}\n" \
               f"IMU type {self._imu_settings.IMUType} at I2C address {self._imu_settings.I2CAddress}\n" \
               f"IMU fusion filter: {self._imu_settings.FusionType}\n" \
               f"IMU Calibrations, compass/ellipsoid/accel/gyro: " \
               f"{self._imu_settings.CompassCalValid}/" \
               f"{self._imu_settings.CompassCalEllipsoidValid}/" \
               f"{self._imu_settings.AccelCalValid}/" \
               f"{self._imu_settings.GyroBiasValid}"

    def imu_init(self):
        """Initialises the IMU.

        :raises RuntimeError: If the IMU cannot be initialised.
        """
        if not self._imu.IMUInit():
            raise RuntimeError('Unable to initialise IMU')

    def get_imu_poll_interval(self) -> float:
        """Gets the IMU poll interval.

        :return: The IMU poll interval in seconds.
        """
        return self._imu.IMUGetPollInterval()/1000.0

    def get_imu_data(self) -> typing.Union[typing.Dict[str, typing.Any], None]:
        """Gets the IMU data.

        :return: The IMU data.
        """
        if self._imu.IMURead():
            return self._imu.getIMUData()
        else:
            return None


class SenseHatComponent(component.Component):
    NAME = "sense_hat"

    @staticmethod
    def _hat_setup() -> SenseHat:
        """Set up and init the sense hat"""
        config_file_path = os.environ.get("SENSE_HAT_CONFIG_FILE", "/etc/RTIMULib.ini")
        try:
            hat = SenseHat(config_file_path)
            hat.imu_init()
        except Exception as e:
            raise RuntimeError(f"Could not initialize SenseHat: {e}")

        return hat

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        #: Is the sense worker alive
        self._sense_worker_alive = False
        #: The sense worker thread
        self._sens_worker_thread = threading.Thread(target=self._sense_worker, daemon=True)
        #: Is the sense worker data valid or is it emulated data
        self._sense_emulation = False

        #: Sense hat instance, can be None if not available
        self._hat: typing.Union[SenseHat, None] = None
        try:
            self._hat = self._hat_setup()
        except Exception as e:
            self.logger.warning(f"Could not initialize sense hat, defaulting to emulated data: {e}", self.NAME)
            self._sense_emulation = True

        for line in self._hat.dumps_settings().split("\n"):
            self.logger.info(line, self.NAME)

        #: Imu poll interval
        self._imu_poll_interval = self._hat.get_imu_poll_interval()  if self._hat is not None else 0.0

        self._update_custom_status()

    def _update_custom_status(self):
        """
        Update the custom status to sensors:sense_hat:status
        """
        self.redis.set(
            "sensors:sense_hat:status",
            json.dumps(
                {"sense_hat_worker_alive": self._sense_worker_alive, "sense_hat_emulation": self._sense_emulation}),
        )
        self.ipc_node.send(
            "sensors:sense_hat:status",
            {"sense_hat_worker_alive": self._sense_worker_alive, "sense_hat_emulation": self._sense_emulation}
        )

    def _update_sense_data(self):
        raw = self._hat.get_imu_data()

        if raw is None:
            return

        data = {
            "timestamp": raw["timestamp"],
            "roll": math.degrees(raw["fusionPose"][0]),  # -180 | +180
            "pitch": math.degrees(raw["fusionPose"][1]),  # -180 | +180
            "yaw": math.degrees(raw["fusionPose"][2]),  # -180 | +180
            "gyroRoll": math.degrees(raw["gyro"][0]),  # Radians/s
            "gyroPitch": math.degrees(raw["gyro"][1]),  # Radians/s
            "gyroYaw": math.degrees(raw["gyro"][2]),  # Radians/s
            "accelX": raw["accel"][0],  # G
            "accelY": raw["accel"][1],  # G
            "accelZ": raw["accel"][2],  # G
            "compassX": raw["compass"][0],  # uT Micro Teslas
            "compassY": raw["compass"][1],  # uT Micro Teslas
            "compassZ": raw["compass"][2],  # uT Micro Teslas
            "pressure": raw["pressure"],  # Millibars
            "temperature": raw["temperature"],  # Celcius
            "humidity": raw["humidity"],  # Percentage
        }

        self.ipc_node.send("sensors:sense_hat:data", data)
        self.redis.set("sensors:sense_hat:data", json.dumps(data))


    def _update_emulated_sense_data(self):
        data = self.redis.get("sensors:sense_hat:data")
        if data == b'' or b'inc_pitch' not in data:
            data = {
                'timestamp': time.time(),
                'roll': 0, 'pitch': 0, 'yaw': 0,
                'gyroRoll': 0, 'gyroPitch': 0, 'gyroYaw': 0,
                'accelX': 0, 'accelY': 0, 'accelZ': 0,
                'compassX': 0, 'compassY': 0, 'compassZ': 0,
                'pressure': 1013, 'temperature': 20, 'humidity': 50,
                # 2 additional fields for emulating purpose
                'inc_pitch': True, 'inc_roll': True}
            self.redis.set("sensors:sense_hat:data", json.dumps(data))
            self.ipc_node.send("sensors:sense_hat:data", data)
        else:
            data = json.loads(data)
            data['timestamp'] = time.time()
            data['roll'] += 1 if data['inc_roll'] else -1
            if data['roll'] >= 40:
                data['inc_roll'] = False
                data['roll'] = 40
            elif data['roll'] <= -40:
                data['inc_roll'] = True
                data['roll'] = -40

            data['pitch'] += 1 if data['inc_pitch'] else -1
            if data['pitch'] >= 40:
                data['inc_pitch'] = False
                data['pitch'] = 40
            elif data['pitch'] <= 0:
                data['inc_pitch'] = True
                data['pitch'] = 0

            self.redis.set("sensors:sense_hat:data", json.dumps(data))
            self.ipc_node.send("sensors:sense_hat:data", data)

            time.sleep(0.05)

    def _sense_worker(self):
        """
        The sense worker
        """
        # Clear eventual previous data
        self.redis.set("sensors:sense_hat:data", "")
        self._update_custom_status()

        try:
            while self._sense_worker_alive:
                if not self._sense_emulation:
                    self._update_sense_data()
                else:
                    self._update_emulated_sense_data()

        except Exception as e:
            # verbose traceback
            self.logger.error(f"Sense worker stopped unexpectedly: {e}\n{traceback.format_exc()}", self.NAME)
            self._sense_worker_alive = False

        self._update_custom_status()

    def start(self):
        self._sense_worker_alive = True
        self._sens_worker_thread.start()

    def stop(self):
        self._sense_worker_alive = False
        self._sens_worker_thread.join()
