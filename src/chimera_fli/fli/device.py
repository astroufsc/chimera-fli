"""
FLI.device.py

Object-oriented base interface for handling FLI USB devices

author:       Craig Wm. Versek, Yankee Environmental Systems
author_email: cwv@yesinc.com
"""

__author__ = "Craig Wm. Versek"
__date__ = "2012-08-16"


import ctypes
from ctypes import POINTER, byref, c_char_p, c_long, c_size_t

from .lib import (
    FLI_INVALID_DEVICE,
    FLIDOMAIN_USB,
    FLIError,
    FLILibrary,
    flidev_t,
    flidomain_t,
)

###############################################################################
DEBUG = False
BUFFER_SIZE = 64


###############################################################################
class USBDevice(object):
    """base class for all FLI USB devices"""

    # load the DLL
    _libfli = FLILibrary.getDll(debug=DEBUG)
    _domain = flidomain_t(FLIDOMAIN_USB)

    def __init__(self, dev_name, model):
        self.dev_name = dev_name
        self.model = model
        # open the device
        self._dev = flidev_t(FLI_INVALID_DEVICE)
        self._libfli.FLIOpen(byref(self._dev), dev_name, self._domain)

    def __del__(self):
        self.close()

    def close(self):
        """closes the device handle; safe to call more than once"""
        if self._dev.value == FLI_INVALID_DEVICE:
            return
        try:
            self._libfli.FLIClose(self._dev)
        finally:
            self._dev = flidev_t(FLI_INVALID_DEVICE)

    def reopen(self):
        """closes any stale handle and opens the device again, e.g. after a
        USB disconnection"""
        try:
            self.close()
        except FLIError:
            pass  # the stale handle may fail to close after a disconnect
        self._dev = flidev_t(FLI_INVALID_DEVICE)
        self._libfli.FLIOpen(byref(self._dev), self.dev_name, self._domain)

    def lock(self):
        """acquires an exclusive (cross-process) lock on the device"""
        self._libfli.FLILockDevice(self._dev)

    def unlock(self):
        """releases the exclusive lock on the device"""
        self._libfli.FLIUnlockDevice(self._dev)

    def get_serial_number(self):
        serial = ctypes.create_string_buffer(BUFFER_SIZE)
        self._libfli.FLIGetSerialString(self._dev, serial, c_size_t(BUFFER_SIZE))
        return serial.value.decode()

    def get_fw_revision(self):
        rev = c_long()
        self._libfli.FLIGetFWRevision(self._dev, byref(rev))
        return rev.value

    def get_hw_revision(self):
        rev = c_long()
        self._libfli.FLIGetHWRevision(self._dev, byref(rev))
        return rev.value

    @classmethod
    def find_devices(cls):
        """locates all FLI USB devices in the current domain and returns a
        list of USBDevice objects"""

        tmplist = POINTER(c_char_p)()
        cls._libfli.FLIList(cls._domain, byref(tmplist))  # allocates memory
        devs = []
        # process list only if it is not NULL
        if tmplist:
            i = 0
            while tmplist[i]:  # process members only if they are not NULL
                # FLIList returns bytes; FLIOpen needs the raw (bytes) dev_name
                dev_name, model = tmplist[i].split(b";")
                devs.append(
                    cls(dev_name=dev_name, model=model.decode())
                )  # create device objects
                i += 1
            cls._libfli.FLIFreeList(tmplist)  # frees memory
        # finished processing list
        return devs

    @classmethod
    def locate_device(cls, serial_number):
        """locates the FLI USB devices in the current domain that matches the
        'serial_number' string

        returns None if no match is found

        raises FLIError if more than one device matching the serial_number
               is found, i.e., there is a conflict
        """
        dev_match = None
        devs = cls.find_devices()
        for dev in devs:
            dev_sn = dev.get_serial_number()
            if dev_sn == serial_number:  # match found
                if dev_match is None:  # first match
                    dev_match = dev
                else:  # conflict
                    msg = (
                        "Device Conflict: there are more than one devices matching the serial_number '%s'"
                        % serial_number
                    )
                    raise FLIError(msg)
        return dev_match


###############################################################################
#  TEST CODE
###############################################################################
if __name__ == "__main__":
    devs = USBDevice.find_devices()
