"""First-person controller run with a virtual uinput pad (simulated controller evidence, not a physical pad). The
pad's events reach the game through the kernel, SDL and Slate like a real controller's. Run it while the game runs
Tests/Auto/fp_pad.txt, which logs every press, held state and a sample of the player each second.

Usage: python3 fp_virtual_pad.py [xbox|ds4] [out log]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from virtual_pad import ABS, EV_ABS, Pad  # noqa: E402

KIND = sys.argv[1] if len(sys.argv) > 1 else "xbox"
OUT = open(sys.argv[2] if len(sys.argv) > 2 else "fp_virtual_pad_log.txt", "w")


def log(msg):
    line = f"{time.time():.3f} {msg}"
    print(line)
    OUT.write(line + "\n")
    OUT.flush()


def axis(pad, name, value):
    """value -1..1; Y axes are evdev-down-positive, so forward and look-up are negative."""
    lo, hi = pad.stick_range
    mid = (lo + hi) / 2 if lo == 0 else 0
    pad._emit(EV_ABS, ABS[name], int(mid + value * (hi - mid)))
    pad.sync()


def main():
    time.sleep(8)   # the game is up and fp_pad.txt is logging
    pad = Pad(KIND)
    log(f"pad created {KIND}")
    time.sleep(1.5)
    log("walk forward, stick at 90%")
    axis(pad, "Y", -0.9); time.sleep(1.5)
    log("sprint toggle (left stick press) while running")
    pad.press("l3", gap=0.0); time.sleep(1.5)
    log("stop: the toggled sprint ends")
    axis(pad, "Y", 0.0); time.sleep(0.8)
    axis(pad, "Y", -0.9); time.sleep(0.8)
    axis(pad, "Y", 0.0); time.sleep(0.5)
    log("look right, full tilt, 1 s; then up 0.5 s")
    axis(pad, "RX", 1.0); time.sleep(1.0); axis(pad, "RX", 0.0); time.sleep(0.3)
    axis(pad, "RY", -1.0); time.sleep(0.5); axis(pad, "RY", 0.0); time.sleep(0.5)
    log("resting stick inside the dead zone (10%)")
    axis(pad, "X", 0.1); axis(pad, "RX", 0.1); time.sleep(1.0); axis(pad, "X", 0.0); axis(pad, "RX", 0.0)
    log("jump (bottom face button)")
    pad.press("bottom", gap=1.2)
    log("crouch toggle (D-pad down) on, then off")
    pad.dpad(y=1, gap=0.8)
    pad.dpad(y=1, gap=0.8)
    log("pause (Options / Menu), then resume with the right face button (back)")
    pad.press("start", gap=0.8)
    pad.press("right", gap=0.8)
    log("disconnect while walking")
    axis(pad, "Y", -0.9); time.sleep(0.6)
    pad.close()
    time.sleep(2.0)
    log("reconnect a new pad and resume with the bottom face button (Resume is selected)")
    pad = Pad(KIND)
    time.sleep(1.0)
    pad.press("bottom", gap=1.0)
    axis(pad, "Y", -0.9); time.sleep(1.0); axis(pad, "Y", 0.0)
    time.sleep(1.0)
    pad.close()
    log("done")


main()
