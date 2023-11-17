from utilities import component
from utilities.ipc import route
from utilities.ipc import LogLevels as ll

import dataclasses
import gi
import asyncio as aio
from websockets import exceptions as wssexcept
from websockets.client import connect as cn

import threading

gi.require_version('Gst', '1.0')
gi.require_version("GstVideo", "1.0")
from gi.repository import GObject, Gst, GstVideo

import os


COMMON_PIPELNE = "videotestsrc ! videoconvert ! openh264enc ! video/x-h264,profile=baseline,stream-format=byte-stream ! appsink name=sink"


def functionWrap(func, object, *args):
    func(tuple(object) + args)


@dataclasses.dataclass
class NVSState:
    """
    @brief Class representing the different states of NVSComponent.
    """
    GstInitFail: int = 0
    PipelineCreationFail: int = 1
    SinkLookupFail: int = 2
    Initialized: int = 3
    WaitingConnection: int = 4
    Streaming: int = 5
    Cleaning: int = 6
    Unknown: int = 7
    PendingStop: int = 8

async def fakee(compo):
    await compo._start_serving()


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
        self.thread = None
        self.loop = None

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
        def loop_setter(loop):
            aio.set_event_loop(loop)
            loop.run_forever()

        if self.nvs_state != NVSState.Initialized:
            return

        self.loop = aio.new_event_loop()
        aio.set_event_loop(self.loop)
        self.thread = threading.Thread(target=loop_setter, args=(self.loop,))
        self.thread.start()

        aio.run_coroutine_threadsafe(fakee(self), self.loop)
        #self.loop.call_soon_threadsafe(self.loop.stop)


        """blocking_coro = aio.to_thread(self._start_serving)
        task = aio.create_task(blocking_coro)"""

        while self.nvs_state != NVSState.WaitingConnection:
            pass

        self.log("[NVS] Started.", ll.INFO)

        """while self.loop.is_running():
            pass"""

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
        print("Serving!", flush=True)
        try:
            self.pipeline.set_state(Gst.State.PLAYING)
            self.log("[NVS] Starting WS serving.", ll.INFO)

            while self.nvs_state != NVSState.PendingStop:
                print("Waiting...")
                try:
                    self.nvs_state = NVSState.WaitingConnection
                    async with cn("ws://127.0.0.1:7000") as ws:
                        await self._on_connection(ws)

                finally:
                    self.pipeline.set_state(Gst.State.NULL)

        finally:
            pass

        self.log("[NVS] WS serving stopped.", ll.INFO)
        self.nvs_state = NVSState.Initialized

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
    compo = NVSComponent()
    compo.start()
