import asyncio
import logging
import ssl
from aiohttp import web
import json
from modules.MediaWebcam import MediaWebcam
import netifaces
import glob
from aiortc import RTCPeerConnection, RTCSessionDescription
from v4l2py import Device
from modules.Plugins import *
import sys

pcs = set()

webcam = MediaWebcam()
devices = []
global_plugins = [
    # FlipPlugin(),
    PortraitPaddingPlugin()
]

async def index(request):
    return web.FileResponse("./static/index.html")

async def get_devices(request):
    return web.json_response(devices)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    async def on_track(track):
        if track.kind == "video":
            webcam.addTrack(track, device=params["device"], plugins=global_plugins)
            await webcam.start()

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )

async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/get_devices", get_devices)
    app.router.add_post("/offer", offer)
    app.router.add_static("/", "./static")
    app.on_shutdown.append(on_shutdown)
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout)

    logging.info("Getting devices...")
    for glob_path in glob.glob("/dev/video*"):
        # Programs like OBS will use video0, so skip it
        if glob_path.endswith("video0"):
            continue
        with Device(glob_path) as device:
            devices.append({
                "name": device.info.card,
                "path": glob_path,
            })
    if len(devices) == 0:
        logging.error("No device found. Please check v4l2loopback driver status and rerun the script.")
        exit(1)
    logging.info("===============================================================")
    logging.info("Found %d devices:" % len(devices))
    for device in devices:
        logging.info("%s (%s)" % (device["name"], device["path"]))
    logging.info("===============================================================")
    
    logging.info("Starting RTCwebcam server...")
    logging.info("===============================================================")
    logging.info("You can connect to RTCwebcam from other devices at one of the following addresses:")
    for interface in netifaces.interfaces():
        iface_details = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in iface_details:
            for link in iface_details[netifaces.AF_INET]:
                if "addr" in link:
                    logging.info("https://%s:8080" % link["addr"])
    logging.info("===============================================================")
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain("./data/cert.cert")
    web.run_app(app, host='0.0.0.0', port=8080, ssl_context=ssl_context)
