import json

from utilities import component, ipc


class ConfigComponent(component.Component):
    """
    This component is responsible for updating the config of the drone.
    """
    NAME = "config"

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

    @ipc.Route(["config:data"], False).decorator
    def update_config(self, call_data: ipc.CallData, payload: dict):
        """
        This method is used to update the config of the drone.
        """
        self.redis.set("config:name", payload["name"])

        canals_count = len(payload["servo_canals"])  # Canal count as to be the same for servos and brushless
        if len(payload["brushless_canals"]) != canals_count:
            self.logger.warning("Servos and brushless canals count mismatch", self.NAME)
            return

        """
        Save the config of the servos and brushless motors canals
        """
        for i in range(1, canals_count + 1):
            self.redis.set(f"config:servos:canal:{i}", json.dumps(payload["servo_canals"][i - 1]))
            self.redis.set(f"config:brushless:canal:{i}", json.dumps(payload["brushless_canals"][i - 1]))

        self.logger.info("Config was updated", self.NAME)

    def start(self):
        pass

    def stop(self):
        pass
