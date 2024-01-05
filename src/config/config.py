import json

from utilities import component, ipc


class ConfigComponent(component.Component):
    """
    This component is responsible for updating the config of the drone.
    """
    NAME = "config"

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

    @ipc.Route(["config:*"], False).decorator
    def update_config(self, call_data: ipc.CallData, payload: dict):
        """
        This method is used to update the config of the drone.
        """
        if "canals" in payload:
            for canal in payload["canals"]:
                self.redis.set(f"config:canal:{canal['canal']}", json.dumps(canal))

        self.logger.info("Config was updated", self.NAME)

    def start(self):
        pass

    def stop(self):
        pass
