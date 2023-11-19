from utilities import component as component, ipc
import time

from nemesis_utilities.utilities.component import State


class HelloComponent(component.Component):
    NAME = "hello"

    def __init__(self):
        super().__init__()
        self.do_work_please = False
        self.log("Hello component initialized")

    def start(self):
        self.log("Hello component started")
        self.do_work_please = True

    def do_work(self):
        i = 0
        while self.do_work_please:
            self.log(f"Hello World {i}", ipc.LogLevels.DEBUG)
            i += 1
            time.sleep(2)

    def stop(self):
        self.do_work_please = False
        self.log("Hello component stopped")


def run():
    compo = HelloComponent()
    compo.start()
    compo.do_work()
