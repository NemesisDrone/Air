from utilities import component as component
from utilities import ipc.LogLevels as ll


import gi
import asyncio as aio
import functools as ft
from websockets.server import serve as wsserve
from websockets.exceptions import exceptions as wssexcept


gi.require_version('Gst', '1.0')
gi.require_version("GstVideo", "1.0")
from gi.repository import GObject, Gst, GstVideo




COMMON_PIPELNE = "v4l2src"
                 " ! videoconvert"
                 " ! openh264enc"
                 " ! video/x-h264,profile=baseline,stream-format=byte-stream"
                 " ! appsink name=sink"




def onDataAvailable(appsink, compo):
    sample = appsink.emit("pull-sample")

    if sample:
        gst_buffer = sample.get_buffer()

        try:
            (ret, buffer_map) = gst_buffer.map(Gst.MapFlags.READ)
            if compo.wss: # Would be useless to store frames while there is no conn.
                compo.waiting.append((gst_buffer, buffer_map))

        finally:
            pass

    return Gst.FlowReturn.OK


async def sendData(wss, stuff):
    await wss.send(stuff[1].data)
    stuff[0].unmap(stuff[1])


async def onConnection(wss, compo):
    compo.log("[NVS] WS Connection opened.", ll.INFO)
    try:
        while True:
            # Push all the frames.
            while compo.waiting:
                await sendData(wss, compo.pop(0))
    except wssexcept.ConnectionClosed:
        # Remove con
        compo.wss = None
        compo.clearWaitingData()
        compo.log("[NVS] WS Connection closed.", ll.INFO)


async def startServing(compo):
    compo.pipeline.set_state(Gst.State.PLAYING)

    try:
        compo.log("[NVS] Starting WS serving.", ll.INFO)
        async with wsserve(ft.partial(onConnection, compo=compo), "", 8000): # [TODO] Change port and restrain to an iface?
            compo.log("[NVS] Waiting for WS connections.", ll.INFO)
            await aio.Future()
    finally:
        compo.pipeline.set_state(Gst.State.NULL)


class NVSComponent(component.Component):
    NAME = "NVS"

    pipeline = None
    sink = None
    wss = None
    waiting = []


    def __init__(self):
        super().__init__()

        Gst.init_check(None)
        Gst.init()  # init gstreamer

        # Setting GST'logging level to output.
        # see https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html
        # Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)

        global COMMON_PIPELNE
        self.pipeline = Gst.parse_launch(COMMON_PIPELNE)
        if not self.pipeline:
            self.log("[NVS] Could not create pipeline.", ll.CRITICAL)
            return

        self.sink = self.pipeline.get_by_name("sink")
        if not self.sink:
            self.log("[NVS] Failed to get pipeline's sink.", ll.CRITICAL)
            return

        # Notify us when it receives a frame
        self.sink.set_property("emit-signals", True)
        # Set CB for new data
        self.sink.connect("new-sample", onDataAvailable, self)

        self.log("[NVS] Initialized.", ll.INFO)


    def start(self):
        aio.run(startServing(self))
        self.log("[NVS] Started.", ll.INFO)


    def stop(self):
        # Close connection if there is one.
        if self.wss:
            self.wss.close()
            self.wss = None

        # Release all the frames' data
        self.clearWaitingData()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        self.log("[NVS] Stopped.", ll.INFO)


    def clearWaitingData(self):
        while self.waiting:
            f = self.waiting.pop(0)
            f[0].unmap(f[1])


def run():
    NVSComponent().start()
