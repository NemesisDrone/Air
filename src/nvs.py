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

RESOLUTIONS = [
    (160,160),
    (320,320),
    (480,480),
    (576,576),
    (640,640),
    (768,768),
    (800,800),
    (864,864),
    (960,960),
    (1024,1024),
    (1152,1152),
    (1280,1280),
    (1440,1440),
    (1536,1536),
    (1600,1600),
    (1920,1920)
]


async def functionWrap(func):
    await func()


def build_caps(w, h, fr):
    return "video/x-raw,width=" + str(w) + ",height=" + str(h) + ",framerate=" + str(int(fr)) + "/1"


def build_pipeline(sset, framerate, quality):
    global RESOLUTIONS
    pipeline = "libcamerasrc name=src camera-name=\"" + r"/base/soc/i2c0mux/i2c\@1/ov5647\@36" + "\" ! "
    pipeline += build_caps(RESOLUTIONS[sset][0], RESOLUTIONS[sset][1], framerate)
    pipeline += " ! jpegenc name=enc quality=" + str(quality) + " ! appsink name=sink"

    return pipeline


class NVSState(int):
    """
    Class representing the different states of NVSComponent.
    """
    GstInitFail: int = 0
    PipelineCreationFail: int = 1
    SinkLookupFail: int = 2
    EncLookupFail: int = 3
    SrcLookupFail: int = 4
    GstBufferFail: int = 5
    Initialized: int = 6
    WaitingConnection: int = 7
    Streaming: int = 9
    Cleaning: int = 10
    Unknown: int = 11
    PendingStop: int = 12


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
        self.encoder = None
        self.src = None
        self.wss: wssp = None
        self.suspension_count: int = 0
        self._framerate: int = 10
        self._quality: int = 30
        self._resolution: int = 2
        self.gst_pipeline_str: str = build_pipeline(2, 10, 30)

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

        self.encoder = self.pipeline.get_by_name("enc")
        if not self.encoder:
            self.log("Failed to get pipeline's encoder.", ll.CRITICAL)
            self.set_nvs_state(NVSState.EncLookupFail)
            return

        self.src = self.pipeline.get_by_name("src")
        if not self.src:
            self.log("Failed to get pipeline's source.", ll.CRITICAL)
            self.set_nvs_state(NVSState.SrcLookupFail)
            return

        # Notify us when it receives a frame
        self.sink.set_property("emit-signals", True)
        # Set CB for new data
        self.sink.connect("new-sample", self._on_data_available)

        self.log("Initialized.", ll.INFO)
        self.set_nvs_state(NVSState.Initialized)


    def __del__(self):
        self.stop()
        Gst.deinit()


    def set_nvs_state(self, val: int):
        """
        Sets value of the nvs_state. Used as guard to watch unproper behaviours on value updates.
        :param int val: Value of an NVSState.
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

        # Release all the frames' data
        self.clear_waiting_data()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        self.log("Stopped.", ll.INFO)
        self.set_nvs_state(NVSState.Initialized)


    def clear_waiting_data(self):
        """
        Clears all the data put in the pending for sending.
        """
        if self.waiting:
            f, self.waiting = self.waiting, None
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
                        async with cn("ws://100.87.214.117:7000") as ws:  # [TODO] See what address to use
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
        Handles a connection to the server.
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
            # Remove con
            self.wss = None
            self.clear_waiting_data()
            self.log("Lost.", ll.INFO)
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
        Sends video data over a WS.
        """
        await wss.send(stuff[1].data)
        stuff[0].unmap(stuff[1])


    @route("nvs:state", thread=False, blocking=True)
    def get_nvs_state(self):
        """
        Gives you the current internal state of NVS.
        """
        return self.nvs_state


    def _waiting_lock(self):
        """
        Returns when no more functions are changing the pipeline data.
        """
        while self.suspension_count != 0:
            pass


    def _reconstruct_local_gst_pipeline(self):
        """
        Reconstructs the whole pipeline string used for GST.
        """
        self.gst_pipeline_str = build_pipeline(self._resolution, self._quality, self._framerate)


    def _update_pipeline_elements(self):
        """
        Updates the pipeline's elements' data. Meant to be used when the pipeline is already setup.
        """
        global RESOLUTIONS

        caps: str = build_caps(RESOLUTIONS[self._resolution][0], RESOLUTIONS[self._resolution][1], self._framerate)
        self.encoder.set_property("quality", self._quality)
        self.src.set_property("caps", Gst.Caps.from_string(caps))


    def _pipeline_locking_set(self, name: str, val: int):
        """
        Change the value of an attribute that must block the pipeline.
        :param str name: The attribute's name
        :param int val: Value to assign to the attribute.
        """

        # 0: not responsible & no pipeline running, 1: responsible, no pipeline running, 2: pipeline might be
        # running, not responsible, 3: responsible and pipeline running.
        responsible: int = int(self.suspension_count == 0) + int(self.nvs_state == NVSState.Streaming)*2

        if responsible == 3:
            self.pipeline.set_state(Gst.State.PAUSED)

        self.suspension_count += 1
        # Assign the corresponding value.
        setattr(self, name, val)
        self.suspension_count -= 1

        if responsible%2 == 1:
            self._waiting_lock()
            self._reconstruct_local_gst_pipeline()
            self._update_pipeline_elements()

        if responsible == 3:
            self.pipeline.set_state(Gst.State.PLAYING)


    @route("nvs:ctl:resolution", thread=False, blocking=True)
    def set_resolution(self, pl: int):
        """
        Change the resolution of the camera stream.
        :param int pl: The index of the new resolution to use. Must be within [0; 16].
        """
        if pl < 0 or pl > 16:
            return False

        self._pipeline_locking_set("_resolution", pl)
        return True


    @route("nvs:ctl:framerate", thread=False, blocking=True)
    def set_framerate(self, pl: int):
        """
        Change the frame rate of the camera stream.
        :param int pl: The new frame rate to use. Must be within [0; 30].
        """
        # From 1 to 30 max.
        if pl < 0 or pl > 30:
            return False

        self._pipeline_locking_set("_framerate", pl)
        return True


    @route("nvs:ctl:quality", thread=False, blocking=True)
    def set_quality(self, pl: int):
        """
        Change the JPEG quality level.
        :param int pl: The new quality of encoding to use. Must be within [0; 60].
        """
        # From 1 to 60 max.
        if pl < 0 or pl > 60:
            return False

        self._pipeline_locking_set("_quality", pl)


def run():
    compo = NVSComponent()
    compo.start()
