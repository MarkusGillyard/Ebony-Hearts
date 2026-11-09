"""Virtual gamepads through Linux uinput, for automated controller tests of a running game.

Usage: python3 virtual_pad.py <scenario> [xbox|ds4]
  menu-and-fight  title -> Versus CPU -> fight with every default action, then quits through the menus.
  disconnect      fights, destroys the device mid-match (disconnect), recreates it (reconnect), takes the slot back
                  with Cross / A, fights again, then quits.
  layout          presses every default button once (an analog R2 / RT hold, an L2 / LT squeeze, D-pad down) while the
                  game logs what each produced (pair it with an automation script that runs log_input in Training).
  remap           through Settings > Controls > Controller - Player 1: moves Light attack onto Triangle / Y,
                  answers the conflict with Swap, backs out to the main menu, then quits.
Pads: "xbox" is a Microsoft Xbox 360 pad (045e:028e); "ds4" is a Sony DualShock 4 (054c:05c4) laid out like the
kernel's hid-sony driver. Buttons are named by the position-neutral layout below, so both pads run the same scenario.
The devices exist only while this script runs. Results are simulated-controller evidence, not physical-pad testing.
"""
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
ABS = {"X": 0x00, "Y": 0x01, "Z": 0x02, "RX": 0x03, "RY": 0x04, "RZ": 0x05, "HAT0X": 0x10, "HAT0Y": 0x11}

# Position-neutral names -> evdev codes per pad. bottom/right/left/top are the face buttons (Cross/Circle/Square/
# Triangle on PlayStation, A/B/X/Y on Xbox); l1/r1 the shoulders; start = Options / Menu; select = Share / View.
PADS = {
    "xbox": {"ids": (0x045E, 0x028E, 0x0110), "name": "Ebony Hearts Test Pad",
             "btn": {"bottom": 0x130, "right": 0x131, "left": 0x133, "top": 0x134, "l1": 0x136, "r1": 0x137,
                     "select": 0x13A, "start": 0x13B, "guide": 0x13C, "l3": 0x13D, "r3": 0x13E},
             "trig": None},
    # 054c:05c4 (first DualShock 4): SDL skips a uinput copy of a Sony id it already drives over HID, such as a real
    # 09cc pad paired to this machine, so the simulated pad uses the other DualShock 4 id.
    "ds4": {"ids": (0x054C, 0x05C4, 0x8111), "name": "Sony Computer Entertainment Wireless Controller",
            "btn": {"bottom": 0x130, "right": 0x131, "top": 0x133, "left": 0x134, "l1": 0x136, "r1": 0x137,
                    "l2": 0x138, "r2": 0x139, "select": 0x13A, "start": 0x13B, "guide": 0x13C, "l3": 0x13D, "r3": 0x13E},
            "trig": ("l2", "r2")},
}


class Pad:
    def __init__(self, kind="xbox", name=None):
        self.kind = kind
        self.spec = PADS[kind]
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_ABS)
        for code in self.spec["btn"].values():
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, code)
        stick = (-32768, 32767) if kind == "xbox" else (0, 255)
        ranges = {"X": stick, "Y": stick, "RX": stick, "RY": stick, "Z": (0, 255), "RZ": (0, 255), "HAT0X": (-1, 1), "HAT0Y": (-1, 1)}
        self.stick_range = stick
        for axis, (lo, hi) in ranges.items():
            fcntl.ioctl(self.fd, UI_SET_ABSBIT, ABS[axis])
            fuzz, flat = (16, 128) if hi > 255 else (0, 0)
            fcntl.ioctl(self.fd, UI_ABS_SETUP, struct.pack("HHiiiiii", ABS[axis], 0, 0, lo, hi, fuzz, flat, 0))
        vendor, product, version = self.spec["ids"]
        label = (name or self.spec["name"]).encode()[:79]
        fcntl.ioctl(self.fd, UI_DEV_SETUP, struct.pack("HHHH80sI", 0x03, vendor, product, version, label, 0))
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(1.5)   # let the system and SDL notice the new device
        self.centre()

    def _emit(self, etype, code, value):
        now = time.time()
        os.write(self.fd, struct.pack("llHHi", int(now), int((now % 1) * 1e6), etype, code, value))

    def sync(self):
        self._emit(EV_SYN, 0, 0)

    def centre(self):
        lo, hi = self.stick_range
        mid = (lo + hi) // 2 if lo == 0 else 0
        for axis in ("X", "Y", "RX", "RY"):
            self._emit(EV_ABS, ABS[axis], mid)
        self.sync()

    def press(self, button, hold=0.08, gap=0.2):
        code = self.spec["btn"][button]
        self._emit(EV_KEY, code, 1)
        self.sync()
        time.sleep(hold)
        self._emit(EV_KEY, code, 0)
        self.sync()
        time.sleep(gap)

    def trigger(self, side, value):
        """Analog trigger 0..1 (r2/rt or l2/lt); the DualShock also reports its digital trigger buttons."""
        axis = ABS["RZ" if side == "r" else "Z"]
        self._emit(EV_ABS, axis, int(value * 255))
        if self.spec["trig"]:
            self._emit(EV_KEY, self.spec["btn"][side + "2"], 1 if value > 0.05 else 0)
        self.sync()

    def hold_trigger(self, side, seconds, gap=0.3):
        for v in (0.15, 0.4, 0.9):       # a real squeeze crosses the thresholds on the way down
            self.trigger(side, v)
            time.sleep(0.02)
        time.sleep(seconds)
        for v in (0.4, 0.1, 0.0):
            self.trigger(side, v)
            time.sleep(0.02)
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
        lo, hi = self.stick_range
        mid = (lo + hi) / 2 if lo == 0 else 0
        self._emit(EV_ABS, ABS["X"], int(mid + x * (hi - mid)))
        self.sync()
        time.sleep(seconds)
        self._emit(EV_ABS, ABS["X"], int(mid))
        self.sync()

    def close(self):
        fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        os.close(self.fd)


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def to_fight(pad):
    pad.press("bottom")            # title
    time.sleep(1.0)
    pad.press("bottom")            # Versus CPU
    time.sleep(0.6)
    pad.press("bottom")            # Wren
    pad.press("bottom")            # opponent
    pad.press("bottom")            # difficulty/side -> fight
    time.sleep(6.0)


