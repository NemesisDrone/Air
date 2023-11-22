from utilities import component
from utilities.ipc import route
from utilities.ipc import LogLevels as ll

import gi
import threading
import asyncio as aio
from websockets import exceptions as wssexcept
from websockets.server import WebSocketServerProtocol as wssp
from websockets.client import connect as cn

gi.require_version('Gst', '1.0')
gi.require_version("GstVideo", "1.0")
from gi.repository import GObject, Gst, GstVideo


# [TODO] See if it's worth switching back to H264
#COMMON_PIPELINE = "v4l2src ! videoconvert ! v4l2h264enc ! video/x-h264,profile=baseline,stream-format=byte-stream ! appsink name=sink"
COMMON_PIPELINE = "v4l2src ! video/x-raw,format=YUY2,width=1280,height=720,framerate=10/1 ! videoscale ! video/x-raw,format=YUY2,width=320,height=180,framerate=10/1 ! jpegenc quality=30 ! appsink name=sink"


async def functionWrap(func):
    await func()


class NVSState(int):
    """
    Class representing the different states of NVSComponent.
    """
    GstInitFail: int = 0
    PipelineCreationFail: int = 1
    SinkLookupFail: int = 2
    GstBufferFail = 3
    Initialized: int = 4
    WaitingConnection: int = 5
    Streaming: int = 6
    Cleaning: int = 7
    Unknown: int = 8
    PendingStop: int = 9


class NVSComponent(component.Component):
    """
    Component that handles streaming video from cam to WebSocket server.
    """
    NAME = "NVS"

    def __init__(self):
        super().__init__()

        self.nvs_state = NVSState.Unknown
        self.thread: threading.Thread = None
        self.loop: aio.AbstractEventLoop = None
        self.waiting: tuple = None
        self.pipeline = None
        self.sink = None
        self.wss: wssp = None

        if not Gst.init_check(None): # init gstreamer
            self.log("GST init failed!", ll.CRITICAL)
            self.set_nvs_state(NVSState.GstInitFail)
            return

        # Setting GST's logging level to output.
        # see https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html
        # Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)

        global COMMON_PIPELINE
        self.pipeline = Gst.parse_launch(COMMON_PIPELINE)
        if not self.pipeline:
            self.log("Could not create pipeline.", ll.CRITICAL)
            self.set_nvs_state(NVSState.PipelineCreationFail)
            return

        self.sink = self.pipeline.get_by_name("sink")
        if not self.sink:
            self.log("Failed to get pipeline's sink.", ll.CRITICAL)
            self.set_nvs_state(NVSState.SinkLookupFail)
            return

        # Notify us when it receives a frame
        self.sink.set_property("emit-signals", True)
        # Set CB for new data
        self.sink.connect("new-sample", self._on_data_available)

        self.log("Initialized.", ll.INFO)
        self.set_nvs_state(NVSState.Initialized)


    def __del__(self):
        self.stop()


    def set_nvs_state(self, val: int):
        """
        Used as guard to watch unproper behaviours.
        """
        if int(val) < int(NVSState.Initialized):
            self.log("Warning, state:" + str(val), ll.CRITICAL)
        self.nvs_state = val


    def start(self):
        def loop_setter(loop):
            """
            Used to start a thread with an Asyncio event loop running within.
            """
            aio.set_event_loop(loop)
            loop.run_forever()

        if self.nvs_state != NVSState.Initialized:
            return

        self.loop = aio.new_event_loop()
        aio.set_event_loop(self.loop)
        self.thread = threading.Thread(target=loop_setter, args=(self.loop,))
        self.thread.start()
        aio.run_coroutine_threadsafe(functionWrap(self._start_serving), self.loop)

        self.log("Started.", ll.INFO)


    def stop(self):
        self.set_nvs_state(NVSState.Cleaning)

        # Close connection if there is one.
        if self.wss:
            self.set_nvs_state(NVSState.PendingStop)
            while self.nvs_state != NVSState.Initialized:
                pass

        # Release all the frames' data
        self.clear_waiting_data()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        self.log("Stopped.", ll.INFO)
        self.set_nvs_state(NVSState.Initialized)


    def clear_waiting_data(self):
        """
        Clears all the data put in the pending list for sending.
        """
        if self.waiting:
            f, self.waiting = self.waiting, None
            f[0].unmap(f[1])


    async def _start_serving(self):
        try:
            while self.nvs_state != NVSState.PendingStop:
                try:
                    self.set_nvs_state(NVSState.WaitingConnection)
                    try:
                        async with cn("ws://10.0.3.1:7000/") as ws:  # [TODO] See what address to use
                            await self._on_connection(ws)
                    except Exception:
                        pass
                finally:
                    pass
        finally:
            pass

        self.set_nvs_state(NVSState.Initialized)


    async def _on_connection(self, wss: wssp):
        """
        Handles connection to a WS.
        """
        self.pipeline.set_state(Gst.State.PLAYING)
        self.set_nvs_state(NVSState.Streaming)
        self.log("Established.", ll.INFO)
        self.wss = wss

        try:
            while True:
                # Push the current frame.
                if self.waiting:
                    await self.send_data(self.wss, self.waiting)
                    self.waiting = None
        except wssexcept.ConnectionClosed:
            #pass

            # Remove con
            self.wss = None
            self.clear_waiting_data()
            self.log("Lost.", ll.INFO)
            if self.nvs_state != NVSState.PendingStop:
                self.nvs_state = NVSState.WaitingConnection

        self.pipeline.set_state(Gst.State.NULL)


    def _on_data_available(self, appsink):
        """
        Handles incoming data from a GST pipeline.
        """
        sample = appsink.emit("pull-sample")

        if sample:
            gst_buffer = sample.get_buffer()
            try:
                (ret, buffer_map) = gst_buffer.map(Gst.MapFlags.READ)
                if ret:
                    if self.wss:  # Would be useless to store frames while there is no conn.
                        if self.waiting:
                            self.waiting[0].unmap(self.waiting[1])
                        self.waiting = (gst_buffer, buffer_map)
                else:
                    self.set_nvs_state(NVSState.GstBufferFail)

            finally:
                pass

        return Gst.FlowReturn.OK


    @staticmethod
    async def send_data(wss: wssp, stuff: tuple):
        """
        Sends video data to a WS.
        """
        await wss.send(stuff[1].data)
        stuff[0].unmap(stuff[1])


    @route("nvs:state", thread=True)
    def get_nvs_state(self):
        """
        Gives you the current internal state of NVS.
        """
        return self.nvs_state


def run():
    compo = NVSComponent()
    compo.start()
