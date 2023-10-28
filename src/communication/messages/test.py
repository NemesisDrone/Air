import random
import time
from utilities import component as component
from utilities.ipc import IpcNode, route, LogLevels


class TestCompo(component.Component,IpcNode):
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
        if random.randint(0, 1):
            self.log("TARGET NEUTRALIZED")
        else:
            self.log("TARGET MISSED, TRYING TO REACH AGAIN", level=LogLevels.WARNING)

        if random.randint(0, 1):
            self.log("Lost WING", LogLevels.CRITICAL)
        else:
            self.log("Lost MOTOR", LogLevels.CRITICAL)

    def work(self):
        while self.work_please:
            # I send a message to the `pong` route, since I want this node to receive it, I set `loopback` to True.
            rand_value = random.randint(97, 110)
            # print('Sent altitude: ', rand_value)
            self.send("sensor:altitude", rand_value)
            rand_value = random.randint(0, 100)
            # print('Sent battery: ', rand_value)
            self.send("sensor:battery", rand_value)
            rand_value = random.randint(30, 40)
            # print('Sent speed: ', rand_value)
            self.send("sensor:speed", rand_value)
            self.send("pong", {"extra_message": "Hello World!"}, loopback=True)
            self.log("RETURN TO HOME", level=LogLevels.WARNING)
            time.sleep(1)


def run():
    n = TestCompo()
    n.start()
    n.work()


