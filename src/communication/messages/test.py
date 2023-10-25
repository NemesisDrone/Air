import random
import time

from utilities.ipc import IpcNode, route, LogLevels
class PingPongNode(IpcNode):

    # I register a ping route, all messages sent to `ping` route will be received by this function
    @route("ping")
    def ping(self, payload: dict):
        self.log("Ping!")

        # I send a message to the `pong` route, since I want this node to receive it, I set `loopback` to True.
        self.send("pong", {"extra_message": "Hello World!"}, loopback=True)
        rand_value = random.randint(97, 110)
        print('Sent altitude: ', rand_value)
        self.send("sensor:altitude", rand_value)
        rand_value = random.randint(0, 100)
        print('Sent battery: ', rand_value)
        self.send("sensor:battery", rand_value)
        rand_value = random.randint(30, 40)
        print('Sent speed: ', rand_value)
        self.send("sensor:speed", rand_value)
        self.log("RETURN TO HOME", level=LogLevels.WARNING)

    # I register a pong route, all messages sent to `pong` route will be received by this function
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
        # I can access the data sent by the ping function
        # self.log(payload["extra_message"])

    # I register a blocking route, all messages sent to `return_pi` route will be received by this function
    # Value will be sent back to the sender
    @route("return_pi", blocking=True, thread=True)
    def return_pi(self, payload: dict):
        return 3.14159265359


# I create a new node called `ipc-node-test`
n = PingPongNode("ipc-node-test")
# I start the node
n.start()
while True:
    # I send a message to the `ping` route and use `loopback` since I want to receive it with the same node
    n.send("ping", {}, loopback=True)
    # I send a message to the `return_pi`  blocking route, this will wait for the response
    n.log(n.send_blocking("return_pi", {}, loopback=True), level=LogLevels.DEBUG)
    # I don't forget to stop the node !
    # break
    time.sleep(1)
n.stop()


