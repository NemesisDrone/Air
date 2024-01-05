from utilities import component, ipc

import gi
import threading
import asyncio as aio
from websockets import exceptions as wssexcept
from websockets.server import WebSocketServerProtocol as wssp
from websockets.client import connect as cn

gi.require_version('Gst', '1.0')
gi.require_version("GstVideo", "1.0")
from gi.repository import GObject, Gst, GstVideo

RESOLUTIONS = [
    (160, 160),
    (320, 320),
    (480, 480),
    (576, 576),
    (640, 640),
    (768, 768),
    (800, 800),
    (864, 864),
    (960, 960),
    (1024, 1024),
    (1152, 1152),
    (1280, 1280),
    (1440, 1440),
    (1536, 1536),
    (1600, 1600),
    (1920, 1920)
]


async def functionWrap(func):
    await func()


def build_caps(w, h, fr) -> str:
    return "video/x-raw,width=" + str(w) + ",height=" + str(h) + ",framerate=" + str(int(fr)) + "/1,fromat=YUY2"


def build_pipeline(sset, framerate, quality) -> str:
    global RESOLUTIONS
    pipeline = "libcamerasrc camera-name=\"" + r"/base/soc/i2c0mux/i2c\@1/ov5647\@36" + "\""
    pipeline += " ! capsfilter name=capper caps="
    pipeline += build_caps(RESOLUTIONS[sset][0], RESOLUTIONS[sset][1], framerate)
    pipeline += " ! jpegenc name=enc idct-method=1 quality=" + str(quality) + " ! appsink name=sink"

    return pipeline