def fight_inputs(pad):
    """Every default action once, with the creator's layout."""
    pad.stick(1.0, 0.6)            # walk forward with the analog stick
    for _ in range(3):
        pad.press("left", gap=0.1)     # Square / X: light string
    pad.press("top", gap=0.4)          # Triangle / Y: heavy
    pad.hold_trigger("r", 0.8)         # R2 / RT: block while held
    pad.press("bottom", gap=0.6)       # Cross / A: jump (D-pad up and the stick's up jump too)
    pad.press("l1", gap=0.6)           # L1 / LB: block (second binding beside R2 / RT)
    pad.press("right", gap=0.6)        # Circle / B: dodge
    pad.press("r1", gap=0.8)           # R1 / RB: special
    pad.hold_trigger("l", 0.1, gap=0.9)  # L2 / LT: throw
    pad.dpad(y=1, hold=0.4, gap=0.5)   # D-pad down: crouch


def quit_from_main(pad):
    pad.press("right")             # main menu: Back opens the quit confirmation
    time.sleep(0.5)
    pad.press("bottom")            # Quit


def pause_to_main(pad):
    pad.press("start")             # pause
    time.sleep(0.5)
    pad.dpad(y=-1)                 # wrap to Main Menu
    pad.press("bottom")
    time.sleep(1.0)


def layout(pad):
    """One press of every default button, spaced so the game's log shows each result separately."""
    steps = [("left", "Square / X"), ("top", "Triangle / Y"), ("right", "Circle / B"), ("bottom", "Cross / A"),
             ("l1", "L1 / LB"), ("r1", "R1 / RB")]
    for button, label in steps:
        log(f"press {label}")
        pad.press(button, hold=0.1, gap=0.7)
    log("hold R2 / RT")
    pad.hold_trigger("r", 0.6, gap=0.7)
    log("squeeze L2 / LT (throw)")
    pad.hold_trigger("l", 0.1, gap=0.9)
    log("D-pad down (crouch)")
    pad.dpad(y=1, hold=0.4, gap=0.5)
    log("D-pad right")
    pad.dpad(x=1, hold=0.4, gap=0.5)
    log("D-pad left")
    pad.dpad(x=-1, hold=0.4, gap=0.5)
    log("stick right")
    pad.stick(1.0, 0.4)
    time.sleep(0.5)
    log("press Options / Menu (pause)")
    pad.press("start", gap=0.8)
    log("press Circle / B (resume)")
    pad.press("right", gap=0.8)


def remap(pad):
    """Settings > Controls > Controller - Player 1 > Light attack > Primary > Triangle / Y > Swap, then back out."""
    pad.press("bottom")            # title
    time.sleep(1.0)
    for _ in range(5):             # Versus CPU, Local Versus, Training, Lesson, Move List -> Settings
        pad.dpad(y=1, gap=0.15)
    pad.press("bottom", gap=0.5)   # Settings
    pad.press("bottom", gap=0.5)   # Controls
    pad.dpad(y=1, gap=0.15)        # Button prompts -> Controller - Player 1
    pad.press("bottom", gap=0.6)   # open the layout
    pad.press("bottom", gap=0.6)   # Light attack
    pad.press("bottom", gap=0.6)   # Primary: start capture
    log("capture: pressing Triangle / Y")
    pad.press("top", gap=0.8)      # Heavy's button: conflict page
    pad.press("bottom", gap=0.8)   # Swap
    log("swap chosen")
    for _ in range(4):             # action page -> list -> Controls -> Settings -> main menu
        pad.press("right", gap=0.6)
    time.sleep(1.0)


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "menu-and-fight"
    kind = sys.argv[2] if len(sys.argv) > 2 else "xbox"
    pad = Pad(kind)
    log(f"pad created: {kind}")
    try:
        if scenario == "menu-and-fight":
            to_fight(pad)
            fight_inputs(pad)
            pause_to_main(pad)
            quit_from_main(pad)
        elif scenario == "disconnect":
            to_fight(pad)
            fight_inputs(pad)
            pad.press("start")        # disconnect while this pad owns the pause menu
            time.sleep(0.5)
            pad.close()
            log("pad destroyed (disconnect)")
            time.sleep(4.0)
            pad = Pad(kind, PADS[kind]["name"] + " 2" if kind == "xbox" else None)
            log("pad recreated (reconnect)")
            time.sleep(1.0)
            pad.press("bottom")        # take over the disconnected player's slot
            time.sleep(1.0)
            pad.press("start")         # pause menu from the new device
            pad.press("start")         # resume
            fight_inputs(pad)
            pause_to_main(pad)
            quit_from_main(pad)
        elif scenario == "layout":
            layout(pad)
        elif scenario == "remap":
            remap(pad)
    finally:
        try:
            pad.close()
        except OSError:
            pass
    log(f"virtual pad scenario done: {scenario} ({kind})")


main()
