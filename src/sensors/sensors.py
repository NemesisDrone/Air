import json
import threading
import time

import math
from utilities import component as component, ipc as ipc
from utilities.sense_hat import SenseHat


class SensorsComponent(component.Component):
    NAME = "sensors"

    def __init__(self):
        super().__init__()

        self.valid = True
        self.alive = False

        try:
            self.hat = SenseHat()
            self.hat.set_imu_config(True, True, True)
            self.hat._init_humidity()
            self.hat._init_pressure()
        except Exception as e:
            self.log("Could not initialize SenseHat: " + str(e), ipc.LogLevels.WARNING)
            self.valid = False

        self.r.set("state:sensors:custom", json.dumps({"valid": self.valid, "alive": self.alive}))
        self.send("state:sensors:custom", {"valid": self.valid, "alive": self.alive})

        self.log("Sensors component initialized")

    def sense_hat_listener(self):
        self.r.set("state:sensors:custom", json.dumps({"valid": self.valid, "alive": self.alive}))
        self.send("state:sensors:custom", {"valid": self.valid, "alive": self.alive})

        # Emulator datas
        inc_pitch = True
        inc_roll = True
        roll, pitch, yaw = 0, 0, 0
        gyrX, gyrY, gyrZ = 0, 0, 0
        accX, accY, accZ = 0, 0, 0
        compX, compY, compZ = 0, 0, 0
        pressure, temperature, humidity = 1013, 20, 50

        def var():
            nonlocal inc_pitch, inc_roll, roll, pitch, yaw, gyrX, gyrY, gyrZ, accX, accY, accZ, compX, compY, compZ, pressure, temperature, humidity

            roll += 1 if inc_roll else -1
            if roll >= 40:
                inc_roll = False
                roll = 40
            elif roll <= -40:
                inc_roll = True
                roll = -40

            pitch += 1 if inc_pitch else -1
            if pitch >= 40:
                inc_pitch = False
                pitch = 40
            elif pitch <= 0:
                inc_pitch = True
                pitch = 0

        try:
            while self.alive:
                if self.valid:
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
                else:
                    var()
                    data = {'timestamp': time.time(),
                            'roll': roll,  # -180 | +180
                            'pitch': pitch,  # -180 | +180
                            'yaw': yaw,  # -180 | +180
                            'gyroRoll': gyrX,  # Radians/s
                            'gyroPitch': gyrY,  # Radians/s
                            'gyroYaw': gyrZ,  # Radians/s
                            'accelX': accX,  # G
                            'accelY': accY,  # G
                            'accelZ': accZ,  # G
                            'compassX': compX,  # uT Micro Teslas
                            'compassY': compY,  # uT Micro Teslas
                            'compassZ': compZ,  # uT Micro Teslas
                            'pressure': pressure,  # Millibars
                            'temperature': temperature,  # Celcius
                            'humidity': humidity,  # Percentage
                            }
                    # TODO: change later
                    time.sleep(0.05)

                self.send("sensors:full", data)
                self.r.set("sensors:full", json.dumps(data))

        except Exception as e:
            self.log("SenseHat stopped unexpectedly: " + str(e), level=ipc.LogLevels.ERROR)
            self.valid = False
            self.alive = False

        self.r.set("state:sensors:custom", json.dumps({"valid": self.valid, "alive": self.alive}))
        self.send("state:sensors:custom", {"valid": self.valid, "alive": self.alive})

    def start(self):
        self.alive = True

        return self

    def stop(self):
        self.alive = False
        self.log("Sensors component stopped")


def run():
    comp = SensorsComponent().start()
    comp.sense_hat_listener()
    comp.log("Sensors component started")