class NVSState(int):
    """
    Class representing the different states of NVSComponent.
    """
    GstInitFail: int = 0
    PipelineCreationFail: int = 1
    SinkLookupFail: int = 2
    GstBufferFail: int = 3
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

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        self.nvs_state = NVSState.Unknown
        self.thread: threading.Thread = None
        self.loop: aio.AbstractEventLoop = None
        self.waiting: list = []
        self.pipeline = None
        self.sink = None
        self.wss: wssp = None
        self.suspension_count: int = 0
        self.gst_pipeline_str: str = build_pipeline(0, 10, 30)

        if not Gst.init_check(None):  # init gstreamer
            self.logger.critical("Could not initialize GStreamer.", self.NAME)
            self.set_nvs_state(NVSState.GstInitFail)
            return

        # Setting GST's logging level to output.
        # see https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html
        # Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)

        self.pipeline = Gst.parse_launch(self.gst_pipeline_str)
        if not self.pipeline:
            self.logger.critical("Could not create pipeline.", self.NAME)
            self.set_nvs_state(NVSState.PipelineCreationFail)
            return

        self.sink = self.pipeline.get_by_name("sink")
        if not self.sink:
            self.logger.critical("Could not find pipeline sink.", self.NAME)
            self.set_nvs_state(NVSState.SinkLookupFail)
            return

        # Notify us when it receives a frame
        self.sink.set_property("emit-signals", True)
        # Set CB for new data
        self.sink.connect("new-sample", self._on_data_available)

        self.set_nvs_state(NVSState.Initialized)

    def set_nvs_state(self, val: int):
        """
        Sets value of the nvs_state. Used as guard to watch unproper behaviours on value updates.
        :param int val: Value of an NVSState.
        """
        if int(val) < int(NVSState.Initialized):
            self.logger.warning("Warning, state:" + str(val))
        self.nvs_state = val

    def start(self) -> bool:
        """
        Function used to start the module. It will set up different threads and schedule tasks, as well as running the GST pipeline.
        """

        def loop_setter(loop):
            """
            Used to start a thread with an Asyncio event loop running within.
            """
            aio.set_event_loop(loop)
            loop.run_forever()

        if self.nvs_state != NVSState.Initialized:
            return False

        self.loop = aio.new_event_loop()
        aio.set_event_loop(self.loop)
        self.thread = threading.Thread(target=loop_setter, args=(self.loop,))
        self.thread.start()
        aio.run_coroutine_threadsafe(functionWrap(self._start_serving), self.loop)

        return True

    def stop(self):
        """
        Stops the streaming. It will wait until all the threads are able to stop and do so to ensure proper releases.
        This means that the function might be blocking for an undetermined amount of time.
        """
        self.set_nvs_state(NVSState.Cleaning)

        # Close connection if there is one.
        if self.wss:
            self.set_nvs_state(NVSState.PendingStop)
            while self.nvs_state != NVSState.Initialized:
                pass

        # Make the thread join.
        if self.thread:
            self.thread.join()

        # Release all the frames' data
        self.clear_waiting_data()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        self.set_nvs_state(NVSState.Initialized)

        Gst.deinit()

    def clear_waiting_data(self):
        """
        Clears all the data put in the pending for sending.
        """
        tmp, self.waiting = self.waiting, []
        while tmp:
            f = tmp.pop(0)
            f[0].unmap(f[1])

    async def _start_serving(self):
        """
        Starts serving camera stream to the server. It will try to (re)connect to the server until the component is
        stopped.
        """
        try:
            while self.nvs_state != NVSState.PendingStop:
                try:
                    self.set_nvs_state(NVSState.WaitingConnection)
                    try:
                        async with cn("ws://100.87.214.117:7000") as ws:  # [TODO] Change to the right address.
                            await self._on_connection(ws)
                    except BaseException:
                        pass
                finally:
                    pass
        finally:
            pass

        self.set_nvs_state(NVSState.Initialized)

    async def _on_connection(self, wss: wssp):
        """
        Handles a connection to the server.
        """
        self.pipeline.set_state(Gst.State.PLAYING)
        self.set_nvs_state(NVSState.Streaming)
        self.logger.info("Connection established.", self.NAME)
        self.wss = wss

        try:
            while True:
                # Push the current frames.
                while self.waiting:
                    # We need to do it synchronously and not edit the scheduled queue's 1st in the meantime to avoid
                    # corruptions.
                    current: tuple = self.waiting.pop(0)
                    pending: tuple = (aio.create_task(self.send_data(self.wss, current)),)
                    while pending:
                        _, pending = await aio.wait(pending, return_when=aio.FIRST_COMPLETED)
        except wssexcept.ConnectionClosed:
            # Remove con
            self.wss = None
            self.clear_waiting_data()
            self.logger.info("Connection closed.", self.NAME)
            if self.nvs_state != NVSState.PendingStop:
                self.nvs_state = NVSState.WaitingConnection

        self.pipeline.set_state(Gst.State.NULL)

    def _on_data_available(self, appsink):
        """
        Handles incoming data from a GST pipeline and buffers it. If new data is available but the previous has not
        been sent, the previous is dropped and the new one will be scheduled for sending.
        """
        sample = appsink.emit("pull-sample")

        if sample:
            gst_buffer = sample.get_buffer()
            try:
                (ret, buffer_map) = gst_buffer.map(Gst.MapFlags.READ)
                if ret:
                    if self.wss:  # Would be useless to store frames while there is no conn.
                        if len(self.waiting) < 5:  # Frame not scheduled as there's no more space.
                            self.waiting.append((gst_buffer, buffer_map,))
                        else:
                            # Just release this frame.
                            gst_buffer.unmap(buffer_map)
                else:
                    self.set_nvs_state(NVSState.GstBufferFail)

            finally:
                pass

        return Gst.FlowReturn.OK

    @staticmethod
    async def send_data(wss: wssp, stuff: tuple):
        """
        Sends video data over a WS.
        """
        await wss.send(stuff[1].data)
        stuff[0].unmap(stuff[1])

    """
    TODO: @nicolas maybe you can refacto this by storing and updating the internal state as key/value in the redis db
    and update the value when you update the internal state. This would avoid sending blocking requests and instead
    we would be able to easily get the state from the redis db.
    """

    @ipc.Route(["nvs:state"], concurrent=False).decorator
    def get_nvs_state(self) -> int:
        """
        Gives you the current internal state of NVS.
        """
        return self.nvs_state
