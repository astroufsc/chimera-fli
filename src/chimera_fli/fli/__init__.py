# SPDX-FileCopyrightText: 2012 Craig Wm. Versek, Yankee Environmental Systems, Inc.
# SPDX-License-Identifier: MIT
"""
FLI

Object-oriented ctypes interface for handling Finger Lakes Instrumentation
devices through the FLI-provided libfli shared library.

Vendored from https://github.com/cversek/python-FLI (MIT licensed, upstream
unmaintained since 2016) and ported to Python 3.

author:       Craig Wm. Versek, Yankee Environmental Systems
author_email: cwv@yesinc.com
"""

from .camera import USBCamera
from .filter_wheel import USBFilterWheel
from .focuser import USBFocuser

__all__ = ["USBCamera", "USBFilterWheel", "USBFocuser"]
