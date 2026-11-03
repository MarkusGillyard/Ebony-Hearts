"""Virtual Xbox 360-style gamepad through Linux uinput, for automated controller tests of a running game.

Usage: python3 virtual_pad.py <scenario> [args]
  scenario "menu-and-fight": navigates title -> Versus CPU -> fight with pad inputs, then quits the game via the menus.
  scenario "disconnect": presses through to a match, destroys the device mid-fight (disconnect), waits, recreates it
                         (reconnect), presses confirm on the new device to take the slot back, fights, then quits.
The device exists only while this script runs. Results are virtual-controller evidence, not physical-pad testing.
"""
import ctypes
import fcntl
import os
import struct
import sys
import time

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_ABSBIT = 0x40045567
UI_DEV_SETUP = 0x405C5503
UI_ABS_SETUP = 0x401C5504
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
BTN = {"A": 0x130, "B": 0x131, "X": 0x133, "Y": 0x134, "LB": 0x136, "RB": 0x137, "BACK": 0x13A, "START": 0x13B,
       "GUIDE": 0x13C, "LS": 0x13D, "RS": 0x13E}
ABS = {"X": 0x00, "Y": 0x01, "Z": 0x02, "RX": 0x03, "RY": 0x04, "RZ": 0x05, "HAT0X": 0x10, "HAT0Y": 0x11}


class Pad:
    def __init__(self, name="Ebony Hearts Test Pad"):
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_ABS)
        for code in BTN.values():
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, code)
        ranges = {"X": (-32768, 32767), "Y": (-32768, 32767), "RX": (-32768, 32767), "RY": (-32768, 32767),
                  "Z": (0, 255), "RZ": (0, 255), "HAT0X": (-1, 1), "HAT0Y": (-1, 1)}
        for axis, (lo, hi) in ranges.items():
            fcntl.ioctl(self.fd, UI_SET_ABSBIT, ABS[axis])
            fcntl.ioctl(self.fd, UI_ABS_SETUP, struct.pack("HHiiiiii", ABS[axis], 0, 0, lo, hi, 16 if hi > 255 else 0, 128 if hi > 255 else 0, 0))
        # Microsoft Xbox 360 USB ids so SDL applies its standard gamepad mapping.
        setup = struct.pack("HHHH80sI", 0x03, 0x045E, 0x028E, 0x0110, name.encode()[:79], 0)
        fcntl.ioctl(self.fd, UI_DEV_SETUP, setup)
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(1.5)   # let the system and SDL notice the new device

    def _emit(self, etype, code, value):
        now = time.time()
        os.write(self.fd, struct.pack("llHHi", int(now), int((now % 1) * 1e6), etype, code, value))

    def sync(self):
        self._emit(EV_SYN, 0, 0)

    def press(self, button, hold=0.08, gap=0.2):
        self._emit(EV_KEY, BTN[button], 1)
        self.sync()
        time.sleep(hold)
        self._emit(EV_KEY, BTN[button], 0)
        self.sync()
        time.sleep(gap)

    def dpad(self, x=0, y=0, hold=0.1, gap=0.2):
        self._emit(EV_ABS, ABS["HAT0X"], x)
        self._emit(EV_ABS, ABS["HAT0Y"], y)
        self.sync()
        time.sleep(hold)
        self._emit(EV_ABS, ABS["HAT0X"], 0)
        self._emit(EV_ABS, ABS["HAT0Y"], 0)
        self.sync()
        time.sleep(gap)

    def stick(self, x, seconds):
        self._emit(EV_ABS, ABS["X"], int(x * 32767))
        self.sync()
        time.sleep(seconds)
        self._emit(EV_ABS, ABS["X"], 0)
        self.sync()

    def close(self):
        fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        os.close(self.fd)


def to_fight(pad):
    pad.press("A")            # title
    time.sleep(1.0)
    pad.press("A")            # Versus CPU
    time.sleep(0.6)
    pad.press("A")            # Wren
    pad.press("A")            # opponent
    pad.press("A")            # difficulty/side -> fight
    time.sleep(6.0)


def fight_inputs(pad):
    pad.stick(1.0, 0.6)       # walk forward with the analog stick
    for _ in range(3):
        pad.press("A", gap=0.1)   # light string
    pad.press("B", gap=0.4)       # heavy
    pad.press("RB", hold=0.8)     # block hold
    pad.press("X", gap=0.6)       # grab
    pad.press("LB", gap=0.6)      # dodge
    pad.press("Y", gap=0.8)       # special


def quit_from_main(pad):
    pad.press("B")            # main menu: Back opens the quit confirmation
    time.sleep(0.5)
    pad.press("A")            # Quit


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "menu-and-fight"
    pad = Pad()
    try:
        if scenario == "menu-and-fight":
            to_fight(pad)
            fight_inputs(pad)
            pad.press("START")        # pause
            time.sleep(0.5)
            pad.dpad(y=-1)            # wrap to Main Menu
            pad.press("A")
            time.sleep(1.0)
            quit_from_main(pad)
        elif scenario == "disconnect":
            to_fight(pad)
            fight_inputs(pad)
            pad.close()
            print("pad destroyed (disconnect)", flush=True)
            time.sleep(4.0)
            pad = Pad("Ebony Hearts Test Pad 2")
            print("pad recreated (reconnect)", flush=True)
            time.sleep(1.0)
            pad.press("A")            # take over the disconnected player's slot
            time.sleep(1.0)
            pad.press("START")        # pause menu from the new device
            pad.press("START")        # resume
            fight_inputs(pad)
            pad.press("START")        # pause
            time.sleep(0.5)
            pad.dpad(y=-1)            # wrap to Main Menu
            pad.press("A")
            time.sleep(1.0)
            quit_from_main(pad)
    finally:
        try:
            pad.close()
        except OSError:
            pass
    print("virtual pad scenario done:", scenario)


main()
