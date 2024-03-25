# DRAFT IMU
import json
import time
import math
import board
import busio
from adafruit_bno08x.i2c import BNO08X_I2C
from adafruit_bno08x import BNO_REPORT_ROTATION_VECTOR

def quaternion_to_euler(q):
    q0, q1, q2, q3 = q
    yaw = math.atan2(2*(q0*q3 + q1*q2), 1 - 2*(q2**2 + q3**2))
    pitch = math.asin(2*(q0*q2 - q3*q1))
    roll = math.atan2(2*(q0*q1 + q2*q3), 1 - 2*(q1**2 + q2**2))
    return yaw, pitch, roll

i2c = busio.I2C(board.SCL, board.SDA)
bno = BNO08X_I2C(i2c)
bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)


bno.begin_calibration()

import redis
r = redis.Redis(host="localhost", port=6379, db=0)

while True:
    quat_i, quat_j, quat_k, quat_real = bno.quaternion
    yaw, pitch, roll = quaternion_to_euler([quat_i, quat_j, quat_k, quat_real])

    yaw = math.degrees(yaw)
    pitch = math.degrees(pitch)
    roll = math.degrees(roll)

    print("Yaw: %0.2f  Pitch: %0.2f  Roll: %0.2f" % (yaw, pitch, roll))
    r.set(
        "sensors:imu:data",
        json.dumps({"roll": roll, "pitch": pitch, "yaw": yaw})
    )

    time.sleep(0.1)