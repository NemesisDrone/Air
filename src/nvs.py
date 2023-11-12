from utilities import component
from utilities.ipc import route
from utilities.ipc import LogLevels as ll

import dataclasses
import gi
import asyncio as aio
from websockets.exceptions import exceptions as wssexcept
from websockets.client import connect as cn

gi.require_version('Gst', '1.0')
gi.require_version("GstVideo", "1.0")
from gi.repository import GObject, Gst, GstVideo




COMMON_PIPELNE = "v4l2src"
                 " ! videoconvert"
                 " ! v4l2h264enc"
                 " ! video/x-h264,profile=baseline,stream-format=byte-stream"
                 " ! appsink name=sink"


def functionWrap(func, object, *args):
    func(tuple(object) + args)


@dataclasses.dataclass
class NVSState:
    """
    @brief Class representing the different states of NVSComponent.
    """
    GstInitFail: 0
    PipelineCreationFail: 1
    SinkLookupFail: 2
    Initialized: 3
    WaitingConnection: 4
    Streaming: 5
    Cleaning: 6
    Unknown: 7
    PendingStop: 8


class NVSComponent(component.Component):
    """
    Component that handles streaming video from cam to WebSocket server.
    """
    NAME = "NVS"

    pipeline = None
    sink = None
    wss = None
    waiting = None

    def __init__(self):
        super().__init__()

        self.nvs_state = NVSState.Unknown

        if not Gst.init_check(None): # init gstreamer
            self.log("[NVS] GST init failed!", ll.CRITICAL)
            self.nvs_state = NVSState.GstInitFail
            return

        # Setting GST's logging level to output.
        # see https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html
        # Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)

        global COMMON_PIPELNE
        self.pipeline = Gst.parse_launch(COMMON_PIPELNE)
        if not self.pipeline:
            self.log("[NVS] Could not create pipeline.", ll.CRITICAL)
            self.nvs_state = NVSState.PipelineCreationFail
            return

        self.sink = self.pipeline.get_by_name("sink")
        if not self.sink:
            self.log("[NVS] Failed to get pipeline's sink.", ll.CRITICAL)
            self.nvs_state = NVSState.SinkLookupFail
            return

        # Notify us when it receives a frame
        self.sink.set_property("emit-signals", True)
        # Set CB for new data
        self.sink.connect("new-sample", self._on_data_available)

        self.log("[NVS] Initialized.", ll.INFO)
        self.nvs_state = NVSState.Initialized

    def start(self):
        if self.nvs_state != NVSState.Initialized:
            return

        aio.run(self._start_serving(self))
        self.log("[NVS] Started.", ll.INFO)

    def stop(self):
        self.nvs_state = NVSState.Cleaning

        # Close connection if there is one.
        if self.wss:
            self.nvs_state = NVSState.PendingStop
            self.wss.close()
            self.wss = None
            while self.nvs_state != NVSState.Initialized:
                pass

        # Release all the frames' data
        self.clear_waiting_data()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        self.log("[NVS] Stopped.", ll.INFO)
        self.nvs_state = NVSState.Initialized

    def clear_waiting_data(self):
        """
        Clears all the data put in the pending list for sending.
        """
        f, self.waiting = self.waiting, None
        f[0].unmap(f[1])

    async def _start_serving(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self.log("[NVS] Starting WS serving.", ll.INFO)

        while self.nvs_state != NVSState.PendingStop:
            try:
                self.nvs_state = NVSState.WaitingConnection
                async with cn("ws://localhost:8000") as ws:
                    await self._on_connection(ws)

            finally:
                self.pipeline.set_state(Gst.State.NULL)

    async def _on_connection(self, wss):
        """
        Handles connection to a WS.
        """
        self.nvs_state = NVSState.Streaming
        self.log("[NVS] WS Connection opened.", ll.INFO)
        self.wss = wss
        try:
            while True:
                # Push all the frames.
                while self.waiting:
                    await self.send_data(wss, self.waiting)
                    self.waiting = None
        except wssexcept.ConnectionClosed:
            # Remove con
            self.wss = None
            self.clear_waiting_data()
            self.log("[NVS] WS Connection closed.", ll.INFO)
            if self.nvs_state != NVSState.PendingStop:
                self.nvs_state = NVSState.WaitingConnection

    def _on_data_available(self, appsink):
        """
        Handles incoming data from a GST pipeline.
        """
        sample = appsink.emit("pull-sample")

        if sample:
            gst_buffer = sample.get_buffer()
            try:
                (ret, buffer_map) = gst_buffer.map(Gst.MapFlags.READ)
                if self.wss:  # Would be useless to store frames while there is no conn.
                    if self.waiting:
                        self.waiting[0].unmap(self.waiting[1])
                    self.waiting = tuple(gst_buffer, buffer_map)

            finally:
                pass

        return Gst.FlowReturn.OK

    @staticmethod
    async def send_data(wss, stuff):
        """
        Sends video data to a WS.
        """
        await wss.send(stuff[1].data)
        stuff[0].unmap(stuff[1])

    @route("nvs:state", thread=True)
    def get_nvs_state(self):
        return self.nvs_state

def run():
    NVSComponent().start()
