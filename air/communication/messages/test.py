# let it but no longer used I guess ?
"""import random
import time

from air.utilities import component
from air.utilities.ipc import IpcNode, LogLevels, route

class TestCompo(component.Component, IpcNode):
    NAME = "TestCompo"
    # I register a ping route, all messages sent to `ping` route will be received by this function

    def __init__(self):
        super().__init__()
        self.log("Test component initialized")
        self.work_please = False

    def start(self):
        self.work_please = True
        self.log("Test component started", level=LogLevels.INFO)

    def stop(self):
        self.work_please = False
        self.log("Test component stopped", level=LogLevels.INFO)
        print("stopped", flush=True)

    @route("pong")
    def pong(self, payload: dict):
        # if random.randint(0, 1):
        #     self.log("TARGET NEUTRALIZED")
        # else:
        #     self.log("TARGET MISSED, TRYING TO REACH AGAIN !", level=LogLevels.WARNING)
        #
        # if random.randint(0, 1):
        #     self.log("Lost WING", LogLevels.CRITICAL)
        # else:
        #     self.log("Lost MOTOR", LogLevels.CRITICAL)
        pass

    def work(self):
        while self.work_please:
            # I send a message to the `pong` route, since I want this node to receive it, I set `loopback` to True.
            rand_value = random.randint(97, 110)
            # print('Sent altitude: ', rand_value)
            self.send("sensors:altitude", rand_value)
            rand_value = random.randint(0, 100)
            # print('Sent battery: ', rand_value)
            self.send("sensors:battery", rand_value)
            rand_value = random.randint(30, 40)
            # print('Sent speed: ', rand_value)
            self.send("sensors:speed", rand_value)
            self.send("pong", {"extra_message": "Hello World!"}, loopback=True)
            laser_distance = self.r.get("sensors:laser-distance")
            laser_distance = int(laser_distance) if laser_distance is not None else 0

            # self.log(f"RETURN TO HOME {laser_distance}mm", level=LogLevels.WARNING)

            time.sleep(1)


def run():
    n = TestCompo()
    n.start()
    n.work()
"""