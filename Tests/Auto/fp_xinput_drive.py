"""Drives the first-person game window with real X11 input (XTest): keys, relative mouse motion and mouse buttons go
through the X server, SDL and Slate exactly like a physical keyboard and mouse. It also minimises and restores the
window once, a real loss and return of focus. Run it while the game runs Tests/Auto/fp_xinput.txt, which logs the
results.

Usage: python3 fp_xinput_drive.py <window title> <out-dir>
Requires python-xlib, wmctrl and PIL. Sends input only while the game window is the active window.
"""
import os
import subprocess
import sys
import time

from PIL import Image
from Xlib import X, XK, display
from Xlib.ext import xtest

NAME, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
d = display.Display()
root = d.screen().root
LOG = open(os.path.join(OUT, "driver_log.txt"), "w")


def log(msg):
    line = f"{time.time():.3f} {msg}"
    print(line)
    LOG.write(line + "\n")
    LOG.flush()


def find_window():
    out = subprocess.run(["wmctrl", "-lp"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.split(None, 4)[-1].strip() == NAME:
            return int(line.split()[0], 16)
    return None


def active_window():
    out = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True, text=True).stdout
    try:
        return int(out.strip().split()[-1], 16)
    except (ValueError, IndexError):
        return None


WID = None


def require_focus():
    if active_window() != WID:
        subprocess.run(["wmctrl", "-i", "-a", hex(WID)], check=False)
        time.sleep(0.8)
    if active_window() != WID:
        raise SystemExit("game window is not active; refusing to send input")


def kc(sym):
    code = d.keysym_to_keycode(XK.string_to_keysym(sym))
    if code == 0:
        raise SystemExit(f"no keycode for {sym}")
    return code


def key_down(sym):
    require_focus()
    xtest.fake_input(d, X.KeyPress, kc(sym))
    d.sync()
    log(f"down {sym}")


def key_up(sym):
    xtest.fake_input(d, X.KeyRelease, kc(sym))
    d.sync()
    log(f"up {sym}")


def tap(sym, hold=0.08):
    key_down(sym)
    time.sleep(hold)
    key_up(sym)


def click(button=1, hold=0.08):
    require_focus()
    xtest.fake_input(d, X.ButtonPress, button)
    d.sync()
    time.sleep(hold)
    xtest.fake_input(d, X.ButtonRelease, button)
    d.sync()
    log(f"click {button}")


def move(dx, dy, steps=10, gap=0.02):
    require_focus()
    for _ in range(steps):
        xtest.fake_input(d, X.MotionNotify, detail=True, x=dx // steps, y=dy // steps)
        d.sync()
        time.sleep(gap)
    log(f"move {dx} {dy}")


def shot(name):
    w = d.create_resource_object("window", WID)
    g = w.get_geometry()
    raw = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (g.width, g.height), raw.data, "raw", "BGRX").save(os.path.join(OUT, name + ".png"))


def main():
    global WID
    deadline = time.time() + 300
    while time.time() < deadline and WID is None:
        WID = find_window()
        time.sleep(2)
    if WID is None:
        raise SystemExit("game window not found")
    log(f"window {hex(WID)}")
    subprocess.run(["wmctrl", "-i", "-a", hex(WID)], check=False)
    time.sleep(12)   # fp_xinput.txt: start-up, the mouse-button remap and the input log are set up by now

    log("phase walk")
    key_down("w"); time.sleep(1.5); key_up("w")
    time.sleep(0.6)
    log("phase look right 600 counts, up 300")
    move(600, 0)
    move(0, -300)
    time.sleep(0.6)
    move(0, 300)
    log("phase sprint")
    key_down("w"); key_down("Shift_L"); time.sleep(1.5); key_up("Shift_L"); key_up("w")
    time.sleep(0.6)
    log("phase crouch")
    key_down("Control_L"); time.sleep(0.8)
    key_down("w"); time.sleep(0.8); key_up("w")
    key_up("Control_L")
    time.sleep(0.6)
    log("phase jump: space, then the left mouse button (bound by the script)")
    tap("space")
    time.sleep(1.2)
    click(1)
    time.sleep(1.2)
    log("phase pause and resume with Escape")
    tap("Escape")
    time.sleep(0.8)
    shot("x01_paused")
    tap("Escape")
    time.sleep(0.8)
    log("phase focus loss: minimise while walking, then restore")
    key_down("w")
    time.sleep(0.5)
    subprocess.run(["wmctrl", "-i", "-r", hex(WID), "-b", "add,hidden"], check=False)
    time.sleep(0.2)
    xtest.fake_input(d, X.KeyRelease, kc("w"))   # released while another window has focus
    d.sync()
    log("up w (while minimised)")
    time.sleep(2.0)
    subprocess.run(["wmctrl", "-i", "-r", hex(WID), "-b", "remove,hidden"], check=False)
    subprocess.run(["wmctrl", "-i", "-a", hex(WID)], check=False)
    time.sleep(1.5)
    shot("x02_after_focus_return")
    tap("Escape")
    time.sleep(1.5)
    log("done")


main()
