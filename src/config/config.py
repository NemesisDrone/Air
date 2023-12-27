import json

from utilities import component as component, ipc
from utilities.ipc import route


class ConfigComponent(component.Component):
    """
    This component is responsible for updating the config of the drone.
    """
    NAME = "config"

    def __init__(self):
        super().__init__()
        self.log("Config component initialized")

    def start(self):
        return self

    @route("config")
    def update_config(self, payload: dict):
        """
        This method is used to update the config of the drone.
        """
        if "canals" in payload:
            for canal in payload["canals"]:
                self.r.set(f"config:canal:{canal['canal']}", json.dumps(canal))

        self.log("Config updated")

    def stop(self):
        self.log("Config component stopped")


def run():
    compo = ConfigComponent().start()
