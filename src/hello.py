from utilities import component as component
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
            print('Hello World!', i, flush=True)
            i += 1
            time.sleep(2)

    def stop(self):
        self.do_work_please = False
        self.log("Hello component stopped")


def run():
    compo = HelloComponent()
    compo.start()
    compo.do_work()

