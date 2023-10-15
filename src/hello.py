from utilities import component as component


class HelloComponent(component.Component):
    NAME = "hello"

    def __init__(self):
        super().__init__()
        self.log("Hello component initialized")

    def start(self):
        self.log("Hello component started")

    def stop(self):
        self.log("Hello component stopped")


def run():
    HelloComponent().start()
