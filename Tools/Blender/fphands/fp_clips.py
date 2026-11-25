"""The first-person hand clips, keyed pose by pose (see fp_anim.py for the channels and eases).

View space, centimetres: X forward, Y right, Z up, from the eye. The arms are short for their target: the shoulder sits
about 9 cm behind, 20 cm to the side of and 20 cm below the eye, and the knuckles reach about 59 cm from it at full
stretch, a little more with the shoulder carried forward (pro). Strikes stop just short of a locked elbow.

Timings are the game's frame data (60 fps; `Content/Data/firstperson.json`): Jab 6/3/10, Straight 11/3/18, Fireball
12/1/16, Ice Wall 14/1/20 (startup, active, recovery). The active frames are where each strike or cast lands.

Poses follow the first-person hands study (Oblivion's first person and hand anatomy, 2026-11-23): fists with straight
wrists and the knuckles in line with the forearm; the guard raised with the forearms rising from the lower corners; a
casting hand thrown fully open, fingers up and spread, the wrist bent back so the palm faces the target, while the
other hand drops out of the way.
"""


def mirror(h):
    """The right hand's state from the left's (or back): view Y flips."""
    out = dict(h)
    for ch in ("p", "f", "n"):
        if ch in out:
            x, y, z = out[ch]
            out[ch] = (x, -y, z)
    return out


# Shared poses (left hand; the right is the mirror unless given).
READY_L = {"p": (37.0, -13.0, -8.5), "f": (1.0, 0.14, 0.32), "n": (0.0, 0.37, -0.93), "c": 0.9, "s": 0.0, "st": 0.85, "pro": 0.0}
READY_R = {"p": (33.0, 13.0, -11.0), "f": (1.0, -0.14, 0.32), "n": (0.0, -0.37, -0.93), "c": 0.9, "s": 0.0, "st": 0.85, "pro": 0.0}
GUARD_L = {"p": (35.0, -16.5, -4.0), "f": (0.35, 0.30, 1.0), "n": (0.55, 0.85, 0.0), "c": 0.98, "s": 0.0, "st": 0.85, "pro": 0.0}
GUARD_R = mirror(GUARD_L) | {"p": (34.0, 16.5, -5.0)}
# A fist pulled in to cover the chin while the other hand strikes.
CHIN_L = {"p": (31.0, -11.0, -6.0), "f": (0.6, 0.25, 0.75), "n": (0.3, 0.9, -0.3), "c": 1.0, "st": 0.9}
CHIN_R = mirror(CHIN_L) | {"p": (31.0, 12.0, -7.0)}


def up(h, dz):
    x, y, z = h["p"]
    return h | {"p": (x, y, z + dz)}


