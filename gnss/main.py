import json
import time

from utilities import ipc as ipc


class GnssClient(ipc.IpcNode):

    def __init__(self):
        super().__init__()

        self.file = open("/app/gnss.txt", "w")

    @ipc.route("sensors:sim7600:gnss")
    def listen(self, data):
        self.file.write(json.dumps(data) + "\n")
        # Flush to disk
        self.file.flush()
        self.log(f"Flushed {data}")


GnssClient().start()
