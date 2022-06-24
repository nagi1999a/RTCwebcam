import asyncio
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack
from av import VideoFrame
import v4l2py.raw as v4l2
import fcntl

class MediaWebcamContext:
    def __init__(self, device, plugins):
        self.started = False
        self.device = device
        self.task = None
        self.format = v4l2.v4l2_format()
        self.format.type = v4l2.V4L2_BUF_TYPE_VIDEO_OUTPUT
        self.format.fmt.pix.field = v4l2.V4L2_FIELD_NONE
        self.format.fmt.pix.pixelformat  = v4l2.V4L2_PIX_FMT_YUYV
        self.params = v4l2.v4l2_streamparm()
        self.params.type = v4l2.V4L2_BUF_TYPE_VIDEO_OUTPUT
        self.params.parm.output.capability = v4l2.V4L2_CAP_TIMEPERFRAME
        self.params.parm.output.timeperframe.numerator = 1
        self.params.parm.output.timeperframe.denominator = 30
        self.plugins = plugins



class MediaWebcam:
    """
    A media sink that outputs to v4l2 loopback devices.
    Examples:
    """

    def __init__(self):
        self.__tracks = {}

    def addTrack(self, track, device, plugins=[]):
        """
        Add a track to be recorded.
        :param track: A :class:`aiortc.MediaStreamTrack`, only accept video track.
        :param device: The path of v4l2 device to use, ex. /dev/video0.
        """
        if track.kind != "video":
            raise ValueError("Only video tracks are supported")
        if device in self.__tracks:
            raise ValueError(f"Device {device} already occupied")
        
        self.__tracks[track] = MediaWebcamContext(device, plugins)

    async def start(self):
        """
        Start streaming.
        """
        for track, context in self.__tracks.items():
            if context.task is None:
                context.task = asyncio.ensure_future(self.__run_track(track, context))

    async def stop(self, device = None):
        """
        Stop streaming.
        :param device: The path of v4l2 device to use, ex. /dev/video0, default to stop all devices.
        """
        if device is None:
            for track, context in self.__tracks.items():
                if context.task is not None:
                    context.task.cancel()
                    context.task = None
            self.__tracks = {}
        else:
            track, context = self.__tracks[device]
            if context.task is not None:
                context.task.cancel()
                context.task = None
            del self.__tracks[device]

    def apply_plugins(self, frame, plugins):
        frame = frame.to_ndarray(format="bgr24")
        for plugin in plugins:
            frame = plugin.process(frame)
        return VideoFrame.from_ndarray(frame, format="bgr24")


    async def __run_track(self, track: MediaStreamTrack, context: MediaWebcamContext):
        try:
            frame = await track.recv()
        except MediaStreamError:
            return
        if not context.started:
            # adjust the output size to match the first frame
            if isinstance(frame, VideoFrame):
                if len(context.plugins) > 0:
                    frame = self.apply_plugins(frame, context.plugins)
                width, height, channels = frame.width, frame.height, 2
                context.format.fmt.pix.width = width
                context.format.fmt.pix.height = height
                context.format.fmt.pix.bytesperline = width * channels
                context.format.fmt.pix.sizeimage = width * height * channels
            context.started = True
            with open(context.device, 'wb') as device:
                fcntl.ioctl(device, v4l2.VIDIOC_S_FMT, context.format)
                fcntl.ioctl(device, v4l2.VIDIOC_S_PARM, context.params)
                while True:
                    frame = await track.recv()
                    if len(context.plugins) > 0:
                        frame = self.apply_plugins(frame, context.plugins)
                    frame = frame.to_ndarray(format="yuyv422")
                    device.write(frame.tobytes())