# SPDX-FileCopyrightText: 2014-present William Schoenell <wschoenell@gmail.com>
# SPDX-License-Identifier: GPL-2.0-or-later
"""Driver for Finger Lakes Instrumentation USB filter wheels.

Uses the vendored FLI ctypes bindings to the FLI-provided library.
"""

import time

from chimera.core.exceptions import ChimeraException
from chimera.core.lock import lock
from chimera.instruments.filterwheel import FilterWheelBase
from chimera.interfaces.filterwheel import InvalidFilterPositionException

# importing chimera_fli.fli loads libfli.so and fails if the FLI library
# is not installed on the system
try:
    from chimera_fli.fli import USBFilterWheel
    from chimera_fli.fli.lib import FLIError
except (ImportError, OSError, RuntimeError):
    USBFilterWheel = None
    FLIError = None

EPIPE = -32  # errno 32: USB pipe broken, device disconnected mid-transfer
RECONNECT_DELAYS = (1.0, 5.0, 10.0)  # seconds, one entry per reconnect attempt
MOVE_POLL_INTERVAL = 0.05  # seconds


class FLIFilterWheel(FilterWheelBase):
    __config__ = {
        # "USB" selects the first wheel found; set to a device name (e.g.
        # "FLI-0902") or serial number (e.g. "CL0163124") to pin one wheel
        # on buses with more than one device
        "device": "USB",
        # maximum time to wait for the wheel to finish a move. The FLI SDK
        # documents FLISetFilterPos as possibly returning while the motor is
        # still turning, so the move is polled until it stops.
        "move_timeout": 30,  # seconds
    }

    def __init__(self):
        FilterWheelBase.__init__(self)

        self.thewheel = None

    def __start__(self):
        if USBFilterWheel is None:
            raise RuntimeError(
                "The FLI library (libfli.so) was not found on this system."
            )

        wheels = USBFilterWheel.find_devices()
        if not wheels:
            self.log.critical("No FLI filter wheels on USB bus!")
            raise RuntimeError("No FLI filter wheels found on USB bus.")

        self.thewheel = self._select_wheel(wheels)
        self["filter_wheel_model"] = self.thewheel.model
        self.log.info(
            f"Filter wheel: {self.thewheel.model} "
            f"(device={self.thewheel.dev_name.decode()}, "
            f"serial={self.thewheel.get_serial_number()}, "
            f"fw=0x{self.thewheel.get_fw_revision():x}, "
            f"hw=0x{self.thewheel.get_hw_revision():x})"
        )

        nfilters = self.thewheel.get_filter_count()
        if len(self.get_filters()) != nfilters:
            self.log.warning(
                f"Filter wheel reports {nfilters} positions but 'filters' "
                f"configuration lists {len(self.get_filters())}."
            )

    def _select_wheel(self, wheels):
        wanted = str(self["device"])
        if wanted in ("", "USB"):
            # Assume there's only one filter wheel on the USB bus...
            return wheels[0]

        for wheel in wheels:
            if wanted in (wheel.dev_name.decode(), wheel.get_serial_number()):
                return wheel

        available = [f"{w.dev_name.decode()}/{w.get_serial_number()}" for w in wheels]
        raise RuntimeError(
            f"No FLI filter wheel matching device '{wanted}' "
            f"(available: {', '.join(available)})."
        )

    def __stop__(self):
        if self.thewheel is not None:
            self.thewheel.close()

    def _with_reconnect(self, fn):
        """Call fn(); on a USB disconnection (EPIPE) reopen the device with
        increasing delays and retry, giving up after len(RECONNECT_DELAYS)
        consecutive failures."""
        attempt = 0
        while True:
            try:
                return fn()
            except FLIError as e:
                if e.errno != EPIPE or attempt >= len(RECONNECT_DELAYS):
                    raise
                delay = RECONNECT_DELAYS[attempt]
                attempt += 1
                self.log.warning(
                    f"FLI USB disconnected (EPIPE), reconnect attempt "
                    f"{attempt}/{len(RECONNECT_DELAYS)} in {delay:.0f} s..."
                )
                time.sleep(delay)
                self.thewheel.reopen()

    def _wait_move(self):
        deadline = time.monotonic() + float(self["move_timeout"])
        while time.monotonic() < deadline:
            if self._with_reconnect(self.thewheel.get_steps_remaining) == 0:
                return
            time.sleep(MOVE_POLL_INTERVAL)
        raise ChimeraException(
            f"FLI filter wheel still moving after {self['move_timeout']} seconds."
        )

    @lock
    def set_filter(self, filter):
        filter_name = str(filter)

        if filter_name not in self.get_filters():
            raise InvalidFilterPositionException(f"Invalid filter {filter}.")

        try:
            old_filter = self.get_filter()
        except ChimeraException:
            # wheel position unknown (e.g. right after power-up)
            old_filter = None

        position = self._get_filter_position(filter_name)

        self.thewheel.lock()
        try:
            self._with_reconnect(lambda: self.thewheel.set_filter_pos(position))
            self._wait_move()
        finally:
            try:
                self.thewheel.unlock()
            except FLIError:
                pass

        self.filter_change(filter_name, old_filter)
        return True

    def get_filter(self):
        position = self._with_reconnect(self.thewheel.get_filter_pos)
        if position < 0:
            # The FLI API reports -1 when the position is unknown; without
            # this guard, _get_filter_name(-1) would silently return the
            # last filter of the list.
            raise ChimeraException(
                "FLI filter wheel position is unknown. Set a filter to home the wheel."
            )
        return self._get_filter_name(position)
