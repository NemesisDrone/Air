import json
import threading
import time
import traceback

import math
from utilities import component, ipc, custom_sense_hat as csh


class SenseHatComponent(component.Component):
    NAME = "sense_hat"

    def _hat_setup(self):
        try:
            hat = csh.SenseHat()
            hat.set_imu_config(True, True, True)
            hat._init_humidity()
            hat._init_pressure()

            # hat.show_message("OK", text_colour=self.primary_color)

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
        self.primary_color = [34, 197, 94]

        try:
            self._hat = self._hat_setup()
        except Exception as e:
            self.logger.warning(f"Could not initialize sense hat, defaulting to emulated data: {e}", self.NAME)
            self._sense_emulation = True

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
        self._hat._read_imu()
        raw = self._hat._imu.getIMUData()

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
            self.logger.error(f"Sense worker stopped unexpectedly: {e}", self.NAME)
            self._sense_worker_alive = False

        self._update_custom_status()

    def start(self):
        self._sense_worker_alive = True
        self._sens_worker_thread.start()

    def stop(self):
        self._sense_worker_alive = False
        self._sens_worker_thread.join()
