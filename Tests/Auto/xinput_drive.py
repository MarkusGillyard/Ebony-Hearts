"""Drives a running game window with real X11 key events (XTest), the same path a physical keyboard uses
(X server -> SDL -> Slate -> the game's input router). Captures the window between steps.

Usage: python3 xinput_drive.py <window title> <out-dir>
Requires python-xlib and PIL. Sends only to the game window it finds; never types into other applications.
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


def find_window():
    out = subprocess.run(["wmctrl", "-lp"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.split(None, 4)[-1].strip() == NAME:   # wmctrl -lp: id, desktop, pid, host, title
            return int(line.split()[0], 16), line
    return None, None


def key(sym, hold=0.06, gap=0.18):
    kc = d.keysym_to_keycode(XK.string_to_keysym(sym))
    if kc == 0:
        raise SystemExit(f"no keycode for {sym}")
    xtest.fake_input(d, X.KeyPress, kc)
    d.sync()
    time.sleep(hold)
    xtest.fake_input(d, X.KeyRelease, kc)
    d.sync()
    time.sleep(gap)


def shot(wid, name):
    w = d.create_resource_object("window", wid)
    g = w.get_geometry()
    raw = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    img = Image.frombytes("RGB", (g.width, g.height), raw.data, "raw", "BGRX")
    img.save(os.path.join(OUT, name + ".png"))
    return img


def main():
    deadline = time.time() + 240
    wid = None
    while time.time() < deadline and wid is None:
        wid, line = find_window()
        time.sleep(2)
    if wid is None:
        raise SystemExit("game window not found")
    print("window", line)
    subprocess.run(["wmctrl", "-i", "-a", hex(wid)], check=False)
    time.sleep(8)
    shot(wid, "x01_title")
    key("Return")                     # title: any action
    time.sleep(1.0)
    shot(wid, "x02_main")
    key("j")                          # Versus CPU
    time.sleep(0.5)
    key("j")                          # Wren
    key("j")                          # opponent (defaults to Ashka)
    key("j")                          # difficulty/side -> fight
    time.sleep(5.5)
    shot(wid, "x03_fight")
    # A short real-keyboard exchange: walk in, jab string, heavy, block hold, grab.
    for _ in range(4):
        key("d", hold=0.25, gap=0.05)
    for sym in ("j", "j", "j"):
        key(sym, gap=0.10)
    key("k", gap=0.4)
    key("space", hold=0.8, gap=0.2)
    key("i", gap=0.6)
    shot(wid, "x04_after_inputs")
    key("Escape")                     # pause
    time.sleep(0.6)
    shot(wid, "x05_pause")
    key("Escape")                     # resume
    time.sleep(0.5)
    key("Escape")
    key("w")                          # wrap to "Main Menu"
    key("j")
    time.sleep(1.0)
    key("w")                          # main menu: wrap to Quit
    key("j")
    time.sleep(0.5)
    shot(wid, "x06_quit_confirm")
    key("j")
    print("sent quit")


main()