CLIPS = {
    # At the ready: the fists breathe a little and squeeze now and then.
    "Ready": {"loop": True, "sheet": [0, 60], "keys": [
        {"t": 0, "l": READY_L, "r": READY_R},
        {"t": 60, "l": up(READY_L, 0.6) | {"c": 0.93}, "r": up(READY_R, 0.5) | {"c": 0.92}},
        {"t": 120, "l": READY_L, "r": READY_R},
    ]},
    # The block held: Oblivion's stance raised, both fists up and apart, forearms rising from the lower corners.
    "Guard": {"loop": True, "sheet": [0, 60], "keys": [
        {"t": 0, "l": GUARD_L, "r": GUARD_R},
        {"t": 60, "l": up(GUARD_L, 0.4), "r": up(GUARD_R, 0.4)},
        {"t": 120, "l": GUARD_L, "r": GUARD_R},
    ]},
    # Jab (left): a small load, a snapping extension landing on frame 6 with the palm turned down, a short drive
    # through, then straight back. The right fist covers the chin.
    "Jab": {"sheet": [0, 2, 4, 5, 6, 7, 9, 11, 13, 16, 19], "keys": [
        {"t": 0, "l": READY_L, "r": READY_R},
        {"t": 2, "e": "out", "l": {"p": (35.0, -12.5, -12.6), "n": (0.0, 0.6, -0.8), "c": 0.95}},
        {"t": 6, "e": "snap", "l": {"p": (50.0, -7.0, -6.0), "f": (1.0, 0.10, 0.05), "n": (0.0, 0.05, -1.0), "c": 1.0, "st": 1.0, "pro": 12.0},
         "r": CHIN_R},
        {"t": 7, "e": "out", "l": {"p": (51.0, -6.8, -5.8)}},
        {"t": 9, "e": "io", "l": {"p": (50.4, -7.0, -6.0)}},
        {"t": 13, "e": "out", "l": {"p": (40.0, -11.0, -10.5), "n": (0.0, 0.3, -0.95), "c": 0.95, "pro": 3.0}, "r": CHIN_R},
        {"t": 19, "e": "io", "l": READY_L, "r": READY_R},
    ]},
    # Straight (right): loads with the shoulder drawn back, then the shoulder drives forward behind the fist, landing
    # on frame 11; held, then back. The left fist covers the chin.
    "Straight": {"sheet": [0, 3, 5, 8, 10, 11, 12, 14, 18, 22, 27, 32], "keys": [
        {"t": 0, "l": READY_L, "r": READY_R},
        {"t": 5, "e": "out", "r": {"p": (30.0, 14.0, -12.0), "n": (0.0, -0.6, -0.8), "c": 0.95, "pro": -4.0}},
        {"t": 8, "e": "io", "l": CHIN_L},
        {"t": 11, "e": "snap", "r": {"p": (50.0, 2.0, -6.0), "f": (1.0, -0.05, 0.05), "n": (0.0, 0.0, -1.0), "c": 1.0, "st": 1.0, "pro": 18.0}},
        {"t": 12, "e": "out", "r": {"p": (51.2, 2.4, -5.8)}},
        {"t": 14, "e": "io", "r": {"p": (50.5, 2.0, -6.0)}},
        {"t": 20, "e": "io", "l": CHIN_L},
        {"t": 22, "e": "out", "r": {"p": (38.0, 10.0, -12.5), "n": (0.0, -0.3, -0.95), "pro": 4.0, "c": 0.95}},
        {"t": 32, "e": "io", "l": READY_L, "r": READY_R},
    ]},
    # Fireball (left): the hand draws back beside the face, half closed and palm up while the fire gathers, then is
    # thrown fully open toward the target on frame 12 (fingers up and spread, wrist bent back, palm forward), stays
    # open a moment as the fire flies, and closes back to the ready. The right hand drops out of the way.
    "Fireball": {"sheet": [0, 4, 8, 10, 11, 12, 14, 17, 20, 24, 29], "keys": [
        {"t": 0, "l": READY_L, "r": READY_R},
        {"t": 6, "e": "out", "r": {"p": (30.0, 14.0, -22.0), "n": (0.0, -0.6, -0.8), "c": 0.8}},
        {"t": 8, "e": "out", "l": {"p": (33.0, -14.0, -6.0), "f": (0.6, 0.15, 0.8), "n": (0.15, 0.45, 0.88), "c": 0.55, "st": 0.0}},
        {"t": 12, "e": "snap", "l": {"p": (50.0, -8.0, -2.0), "f": (0.25, 0.10, 1.0), "n": (1.0, 0.05, 0.1), "c": 0.0, "s": 1.0, "pro": 12.0}},
        {"t": 14, "e": "out", "l": {"p": (51.0, -8.0, -1.5)}},
        {"t": 20, "e": "io", "l": {"p": (46.0, -10.0, -5.0), "c": 0.05, "s": 0.8, "pro": 6.0}},
        {"t": 22, "e": "io", "r": {"p": (30.0, 14.0, -22.0)}},
        {"t": 29, "e": "io", "l": READY_L, "r": READY_R},
    ]},
    # Ice Wall (both): the hands sink low, palms down and half closed as the cold gathers, then drive forward and up
    # on frame 14, both thrown open, palms to the target, fingers up and spread; held, then back.
    "IceWall": {"sheet": [0, 4, 8, 11, 13, 14, 16, 20, 24, 29, 35], "keys": [
        {"t": 0, "l": READY_L, "r": READY_R},
        {"t": 8, "e": "out", "l": {"p": (35.0, -15.0, -11.0), "f": (1.0, 0.1, -0.1), "n": (0.0, 0.2, -1.0), "c": 0.5, "st": 0.0},
         "r": {"p": (35.0, 15.0, -11.0), "f": (1.0, -0.1, -0.1), "n": (0.0, -0.2, -1.0), "c": 0.5, "st": 0.0}},
        {"t": 14, "e": "snap", "l": {"p": (47.0, -18.0, -4.0), "f": (0.15, 0.05, 1.0), "n": (1.0, -0.1, 0.05), "c": 0.0, "s": 1.0, "pro": 10.0},
         "r": {"p": (47.0, 18.0, -4.0), "f": (0.15, -0.05, 1.0), "n": (1.0, 0.1, 0.05), "c": 0.0, "s": 1.0, "pro": 10.0}},
        {"t": 16, "e": "out", "l": {"p": (48.0, -18.5, -3.5)}, "r": {"p": (48.0, 18.5, -3.5)}},
        {"t": 24, "e": "io", "l": {"p": (46.0, -18.0, -5.0), "c": 0.05, "s": 0.85}, "r": {"p": (46.0, 18.0, -5.0), "c": 0.05, "s": 0.85}},
        {"t": 35, "e": "io", "l": READY_L, "r": READY_R},
    ]},
}
