import os

import gi

from air.utilities import component, ipc
from gi.repository import Gst


gi.require_version("Gst", "1.0")


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
    (1920, 1920),
]


async def functionWrap(func):
    await func()


def build_caps(w, h, fr) -> str:
    return "video/x-raw,width=" + str(w) + ",height=" + str(h) + ",framerate=" + str(int(fr)) + "/1,fromat=YUY2"


def build_pipeline(sset: int, framerate: int, address: str, port: str) -> str:
    global RESOLUTIONS
    # pipeline = "libcamerasrc camera-name=\"" + r"/base/soc/i2c0mux/i2c\@1/ov5647\@36" + "\""
    pipeline = "videotestsrc"
    pipeline += " ! capsfilter name=capper caps="
    pipeline += build_caps(RESOLUTIONS[sset][0], RESOLUTIONS[sset][1], framerate)
    pipeline += " ! vah264lpenc ! rtph264pay ! udpsink host=" + address + " port=" + port

    return pipeline


class NVSState(int):
    """
    Class representing the different states of NVSComponent.
    """

    GstInitFail: int = 0
    PipelineCreationFail: int = 1
    Unknown = 2
    Initialized: int = 3
    Streaming: int = 4


class NVSComponent(component.Component):
    """
    Component that handles streaming video from cam to WebSocket server.
    """

    NAME = "NVS"

    def __init__(self, ipc_node: ipc.IpcNode):
        super().__init__(ipc_node)

        self.nvs_state = NVSState.Unknown
        self.pipeline = None
        self.gst_pipeline_str: str = build_pipeline(
            4, 30, os.environ.get("STREAMING_BASE_HOST"), os.environ.get("STREAMING_BASE_PORT")
        )

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

        self.set_nvs_state(NVSState.Initialized)

    def set_nvs_state(self, val: int):
        """
        Sets value of the nvs_state. Used as guard to watch unproper behaviours on value updates.
        :param int val: Value of an NVSState.
        """
        if val < NVSState.Initialized:
            self.logger.warning("Warning, state:" + str(val))
        self.nvs_state = val

    def start(self):
        """
        Function used to start the module. It will set up different threads and schedule tasks, as well as running the GST pipeline.
        """
        if self.nvs_state != NVSState.Initialized:
            return False

        self.pipeline.set_state(Gst.State.PLAYING)
        self.set_nvs_state(NVSState.Streaming)

    def stop(self):
        """
        Stops the streaming. It will wait until all the threads are able to stop and do so to ensure proper releases.
        This means that the function might be blocking for an undetermined amount of time.
        """
        if self.nvs_state <= NVSState.Initialized:
            return

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        self.set_nvs_state(NVSState.Initialized)
