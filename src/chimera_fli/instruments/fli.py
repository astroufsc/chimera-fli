# SPDX-FileCopyrightText: 2014-present William Schoenell <wschoenell@gmail.com>
# SPDX-License-Identifier: GPL-2.0-or-later
"""Driver for Finger Lakes Instrumentation CCD cameras and filter wheels.

Uses the python-FLI ctypes bindings to the FLI-provided library.
"""

import datetime as dt
import time

from chimera.core.lock import lock
from chimera.instruments.camera import CameraBase
from chimera.instruments.filterwheel import FilterWheelBase
from chimera.interfaces.camera import CameraFeature, CameraStatus, ReadoutMode

try:
    from FLI import USBCamera, USBFilterWheel
except ImportError:
    USBCamera = None
    USBFilterWheel = None


class FLI(CameraBase, FilterWheelBase):
    # Some of the config values were taken from the specs for the cam & CCD.
    __config__ = {
        "device": "USB",
        "camera_model": "Finger Lakes Instrumentation PL4240",
        "ccd_model": "E2V CCD42-40",
    }

    def __init__(self):
        CameraBase.__init__(self)
        FilterWheelBase.__init__(self)

        self.mode = 0
        self._supports = {
            CameraFeature.TEMPERATURE_CONTROL: True,
            CameraFeature.PROGRAMMABLE_GAIN: False,
            CameraFeature.PROGRAMMABLE_OVERSCAN: False,
            CameraFeature.PROGRAMMABLE_FAN: True,
            CameraFeature.PROGRAMMABLE_LEDS: True,
            CameraFeature.PROGRAMMABLE_BIAS_LEVEL: False,
        }

        self._adcs = {"12 bits": 0}

        self._binnings = {"1x1": 0, "2x2": 1, "3x3": 2, "9x9": 9}

        self._binning_factors = {"1x1": 1, "2x2": 2, "3x3": 3, "9x9": 9}

        self._setpoint = 0
        self._isfanning = False

        self.thecam = None
        self.thewheel = None
        self.info = {}
        self.width = None
        self.height = None
        self.imgsz = None
        self.pixel_width = None
        self.pixel_height = None
        self._readout_modes = {}

        self.last_frame_start_time = None
        self.last_frame_temp = None

    def __start__(self):
        if USBCamera is None:
            raise RuntimeError(
                "python-FLI is not installed or the FLI library was not found."
            )

        cams = USBCamera.find_devices()
        if not cams:
            self.log.critical("No FLI devices on USB bus!")
            raise RuntimeError("No FLI devices found on USB bus.")
        # Assume there's only one camera on the USB bus...
        self.thecam = cams[0]

        # The FLI API cannot read the fan speed, so always start chimera
        # with fans on and cooling stopped.
        self.start_fan()
        self.stop_cooling()

        # This provides the following dict pairs: 'serial_number',
        # 'hardware_rev', 'firmware_rev', 'pixel_size', 'array_area',
        # 'visible_area'.
        self.info = self.thecam.get_info()
        self.width, self.height, self.imgsz = self.thecam.get_image_size()
        self.pixel_width, self.pixel_height = self.info["pixel_size"]
        self.log.info(f"Camera: {self.info}")

        self._readout_modes = {}
        for mode, bin_id in self._binnings.items():
            vbin, hbin = [int(v) for v in mode.split("x")]
            readout_mode = ReadoutMode()
            readout_mode.mode = bin_id
            readout_mode.width = self.width // hbin
            readout_mode.height = self.height // vbin
            readout_mode.pixel_width = self.pixel_width * hbin
            readout_mode.pixel_height = self.pixel_height * vbin
            self._readout_modes[bin_id] = readout_mode

        # Filter wheel init
        wheels = USBFilterWheel.find_devices()
        if wheels:
            self.thewheel = wheels[0]
            self["filter_wheel_model"] = self.thewheel.model

    def __stop__(self):
        pass

    def get_pixel_size(self):
        return self.info["pixel_size"]

    def start_cooling(self, temp_c):
        self._setpoint = temp_c
        self.thecam.set_temperature(temp_c)
        return True

    def stop_cooling(self):
        # stop cooling by setting the temperature threshold to 60 degC
        self.thecam.set_temperature(60)
        return True

    def is_cooling(self):
        # find out by querying the power consumption of the camera cooler
        # (flagged as an "undocumented API function" by python-FLI)
        return self.thecam.get_cooler_power() != 0  # in Watts

    @lock
    def get_temperature(self):
        return self.thecam.get_temperature()

    def get_set_point(self):
        return self._setpoint

    def start_fan(self, rate=None):
        self._isfanning = True
        self.thecam.start_fan()
        return True

    def stop_fan(self):
        self._isfanning = False
        self.thecam.stop_fan()
        return True

    def is_fanning(self):
        # The FLI API cannot query the fan state, so track it locally.
        return self._isfanning

    def get_binnings(self):
        return self._binnings

    def get_adcs(self):
        return self._adcs

    def get_physical_size(self):
        return self.width, self.height

    def get_overscan_size(self, ccd=None):
        return 0, 0

    def get_readout_modes(self):
        return self._readout_modes

    def _expose(self, request):
        ftype = "normal"
        exptime = int(request["exptime"])
        self.log.debug(f"ImageRequest received: {request}")
        if request["type"] in ("bias", "dark"):
            ftype = "dark"
        if request["binning"]:
            hbin, vbin = [int(v) for v in request["binning"].split("x")]
        else:
            hbin, vbin = 1, 1
        # The bitdepth from the API seems buggy, leave it at its 16bit default.

        self.log.debug("Setting flush of the CCD to 1...")
        self.thecam.set_flushes(1)
        self.log.debug(f"Setting binning of the CCD to {hbin}x{vbin}...")
        self.thecam.set_image_binning(hbin, vbin)
        self.log.debug(f"Setting exposure time to {exptime} and frametype to {ftype}.")
        self.thecam.set_exposure(exptime * 1000, ftype)  # milliseconds

        self.expose_begin(request)
        # All set up, shoot. This method returns immediately.
        self.log.debug("Starting exposure...")
        self.thecam.start_exposure()

        status = CameraStatus.OK
        self.last_frame_start_time = dt.datetime.now(dt.UTC).replace(tzinfo=None)
        self.last_frame_temp = self.get_temperature()

        timestart = time.time()

        while self.is_exposing():
            self.log.debug("Exposing ...")

            # [ABORT POINT]
            if self.abort.is_set():
                status = CameraStatus.ABORTED
                break
            elif (time.time() - timestart) > 2.0 * exptime:
                self.log.warning("Exposure timed-out")
                status = CameraStatus.ABORTED
                break
            # this sleep is EXTREMELY important: without it, Python would get
            # stuck on this thread and abort would not work.
            time.sleep(1.0)

        self.expose_complete(request, status)
        return True

    def _readout(self, image_request):
        (mode, binning, top, left, width, height) = self._get_readout_mode_info(
            image_request["binning"], image_request["window"]
        )
        # readout
        self.readout_begin(image_request)

        img = self.thecam.fetch_image()

        image = self._save_image(
            image_request,
            img,
            {
                "frame_temperature": self.last_frame_temp,
                "frame_start_time": self.last_frame_start_time,
                "binning_factor": self._binning_factors[binning],
            },
        )

        self.readout_complete(image.url(), CameraStatus.OK)
        return image

    def is_exposing(self):
        return self.thecam.get_exposure_timeleft() != 0

    def supports(self, feature=None):
        return self._supports.get(feature, False)

    # Filter Wheel Control
    @lock
    def set_filter(self, f):
        return self.thewheel.set_filter_pos(self._get_filter_position(f))

    def get_filter(self):
        return self._get_filter_name(self.thewheel.get_filter_pos())
