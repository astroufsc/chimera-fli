# SPDX-FileCopyrightText: 2014-present William Schoenell <wschoenell@gmail.com>
# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests for FLIFilterWheel using a fake wheel (no hardware/libfli)."""

import pytest
from chimera.core.exceptions import ChimeraException
from chimera.interfaces.filterwheel import InvalidFilterPositionException

from chimera_fli.instruments import flifilterwheel as mod
from chimera_fli.instruments.flifilterwheel import FLIFilterWheel


class FakeFLIError(Exception):
    def __init__(self, msg="", errno=None):
        super().__init__(msg)
        self.errno = errno


class FakeWheel:
    model = "CenterLine Filter Wheel"

    def __init__(self, dev_name=b"FLI-0902", serial="CL0163124", count=5):
        self.dev_name = dev_name
        self.serial = serial
        self.count = count
        self.pos = 0
        self.epipe_failures = 0  # calls to fail with EPIPE before succeeding
        self.steps_remaining = 0
        self.reopens = 0
        self.locks = 0
        self.closed = False

    def _maybe_fail(self):
        if self.epipe_failures > 0:
            self.epipe_failures -= 1
            raise FakeFLIError("Broken pipe", errno=-32)

    def get_serial_number(self):
        return self.serial

    def get_fw_revision(self):
        return 0x10

    def get_hw_revision(self):
        return 0x01

    def get_filter_count(self):
        return self.count

    def get_filter_pos(self):
        self._maybe_fail()
        return self.pos

    def set_filter_pos(self, pos):
        self._maybe_fail()
        self.pos = pos

    def get_steps_remaining(self):
        return self.steps_remaining

    def lock(self):
        self.locks += 1

    def unlock(self):
        self.locks -= 1

    def close(self):
        self.closed = True

    def reopen(self):
        self.reopens += 1


@pytest.fixture
def fake(monkeypatch):
    wheel = FakeWheel()
    monkeypatch.setattr(
        mod,
        "USBFilterWheel",
        type(
            "FakeUSBFilterWheel",
            (),
            {"find_devices": staticmethod(lambda: [wheel])},
        ),
    )
    monkeypatch.setattr(mod, "FLIError", FakeFLIError)
    monkeypatch.setattr(mod, "RECONNECT_DELAYS", (0.0, 0.0, 0.0))
    return wheel


@pytest.fixture
def events(monkeypatch):
    fired = []
    monkeypatch.setattr(
        FLIFilterWheel,
        "filter_change",
        lambda self, new, old: fired.append((new, old)),
        raising=False,
    )
    return fired


@pytest.fixture
def fw(fake, events):
    fw = FLIFilterWheel()
    fw["filters"] = "U B V R I"
    fw.__start__()
    return fw


def test_start_reads_model(fw, fake):
    assert fw["filter_wheel_model"] == "CenterLine Filter Wheel"


def test_set_filter_moves_and_fires_event(fw, fake, events):
    assert fw.set_filter("B") is True
    assert fake.pos == 1
    assert fw.get_filter() == "B"
    assert events == [("B", "U")]
    assert fake.locks == 0  # locked and unlocked around the move


def test_set_filter_invalid_name_raises(fw):
    with pytest.raises(InvalidFilterPositionException):
        fw.set_filter("NOSUCHFILTER")


def test_get_filter_unknown_position_raises(fw, fake):
    fake.pos = -1
    with pytest.raises(ChimeraException):
        fw.get_filter()


def test_set_filter_with_unknown_start_position(fw, fake, events):
    fake.pos = -1
    assert fw.set_filter("R") is True
    assert events == [("R", None)]


def test_reconnect_on_epipe(fw, fake):
    fake.epipe_failures = 2
    assert fw.set_filter("V") is True
    assert fake.reopens == 2
    assert fake.pos == 2


def test_reconnect_gives_up(fw, fake):
    fake.epipe_failures = 99
    with pytest.raises(FakeFLIError):
        fw.set_filter("V")
    assert fake.reopens == len(mod.RECONNECT_DELAYS)


def test_move_timeout(fw, fake):
    fake.steps_remaining = 1  # wheel never stops
    fw["move_timeout"] = 0
    with pytest.raises(ChimeraException):
        fw.set_filter("I")
    assert fake.locks == 0  # unlocked even on failure


def test_device_pinning_by_serial(fake, events):
    fw = FLIFilterWheel()
    fw["filters"] = "U B V R I"
    fw["device"] = "CL0163124"
    fw.__start__()
    assert fw["filter_wheel_model"] == "CenterLine Filter Wheel"


def test_device_pinning_no_match(fake, events):
    fw = FLIFilterWheel()
    fw["filters"] = "U B V R I"
    fw["device"] = "NOPE-1234"
    with pytest.raises(RuntimeError):
        fw.__start__()


def test_stop_closes_device(fw, fake):
    fw.__stop__()
    assert fake.closed
