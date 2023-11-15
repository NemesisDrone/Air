import threading
import time

import math
from utilities import component as component, ipc as ipc
from utilities.sense_hat import SenseHat


class SensorsComponent(component.Component):
    NAME = "sensors"

    def __init__(self):
        super().__init__()
        self.log("Sensors component initialized")

        self.alive = False
        self.is_sensor = True

        try:
            self.hat = SenseHat()
            self.hat.set_imu_config(True, True, True)
            self.hat._init_humidity()
            self.hat._init_pressure()
        except Exception as e:
            self.log("Could not initialize SenseHat: " + str(e), ipc.LogLevels.WARNING)
            self.is_sensor = False

    def sense_hat_listener(self):
        while self.alive and self.is_sensor:
            self.hat._read_imu()
            raw = self.hat._imu.getIMUData()
            data = {'timestamp': raw['timestamp'],
                    'roll': math.degrees(raw['fusionPose'][0]),  # -180 | +180
                    'pitch': math.degrees(raw['fusionPose'][1]),  # -180 | +180
                    'yaw': math.degrees(raw['fusionPose'][2]),  # -180 | +180
                    'gyroRoll': math.degrees(raw['gyro'][0]),  # Radians/s
                    'gyroPitch': math.degrees(raw['gyro'][1]),  # Radians/s
                    'gyroYaw': math.degrees(raw['gyro'][2]),  # Radians/s
                    'accelX': raw['accel'][0],  # G
                    'accelY': raw['accel'][1],  # G
                    'accelZ': raw['accel'][2],  # G
                    'compassX': raw['compass'][0],  # uT Micro Teslas
                    'compassY': raw['compass'][1],  # uT Micro Teslas
                    'compassZ': raw['compass'][2],  # uT Micro Teslas
                    'pressure': raw['pressure'],  # Millibars
                    'temperature': raw['temperature'],  # Celcius
                    'humidity': raw['humidity'],  # Percentage
                    }
            self.send("sensors:full", data)
            self.r.set("sensors:full", data)

    def start(self):
        self.alive = True
        threading.Thread(target=self.sense_hat_listener).start()
        self.log("Sensors component started")

    def stop(self):
        self.alive = False
        self.log("Sensors component stopped")


def run():
    SensorsComponent().start()
