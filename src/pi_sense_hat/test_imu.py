import json
import time

import math
from custom_sense_hat import SenseHat

hat = SenseHat(imu_settings_file="RTIMULib")
hat.set_imu_config(True, True, True)

recording_time = 30
start_time = time.time()

data = []

while (time.time() - start_time) < recording_time:
    try:
        hat._read_imu()
        raw = hat._imu.getIMUData()

        print(raw["compass"][0], raw["compass"][1], raw["compass"][2])
        # remaining time
        print(recording_time - (time.time() - start_time))

        data.append(raw["compass"])
    except Exception as e:
        print(f"Error: {e}")

    time.sleep(0.01)


with open("compass_calibrated_2_data_30.json", "w") as f:
    json.dump(data, f)

print("Done")