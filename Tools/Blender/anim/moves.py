"""Animation definitions for Wren Ku (MMA, orthodox, bouncy athletic all-rounder) and Ashka Rook (Muay Thai,
upright, rhythmic, long guard). Character space: f forward, l the character's left, u up (metres, 1.75 m body).

Every move keys its contact pose on the move's first active frame from Content/Data/Fighters/*.json, and feet that
stay planted are keyed in world space (`foot_*_world`) so they hold still while the simulation moves the root.
"""
import json
import os

from animlib import Pose as P

# ------------------------------------------------------------------------------------------------ stances
# Each fighter's stance lives in stances.json, shared with the motion-capture build (build_mocap.py) so every move,
# scripted or captured, starts and ends in the same stance.
def _stance(name):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stances.json")) as f:
        data = json.load(f)[name]
    # lean / head_pitch / head_yaw steer the captured clips' posture; scripted poses use pelvis_rot, chest and head.
    return P(**{k: tuple(v) if isinstance(v, list) else v for k, v in data.items() if k not in ("idle", "lean", "head_pitch", "head_yaw", "clavicle")})


WREN = _stance("wren")
ASHKA = _stance("ashka")

# Each fighter's crouch (see crouch_pose): pelvis drop, hips and chest angles (yaw, pitch, roll), the guard open and
# tight (the crouching guard) as wrist offsets from the head joint (forward, left, up; see Rig.apply, hand_*_head),
# elbow and knee aims, rear heel lift. Until 2026-11-09 the hands were plain character-space points: the crouch carries
# the head 43-47 cm forward, so they ended 12-24 cm behind and above it, the forearms crossed over the head.
WREN_CROUCH = {
    "pelvis": (0.0, 0.0, -0.47), "pelvis_rot": (-28, 14, 0), "chest": (-4, 26, 0), "head": (0, 6, 0),
    "hands": ((0.30, 0.06, -0.16), (0.17, -0.08, -0.12)), "hands_tight": ((0.16, 0.07, -0.03), (0.12, -0.08, -0.02)),
    "elbow_l": (0.3, -0.12, -0.95), "elbow_r": (0.3, 0.12, -0.95), "knee_l": (0.9, 0.25, 0.0), "knee_r": (0.8, -0.25, 0.1), "ball_r": 45,
}
ASHKA_CROUCH = {
    "pelvis": (0.0, 0.0, -0.49), "pelvis_rot": (-12, 12, 0), "chest": (2, 30, 0), "head": (0, 6, 0),
    "hands": ((0.28, 0.06, -0.14), (0.17, -0.08, -0.10)), "hands_tight": ((0.16, 0.07, -0.04), (0.13, -0.08, -0.03)),
    "elbow_l": (0.4, -0.1, -0.9), "elbow_r": (0.4, 0.1, -0.9), "knee_l": (0.9, 0.2, 0.0), "knee_r": (0.8, -0.25, 0.1), "ball_r": 45, "ball_l": 10,
}
# Each fighter's standing guard (see guard): the stance a little lower, chest and head pitched forward (degrees added
# to the stance's), the shoulders up a little, both wrists as offsets from the head joint so the gloves sit in front of
# the face with the forearms upright, and the elbows aimed down and in. Wren holds a compact MMA shell (lower,
# hunched, gloves at the temples, elbows on the ribs); Ashka a taller Muay Thai high guard (upright, gloves at the
# brow, elbows forward over the body). Until 2026-11-09 the guard put the wrists 17-20 cm forward of the root at
# 1.52 m, where the leaning stance already has the head: the hands wrapped over the head and the outward elbow aims
# flared the elbows to shoulder height.
WREN_GUARD = {
    "pelvis": (-0.01, 0.0, -0.03), "chest": (0, 3, 0), "head": (0, 5, 0), "clav": 4,
    "hand_l": (0.16, 0.07, -0.03), "hand_r": (0.12, -0.08, -0.02),
    "elbow_l": (0.25, -0.12, -0.95), "elbow_r": (0.25, 0.12, -0.95),
}
ASHKA_GUARD = {
    "pelvis": (0.0, 0.0, -0.015), "chest": (0, 3, 0), "head": (0, 5, 0), "clav": 3,
    "hand_l": (0.17, 0.07, -0.04), "hand_r": (0.13, -0.08, -0.03),
    "elbow_l": (0.45, -0.22, -0.86), "elbow_r": (0.45, 0.22, -0.86),
}


def world_feet(stance):
    """Stance with both feet expressed in world space (planted against root travel)."""
    return stance(foot_l_world=stance["foot_l"], foot_r_world=stance["foot_r"])


def lying(stance):
    """On the back, head away from the opponent, body centred on the root. Arms rest on the floor beside the head
    (pelvis-relative: f points up from the floor once the pelvis lies back). The hips and back lie where the
    captured knockout's do (pelvis 14 cm, upper spine 13 cm up); 10 cm higher, the body floated above the floor."""
    return stance(pelvis=(-0.15, 0.0, -0.82), pelvis_rot=(0, -88, 0), chest=(0, -4, 0), head=(0, 6, -10), gaze=0.0,
                  hand_l_rel=(-0.06, 0.48, 0.36), hand_r_rel=(-0.04, -0.46, 0.26), elbow_l=(0.0, 0.6, -0.3), elbow_r=(0.0, -0.6, -0.3),
                  foot_l=(0.72, 0.16, 0.02), foot_r=(0.62, -0.16, 0.10), foot_l_rot=(0, -60, 0), foot_r_rot=(0, -50, 0),
                  knee_l=(0.3, 0.2, 0.6), knee_r=(0.3, -0.2, 0.6), fist=0.3, ball_l=0, ball_r=0,
                  foot_l_world=None, foot_r_world=None, hand_l=None, hand_r=None)


def unrel(pose):
    """Back to world/character-space limbs after a pose that used pelvis-relative effectors."""
    return pose(hand_l_rel=None, hand_r_rel=None, foot_l_rel=None, foot_r_rel=None, knee_follow_pelvis=False, elbow_follow=0.0)


# ------------------------------------------------------------------------------------------------ shared moves
def idle_bounce(s, frames, depth, sway):
    keys = []
    half = frames // 4
    for i in range(5):
        down = i % 2 == 1
        k = s(pelvis=(s["pelvis"][0], s["pelvis"][1], s["pelvis"][2] - (depth if down else 0.0)),
              chest=(s["chest"][0] + (sway if down else -sway), s["chest"][1] + (2 if down else 0), s["chest"][2]),
              hand_l=(s["hand_l"][0], s["hand_l"][1], s["hand_l"][2] - (0.03 if down else 0.0)),
              hand_r=(s["hand_r"][0], s["hand_r"][1], s["hand_r"][2] - (0.02 if down else 0.0)),
              ball_r=s["ball_r"] + (0 if down else 12), ball_l=s["ball_l"] + (0 if down else 8))
        keys.append((1 + i * half, k, "smooth"))
    return keys, frames + 1, None, True


def walk(s, frames, stride, forward, speed_cm):
    """Step-drag shuffle with world-planted feet; the loop's last frame equals its first."""
    sign = 1 if forward else -1
    lead, rear = ("l", "r") if forward else ("r", "l")
    w = world_feet(s)
    st = stride * sign
    lf = w[f"foot_{lead}_world"]
    rf = w[f"foot_{rear}_world"]
    lift = 0.05
    mid = frames // 2

    def at(fl, fr, **extra):
        return w(**{f"foot_{lead}_world": fl, f"foot_{rear}_world": fr}, **extra)
    keys = [
        (1, at(lf, rf), "smooth"),
        (1 + mid // 2, at((lf[0] + st * 0.5, lf[1], lift), rf, pelvis=(s["pelvis"][0] + 0.02 * sign, 0, s["pelvis"][2] + 0.01)), "smooth"),
        (1 + mid, at((lf[0] + st, lf[1], 0.0), rf), "smooth"),
        (1 + mid + mid // 2, at((lf[0] + st, lf[1], 0.0), (rf[0] + st * 0.5, rf[1], lift * 0.8), pelvis=(s["pelvis"][0], 0, s["pelvis"][2] - 0.015)), "smooth"),
        (frames + 1, at((lf[0] + st, lf[1], 0.0), (rf[0] + st, rf[1], 0.0)), "smooth"),
    ]
    travel = [i * speed_cm / 100.0 * sign for i in range(frames + 3)]
    travel = [0.0] + travel
    return keys, frames + 1, travel, True


def guard_pose(s, g):
    px, py, pz = g["pelvis"]
    return s(pelvis=(s["pelvis"][0] + px, s["pelvis"][1] + py, s["pelvis"][2] + pz),
             chest=tuple(a + b for a, b in zip(s["chest"], g["chest"])), head=tuple(a + b for a, b in zip(s["head"], g["head"])),
             hand_l_head=g["hand_l"], hand_r_head=g["hand_r"], elbow_l=g["elbow_l"], elbow_r=g["elbow_r"],
             clav_l=(0, 0, g["clav"]), clav_r=(0, 0, -g["clav"]), fist=1.0)


def guard(s, g):
    """Standing block (held): the fighter's guard (WREN_GUARD, ASHKA_GUARD) with a slow breath. Its feet are the
    stance's, so going into and out of it from the stance moves the arms and the upper body only."""
    gp = guard_pose(s, g)
    p = gp["pelvis"]
    breathe = gp(pelvis=(p[0], p[1], p[2] - 0.012), chest=(gp["chest"][0], gp["chest"][1] + 1.5, gp["chest"][2]))
    return [(1, gp, "smooth"), (31, breathe, "smooth"), (61, gp, "smooth")], 61, None, True


def block_hit(s, g):
    """A blocked hit (blockstun): the guard takes it, the hips and chest give a little and the gloves are pushed back
    toward the face, then it settles; from frame 18 the guard holds until blockstun ends."""
    gp = guard_pose(s, g)
    p, ch, hd = gp["pelvis"], gp["chest"], gp["head"]
    hl, hr = g["hand_l"], g["hand_r"]
    hit = gp(pelvis=(p[0] - 0.05, p[1], p[2] - 0.01), chest=(ch[0], ch[1] - 6, ch[2]), head=(hd[0], hd[1] - 3, hd[2]),
             hand_l_head=(hl[0] - 0.04, hl[1], hl[2] + 0.01), hand_r_head=(hr[0] - 0.03, hr[1], hr[2] + 0.01))
    return [(1, gp, "smooth"), (3, hit, "snap"), (9, hit(pelvis=(p[0] - 0.03, p[1], p[2])), "smooth"), (18, gp, "smooth")], 18, None, False


def hit_light(s):
    """A clean shot: the head snaps back and turns, the chest follows, the hips give a little and the guard is knocked
    loose, then she recovers into her stance."""
    rec = s(pelvis=(s["pelvis"][0] - 0.10, 0, s["pelvis"][2] - 0.02), chest=(s["chest"][0] - 22, s["chest"][1] - 18, 8), head=(16, -32, 8),
            hand_l=(s["hand_l"][0] - 0.16, s["hand_l"][1] + 0.07, s["hand_l"][2] - 0.08), hand_r=(s["hand_r"][0] - 0.10, s["hand_r"][1], s["hand_r"][2] - 0.05), fist=0.6)
    return [(1, s, "smooth"), (3, rec, "snap"), (8, rec(head=(8, -16, 4), chest=(s["chest"][0] - 12, s["chest"][1] - 8, 4)), "smooth"), (20, s, "smooth")], 20, None, False


def hit_heavy(s):
    rec = s(pelvis=(s["pelvis"][0] - 0.14, 0, s["pelvis"][2] - 0.05), pelvis_rot=(s["pelvis_rot"][0] + 10, -8, 0),
            chest=(s["chest"][0] - 30, s["chest"][1] - 24, 10), head=(18, -30, 10),
            hand_l=(s["hand_l"][0] - 0.25, s["hand_l"][1] + 0.18, s["hand_l"][2] - 0.25), hand_r=(s["hand_r"][0] - 0.2, s["hand_r"][1] - 0.15, s["hand_r"][2] - 0.2),
            elbow_l=(-0.2, 0.5, -0.3), elbow_r=(-0.2, -0.5, -0.3), fist=0.4)
    return [(1, s, "smooth"), (4, rec, "snap"), (12, rec(head=(10, -16, 6), chest=(s["chest"][0] - 16, s["chest"][1] - 10, 5)), "smooth"), (28, s, "smooth")], 28, None, False


def knockdown(s):
    """Knocked off the feet backwards the way people fall: the head snaps back, the knees buckle so the hips drop
    first, she sits down hard with the hands reaching back and the chin tucked, then rolls onto her back and the legs
    settle. Ends at lying(s)."""
    lie = lying(s)
    buckle = s(pelvis=(-0.18, 0, -0.30), pelvis_rot=(s["pelvis_rot"][0] + 10, -22, 0), chest=(0, -26, 4), head=(10, -28, 6), gaze=0.0,
               hand_l=(0.05, 0.40, 1.10), hand_r=(0.0, -0.42, 1.05), elbow_l=(-0.2, 0.6, -0.1), elbow_r=(-0.2, -0.6, -0.1), fist=0.3)
    sit = s(pelvis=(-0.30, 0, -0.66), pelvis_rot=(0, -40, 0), chest=(0, -12, 0), head=(0, 18, 0), gaze=0.0,
            hand_l=(-0.30, 0.38, 0.20), hand_r=(-0.32, -0.38, 0.22), elbow_l=(-0.3, 0.5, 0.2), elbow_r=(-0.3, -0.5, 0.2),
            foot_l=(0.42, 0.14, 0.0), foot_r=(0.30, -0.16, 0.0), foot_l_rot=(0, -10, 0), knee_l=(0.4, 0.2, 0.8), knee_r=(0.4, -0.2, 0.8),
            foot_l_world=None, foot_r_world=None, fist=0.2)
    roll = lie(pelvis=(-0.18, 0, -0.68), head=(0, 26, -4), foot_l=(0.62, 0.16, 0.22), foot_r=(0.52, -0.16, 0.30))
    keys = [(1, s, "smooth"), (4, hit_heavy(s)[0][1][1], "snap"), (9, buckle, "smooth"), (14, sit, "in"), (19, roll, "out"),
            (25, lie, "smooth"), (43, lie(head=(0, 4, -12)), "smooth")]
    return keys, 43, None, False


def knockdown_lie(s, head_toward=False):
    """Lying on the back after a throw lands: head away from the opponent, or toward it (thrown over the shoulder)."""
    lie = lying(s)(spin=180.0) if head_toward else lying(s)
    return [(1, lie, "smooth"), (22, lie(chest=(0, -2, 0)), "smooth"), (43, lie, "smooth")], 43, None, False


def getup(s, technical):
    """From lying on the back to stance in 21 frames. Technical stand-up posts a hand and swings a leg back."""
    lie = lying(s)
    if technical:
        sit = lie(pelvis=(-0.20, 0, -0.66), pelvis_rot=(-20, -40, 0), chest=(0, 25, 0), head=(0, 10, 0), gaze=0.5,
                  hand_r_rel=None, hand_r=(-0.35, -0.30, 0.05), hand_l=(0.25, 0.25, 0.75), hand_l_rel=None, foot_l=(0.45, 0.15, 0.0), foot_l_rot=(-10, 0, 0))
        hips = sit(pelvis=(-0.25, 0, -0.42), pelvis_rot=(-30, -10, 10), chest=(5, 30, 0), foot_r=(-0.20, -0.25, 0.25), foot_r_rot=(-50, 30, 0))
        crouch = s(pelvis=(-0.05, 0, -0.30), chest=(s["chest"][0], 25, 0), hand_l=(0.30, 0.12, 1.20), hand_r=(0.15, -0.10, 1.25))
    else:
        sit = lie(pelvis=(-0.18, 0, -0.62), pelvis_rot=(0, -30, 0), chest=(0, 30, 0), head=(0, 10, 0), gaze=0.5,
                  hand_l_rel=None, hand_r_rel=None, hand_l=(-0.25, 0.32, 0.05), hand_r=(-0.25, -0.32, 0.05), foot_l=(0.40, 0.12, 0.0), foot_r=(0.35, -0.14, 0.0))
        hips = sit(pelvis=(-0.08, 0, -0.45), pelvis_rot=(-10, 10, 0), chest=(0, 35, 0), hand_l=(0.25, 0.20, 0.6), hand_r=(0.2, -0.2, 0.6),
                   foot_l=s["foot_l"], foot_r=s["foot_r"])
        crouch = s(pelvis=(-0.04, 0, -0.28), chest=(s["chest"][0], 22, 0))
    return [(1, lie, "smooth"), (6, unrel(sit), "out"), (11, unrel(hips), "smooth"), (16, unrel(crouch), "smooth"), (21, unrel(s), "smooth")], 21, None, False


def ko(s):
    keys, _, _, _ = knockdown(s)
    lie = lying(s)
    keys = keys[:-1] + [(43, lie(head=(10, 4, -20)), "smooth"), (121, lie(head=(14, 2, -24), chest=(0, -2, 0)), "smooth")]
    return keys, 121, None, False


def tech(s):
    push = s(hand_l=(0.55, 0.15, 1.25), hand_r=(0.52, -0.12, 1.22), fist=0.0, chest=(s["chest"][0] + 10, 5, 0), elbow_l=(0.1, 0.4, -0.4), elbow_r=(0.1, -0.4, -0.4))
    back = s(pelvis=(s["pelvis"][0] - 0.08, 0, s["pelvis"][2] - 0.03))
    # The shove builds over four frames; a snap reached it in one, which read as a jump.
    return [(1, s, "smooth"), (5, push, "smooth"), (10, back, "smooth"), (21, s, "smooth")], 21, None, False


def rolls(s, move, forward):
    """Forward roll (somersault through) or back roll, tucked, pelvis-relative limbs, travel from the move data."""
    total = move["total"]
    sign = 1 if forward else -1
    # Both rolls curl forward (rounded back, chin in, knees to the chest, hands at the shins); only the direction the
    # body turns differs. The back roll used to mirror the curl too, which arched it and folded the legs backwards.
    # Chin and chest tucked well in, so the back of the neck and the shoulders lead the roll rather than the head.
    tuck = s(gaze=0.0, chest=(0, 50, 0), head=(0, 55, 0), fist=0.6,
             hand_l=None, hand_r=None, hand_l_rel=(0.20, 0.18, 0.10), hand_r_rel=(0.20, -0.18, 0.12),
             elbow_l=(0.3, 0.3, -0.2), elbow_r=(0.3, -0.3, -0.2),
             foot_l=None, foot_r=None, foot_l_rel=(0.30, 0.12, -0.30), foot_r_rel=(0.25, -0.12, -0.32),
             foot_l_world=None, foot_r_world=None, knee_follow_pelvis=True, elbow_follow=1.0, knee_l=(0.4, 0.1, 0.4), knee_r=(0.4, -0.1, 0.4))
    dip = s(pelvis=(s["pelvis"][0] + 0.10 * sign, 0, -0.32), chest=(s["chest"][0], 30, 0), head=(0, 20, 0), elbow_follow=1.0)
    # Take-off. The dip names no pelvis-relative feet, so the tuck's used to apply from its first frame and the feet
    # jumped into it (up to 60 cm). Now they push off in character space onto where the tuck holds them at frame 6
    # (measured on both fighters, within ~2 cm) and the tuck takes over from frame 7.
    # The hands go the same way: down from the guard onto where the tuck holds them at the shins.
    if forward:
        off_l, off_r = (-0.18, 0.12, 0.13), (-0.20, -0.12, 0.18)   # heels kick up behind as she dives
        hoff_l, hoff_r = (0.22, 0.18, 0.31), (0.24, -0.18, 0.31)
    else:
        off_l, off_r = (0.22, 0.12, 0.73), (0.24, -0.12, 0.68)     # legs swing up as she sits back onto her shoulders
        hoff_l, hoff_r = (-0.18, 0.18, 0.71), (-0.20, -0.18, 0.71)
    # The knees aim with the pelvis from the dip on, so they do not flip as the pelvis tips into the roll.
    keys = [(1, s, "smooth"), (3, dip(foot_l_rel=None, foot_r_rel=None, hand_l_rel=None, hand_r_rel=None, knee_follow_pelvis=True), "out"),
            (6, tuck(pelvis=(0.1 * sign, 0, -0.45), pelvis_rot=(0, 90 * sign, 0), foot_l_rel=None, foot_r_rel=None,
                     foot_l=off_l, foot_r=off_r, hand_l_rel=None, hand_r_rel=None, hand_l=hoff_l, hand_r=hoff_r), "linear"),
            (7, tuck(pelvis=(0.075 * sign, 0, -0.475), pelvis_rot=(0, 112.5 * sign, 0)), "linear"),
            (10, tuck(pelvis=(0.0, 0, -0.55), pelvis_rot=(0, 180 * sign, 0)), "linear"),
            (14, tuck(pelvis=(0.0, 0, -0.50), pelvis_rot=(0, 270 * sign, 0)), "linear")]
    # Landing (the same for both rolls, which end in the same tuck). As she comes upright the feet leave the tuck
    # where they really are (measured on both fighters, within ~4 cm): the lead foot comes down on its stance spot and
    # the rear one swings through the air onto its own. Before, both jumped to the stance on one frame (up to 52 cm).
    sl, sr = (s["foot_l"][0], s["foot_l"][1], 0.0), (s["foot_r"][0], s["foot_r"][1], 0.0)
    air_l, air_r = (0.34, 0.01, 0.26), (0.21, -0.19, 0.24)
    mid_l, mid_r = sl, ((air_r[0] + sr[0]) / 2, (air_r[1] + sr[1]) / 2, 0.08)
    # The hands leave the tuck from where it holds them (measured, within ~3 cm) and come up into the guard.
    hair_l, hair_r = ((0.21, 0.13, 0.78), (0.11, -0.21, 0.80)) if forward else ((0.28, 0.12, 0.62), (0.20, -0.23, 0.64))
    gl, gr = s["hand_l"], s["hand_r"]
    hmid_l, hmid_r = tuple((a + b) / 2 for a, b in zip(hair_l, gl)), tuple((a + b) / 2 for a, b in zip(hair_r, gr))
    # Out of the forward roll the elbows keep aiming with the chest while she comes upright (the last key hands them back
    # to the stance's aim); out of the back roll that swung an elbow 48 cm in a frame, so they go back to the stance's
    # aim as she rises.
    up = unrel(dip(pelvis_rot=(s["pelvis_rot"][0], 360 * sign + s["pelvis_rot"][1], 0), pelvis=(0, 0, -0.30)))(
        elbow_follow=1.0 if forward else 0.0)
    keys += [(18, up(foot_l=air_l, foot_r=air_r, hand_l=hair_l, hand_r=hair_r), "linear"),
             (21, up(foot_l=mid_l, foot_r=mid_r, hand_l=hmid_l, hand_r=hmid_r), "smooth"),
             (24, up(foot_l=sl, foot_r=sr, hand_l=gl, hand_r=gr), "smooth"),
             (total, unrel(s(pelvis_rot=(s["pelvis_rot"][0], 360 * sign + s["pelvis_rot"][1], 0))), "smooth")]
    return keys, total, move.get("travel"), False


# ------------------------------------------------------------------------------------------------ jump attacks
# The light jump attacks (the heavy ones are captured: mocap_clips.json). The game lifts the fighter (the jump's
# height is the simulation's), so these are airborne poses at standing hip
# height: the legs drawn up under the body (pelvis-relative feet), never on the floor. They begin and end in that
# airborne guard, so the jump clip hands over to them and they hand back to it (or land) without a jump.
def air_guard(s, **kw):
    a = s(foot_l=None, foot_r=None, foot_l_world=None, foot_r_world=None,
          foot_l_rel=(0.16, 0.13, -0.52), foot_r_rel=(-0.04, -0.13, -0.48),
          knee_l=(0.6, 0.1, 0.35), knee_r=(0.6, -0.1, 0.35), knee_follow_pelvis=True)
    return a(**kw) if kw else a


def jump_punch(s, move):
    """Wren's jumping punch: a right straight driven down at the head below, shoulder turned in behind it."""
    total = move["total"]
    a = air_guard(s)
    ch = s["chest"]
    chamber = a(hand_r=(0.08, -0.17, 1.38), chest=(ch[0] - 10, ch[1] + 8, 0))
    punch = a(hand_r=(0.62, -0.03, 1.02), elbow_r=(-0.1, -0.45, -0.3), chest=(ch[0] + 16, ch[1] + 22, -2), clav_r=(22, 0, 0),
              head=(0, 12, 0), gaze=0.5)
    keys = [(1, a, "smooth"), (3, chamber, "in"), (6, punch, "smooth"), (11, punch, "hold"), (total, a, "smooth")]
    return keys, total, None, False


def jump_elbow(s, move):
    """Ashka's jumping elbow: the right elbow raised high, then brought down and forward through the head below."""
    total = move["total"]
    a = air_guard(s)
    ch = s["chest"]
    raised = a(hand_r=(0.04, -0.10, 1.66), elbow_r=(0.2, -0.6, 0.8), chest=(ch[0] - 14, ch[1] - 4, 0))
    strike = a(hand_r=(0.22, 0.02, 1.30), elbow_r=(0.8, -0.2, -0.4), chest=(ch[0] + 22, ch[1] + 20, 0), clav_r=(15, 0, 0),
               head=(0, 10, 0), gaze=0.5)
    keys = [(1, a, "smooth"), (3, raised, "smooth"), (6, strike, "smooth"), (11, strike, "hold"), (total, a, "smooth")]
    return keys, total, None, False


# ------------------------------------------------------------------------------------------------ crouch family
# The crouch is a combat posture the simulation lowers over rules.crouchFrames (3) frames to a crouching hurtbox whose
# top is the head (Wren 110 cm, Ashka 105 cm), so the drawn crouch must bring the head that low. The feet stay on
# their stance spots (world-planted) so going down and coming up never slides them; the knees take the drop and the
# rear heel comes up. `look` is each fighter's own crouch (Wren a wrestler's level change, Ashka a compact,
# more upright Muay Thai shell).
def crouch_pose(s, look, guard_tight=False):
    w = world_feet(s)
    hl, hr = look["hands_tight"] if guard_tight else look["hands"]
    return w(pelvis=look["pelvis"], pelvis_rot=look["pelvis_rot"], chest=look["chest"], head=look["head"], gaze=0.9,
             hand_l_head=hl, hand_r_head=hr, elbow_l=look["elbow_l"], elbow_r=look["elbow_r"], knee_l=look["knee_l"], knee_r=look["knee_r"],
             ball_r=look["ball_r"], ball_l=look.get("ball_l", 0), fist=1.0)


def crouch_loop(s, look, guard_tight=False):
    c = crouch_pose(s, look, guard_tight)
    p = c["pelvis"]
    breathe = c(pelvis=(p[0], p[1], p[2] - 0.012), chest=(c["chest"][0], c["chest"][1] + 2, c["chest"][2]))
    return [(1, c, "smooth"), (31, breathe, "smooth"), (61, c, "smooth")], 61, None, True


def crouch_block_hit(s, look):
    g = crouch_pose(s, look, True)
    (hl, hr), p = look["hands_tight"], g["pelvis"]
    hit = g(pelvis=(p[0] - 0.06, p[1], p[2] - 0.02), chest=(g["chest"][0], g["chest"][1] - 7, 0), head=(g["head"][0], g["head"][1] - 6, 0),
            hand_l_head=(hl[0] - 0.04, hl[1], hl[2] + 0.01), hand_r_head=(hr[0] - 0.03, hr[1], hr[2] + 0.01))
    return [(1, g, "smooth"), (3, hit, "snap"), (9, hit(pelvis=(p[0] - 0.03, p[1], p[2])), "smooth"), (18, g, "smooth")], 18, None, False


def crouch_hit(s, look):
    """Hit while crouching (a mid or a low gets through): the head and shoulders snap back, the guard is knocked loose,
    the hips stay low, then she settles back into the crouch."""
    c = crouch_pose(s, look)
    p, ch = c["pelvis"], c["chest"]
    (hl, hr) = look["hands"]
    rec = c(pelvis=(p[0] - 0.09, p[1], p[2] + 0.03), chest=(ch[0] - 14, ch[1] - 22, 6), head=(12, -26, 6),
            hand_l_head=(hl[0] - 0.12, hl[1] + 0.08, hl[2] - 0.10), hand_r_head=(hr[0] - 0.08, hr[1] - 0.04, hr[2] - 0.06), fist=0.6)
    return [(1, c, "smooth"), (3, rec, "snap"), (9, rec(head=(6, -12, 3), chest=(ch[0] - 6, ch[1] - 10, 3)), "smooth"), (22, c, "smooth")], 22, None, False


def knockdown_launch(s):
    """Launched by an uppercut: the chin snaps up, the body arches and both feet leave the floor, the legs trail as
    the hips rise past the shoulders' line, then the back lands flat and the legs come down. Ends at lying(s), where
    the get-up starts. The simulation knocks the defender down on contact (fully invulnerable); the lift is drawn."""
    lie = lying(s)
    snap = s(pelvis=(-0.06, 0, 0.0), pelvis_rot=(s["pelvis_rot"][0], -6, 0), chest=(0, -28, 0), head=(0, -40, 0), gaze=0.0,
             hand_l=(0.05, 0.38, 1.30), hand_r=(0.10, -0.40, 1.25), elbow_l=(-0.2, 0.6, 0.0), elbow_r=(-0.2, -0.6, 0.0), fist=0.3)
    lifted = s(pelvis=(-0.22, 0, 0.16), pelvis_rot=(0, -30, 0), chest=(0, -30, 4), head=(0, -30, 0), gaze=0.0,
               foot_l_world=None, foot_r_world=None, foot_l=(0.05, 0.14, 0.22), foot_r=(-0.10, -0.16, 0.30),
               knee_l=(0.5, 0.2, 0.3), knee_r=(0.5, -0.2, 0.3), hand_l=(-0.10, 0.50, 1.40), hand_r=(-0.12, -0.52, 1.35),
               elbow_l=(-0.3, 0.6, 0.2), elbow_r=(-0.3, -0.6, 0.2), fist=0.2)
    over = lifted(pelvis=(-0.42, 0, -0.10), pelvis_rot=(0, -62, 0), chest=(0, -16, 0), head=(0, 4, 0),
                  foot_l=(0.30, 0.15, 0.55), foot_r=(0.20, -0.16, 0.62), hand_l=(-0.55, 0.45, 0.80), hand_r=(-0.58, -0.45, 0.78))
    impact = lie(pelvis=(-0.18, 0, -0.80), head=(0, 18, -4), foot_l=(0.58, 0.16, 0.30), foot_r=(0.50, -0.16, 0.42))
    keys = [(1, s, "smooth"), (4, snap, "smooth"), (9, lifted, "smooth"), (17, unrel(over), "smooth"), (24, impact, "fall"),
            (29, lie(head=(0, 10, -6), foot_l=(0.66, 0.16, 0.08)), "out"), (43, lie(head=(0, 4, -12)), "smooth")]
    return keys, 43, None, False


# ------------------------------------------------------------------------------------------------ Wren
def wren_moves(data):
    s = WREN
    w = world_feet(s)
    m = {mv["id"]: mv for mv in data["moves"]}
    out = {}
    out["Idle"] = idle_bounce(s, 72, 0.025, 3)
    out["WalkF"] = walk(s, 16, 0.448, True, data["walkForward"])
    out["WalkB"] = walk(s, 16, 0.384, False, data["walkBack"])
    out["Guard"] = guard(s, WREN_GUARD)
    out["BlockHit"] = block_hit(s, WREN_GUARD)
    out["HitLight"] = hit_light(s)
    out["HitHeavy"] = hit_heavy(s)
    out["Knockdown"] = knockdown(s)
    out["KnockdownLie"] = knockdown_lie(s)
    out["KnockdownLieRev"] = knockdown_lie(s, head_toward=True)
    out["Getup"] = getup(s, True)
    out["KO"] = ko(s)
    out["ThrowTech"] = tech(s)
    out["DF"] = rolls(s, m["DF"], True)
    out["DB"] = rolls(s, m["DB"], False)
    if "JL" in m:
        out["JL"] = jump_punch(s, m["JL"])
    out["Crouch"] = crouch_loop(s, WREN_CROUCH)
    out["CrouchGuard"] = crouch_loop(s, WREN_CROUCH, True)
    out["CrouchBlockHit"] = crouch_block_hit(s, WREN_CROUCH)
    out["CrouchHit"] = crouch_hit(s, WREN_CROUCH)
    out["KnockdownLaunch"] = knockdown_launch(s)
    # Down + Light: low kick. From the crouch the lead leg snaps out low to the shin, heel first with the toes turned
    # out, the body staying down behind it and the hands up; the foot comes straight back to its spot.
    c = crouch_pose(s, WREN_CROUCH)
    pr, cr = WREN_CROUCH["pelvis_rot"], WREN_CROUCH["chest"]
    lk = c(foot_l_world=None, foot_l=(0.98, 0.10, 0.14), foot_l_rot=(-35, -15, 0), knee_l=(0.8, 0.4, 0.2), pelvis=(-0.08, 0, WREN_CROUCH["pelvis"][2] + 0.01),
           pelvis_rot=(pr[0] - 18, pr[1] + 4, -8), chest=(cr[0] - 4, cr[1] + 2, 6), head=(12, -6, 0))
    half = c(foot_l_world=None, foot_l=(0.72, 0.12, 0.14), knee_l=(0.8, 0.35, 0.25), pelvis_rot=(pr[0] - 13, pr[1] + 3, -6))
    out["CL"] = ([(1, c, "smooth"), (4, c(foot_l_world=None, foot_l=(0.40, 0.12, 0.10), knee_l=(0.8, 0.3, 0.3), pelvis_rot=(pr[0] - 8, pr[1] + 2, -4)), "in"),
                  (6, half, "linear"), (7, lk, "out"), (9, lk, "hold"), (14, c(foot_l_world=None, foot_l=(0.45, 0.13, 0.06), knee_l=(0.8, 0.3, 0.2)), "smooth"),
                  (19, c(foot_l_world=(WREN["foot_l"][0], WREN["foot_l"][1], 0.0)), "smooth"), (22, c, "smooth")], 22, None, False)
    # Down + Heavy: rising uppercut. Down low with the rear hip loaded and the rear fist dropped to the hip, she drives
    # up off both legs and turns the rear hip and heel over, the rear fist rising close to the body with the elbow under
    # it, through the chin to above her own head; the lead hand stays on her face. The lead foot steps in with the travel.
    tu = sum((seg["frames"][1] - seg["frames"][0] + 1) * seg["vx"] for seg in m["U"]["travel"]) / 100.0
    fl_in = (s["foot_l"][0] + tu, s["foot_l"][1], 0.0)
    loadu = c(pelvis=(0.0, 0, WREN_CROUCH["pelvis"][2] - 0.02), pelvis_rot=(-48, 24, 0), chest=(-10, 28, 0), hand_r=(0.18, -0.22, 0.86),
              elbow_r=(0.1, -0.8, -0.6), hand_l_head=(0.20, 0.06, -0.06), hand_r_head=None)
    drive = w(pelvis=(0.08, 0, -0.10), pelvis_rot=(18, 8, 0), chest=(16, 0, 0), head=(0, 4, 0), hand_r=(0.55, -0.02, 1.48), elbow_r=(0.6, -0.2, -1.0),
              clav_r=(12, 0, 10), hand_l=(0.24, 0.10, 1.40), elbow_l=(0.4, 0.3, -0.6), ball_r=50, foot_r_rot=(-10, 0, 0), foot_l_world=fl_in, fist=1.0)
    # The follow-through keeps the bend (fist above the eyes, elbow under it) and the rear foot steps up behind it.
    finish = drive(hand_r=(0.42, 0.02, 1.68), elbow_r=(0.5, -0.2, -1.0), chest=(20, -8, 0), head=(0, -4, 0), pelvis=(0.08, 0, -0.04), clav_r=(16, 0, 16),
                   foot_r_world=(s["foot_r"][0] + tu, s["foot_r"][1], 0.0))
    back = w(pelvis=(0.04, 0, -0.10), pelvis_rot=(-15, 6, 0), chest=(0, 8, 0), hand_r=(0.28, -0.12, 1.36), elbow_r=(0.3, -0.2, -0.9), foot_l_world=fl_in, ball_r=20,
             foot_r_world=(s["foot_r"][0] + tu, s["foot_r"][1], 0.0))
    # The rise accelerates into contact ("in"), so the body is still low through the crouching hurtbox's frames.
    # The load eases both ways: from the crouching guard the rear fist travels further to the hip than it did from the
    # old open crouch, and an "in" load put a 25 cm hand step on frame 5.
    out["U"] = ([(1, c, "smooth"), (4, loadu, "smooth"), (10, drive, "in"), (13, finish, "out"), (17, finish, "hold"), (30, back, "smooth"),
                 (52, w(foot_l_world=fl_in, foot_r_world=(s["foot_r"][0] + tu, s["foot_r"][1], 0.0)), "smooth")], 52, m["U"]["travel"], False)

    # Light 1: jab. The lead foot steps in with the 6 cm of travel; contact on frame 5.
    jab = w(hand_l=(0.66, 0.06, 1.43), pelvis_rot=(-30, 6, 0), chest=(-8, 10, 2), clav_l=(-18, 0, 0), elbow_l=(-0.1, 0.45, -0.3),
            foot_l_world=(0.33, 0.11, 0.0), head=(0, -6, 0))
    out["L1"] = ([(1, w, "smooth"), (3, w(hand_l=(0.30, 0.12, 1.40), foot_l_world=(0.30, 0.11, 0.03)), "in"), (5, jab, "snap"),
                  (7, jab, "hold"), (10, jab(hand_l=(0.40, 0.12, 1.39), clav_l=(-5, 0, 0)), "smooth"),
                  (15, w(foot_l_world=(0.33, 0.11, 0.0), foot_r_world=(-0.19, -0.18, 0.0)), "smooth")], 15, m["L1"]["travel"], False)
    # Light 2: cross. Rear hip and heel turn over; rear hand to the jaw line on frame 6.
    cross = w(hand_r=(0.67, -0.02, 1.43), hand_l=(0.16, 0.12, 1.42), pelvis_rot=(0, 8, 0), chest=(12, 12, -2), clav_r=(25, 0, 0),
              elbow_r=(-0.1, -0.45, -0.3), foot_r_rot=(-15, 0, 0), ball_r=40, head=(0, -6, 0), foot_l_world=(0.36, 0.11, 0.0))
    out["L2"] = ([(1, w, "smooth"), (3, w(hand_r=(0.18, -0.12, 1.38), pelvis_rot=(-30, 6, 0)), "in"), (6, cross, "snap"), (8, cross, "hold"),
                  (12, cross(hand_r=(0.35, -0.10, 1.40), pelvis_rot=(-20, 6, 0), clav_r=(8, 0, 0)), "smooth"),
                  (19, w(foot_l_world=(0.40, 0.11, 0.0), foot_r_world=(-0.13, -0.18, 0.0)), "smooth")], 19, m["L2"]["travel"], False)
    # Light 3: spinning back elbow, turning the back through (clockwise); the right elbow lands at ~200 deg. The lead
    # foot steps across onto the pivot with the travel and turns on its ball; the rear foot lifts a little and swings
    # round at hip width, lands back in stance, and the lead foot steps back out. No foot slides round the floor.
    # At contact her right side is to the opponent: the upper arm points at them at head height and the forearm folds
    # in front of the right shoulder (with the fist behind the head the arm wrapped round it, and folded across the
    # chest the elbow pointed up); the left hand guards the face, the head turns ahead of the body
    # to look over the right shoulder at contact, and the knees track over the feet (they caved in with the default
    # aim).
    t3 = sum((seg["frames"][1] - seg["frames"][0] + 1) * seg["vx"] for seg in m["L3"]["travel"]) / 100.0
    piv = (0.28 + t3, 0.02)                                  # world; 20 cm ahead of her centre once the travel is done
    across = (piv[0] - 0.11, piv[1], 0.0)                    # lead ankle, its ball on the pivot
    home_l = (s["foot_l"][0] + t3, s["foot_l"][1], 0.0)      # the lead foot's stance spot after the travel
    # spin=0 is keyed here: the stance has none, and a channel missing from a key takes the next key's value, which
    # turned her 60 deg in one frame as the spin began.
    sb = w(spin=0.0, pivot=piv, pivot_world=True, foot_l_world=across, foot_r_world=None, foot_r=(s["foot_r"][0] - 0.035, s["foot_r"][1], 0.0),
           knee_l=(0.6, 0.3, 0.0), knee_r=(0.5, -0.5, 0.0))
    elbow = sb(spin=-200, hand_r=(-0.07, -0.17, 1.50), elbow_r=(-0.8, -0.30, 0.50), hand_l=(0.20, -0.08, 1.52),
               chest=(-15, 8, 0), head=(-60, 6, 0), gaze=0.0, foot_r=(-0.08, -0.20, 0.07))
    out["L3"] = ([(1, w, "smooth"),
                  (2, w(foot_l_world=((s["foot_l"][0] + across[0]) / 2, (s["foot_l"][1] + across[1]) / 2, 0.04), chest=(8, 6, 0), knee_l=(0.6, 0.2, 0.0)), "smooth"),
                  (3, sb(chest=(12, 8, 0)), "smooth"),
                  (5, sb(spin=-60, chest=(20, 10, 0), hand_r=(0.10, 0.05, 1.42), gaze=0.4, foot_r=(-0.14, -0.20, 0.06)), "smooth"),
                  # The turn flows through the strike: a snap into it turned her 106 deg in one frame, and an "out"
                  # back to the guard moved the arms 47 cm in one.
                  (7, sb(spin=-130, chest=(5, 9, 0), hand_r=(0.06, 0.02, 1.43), elbow_r=(-0.5, -0.45, 0.05), hand_l=(0.30, 0.02, 1.48),
                         head=(-35, 4, 0), gaze=0.0, foot_r=(-0.10, -0.20, 0.07)), "smooth"),
                  (9, elbow, "smooth"), (11, elbow(spin=-225, head=(-55, 6, 0)), "smooth"),
                  # The elbow drops back under the arm on the way to the guard (aimed straight from the strike's
                  # aim to the guard's, it flipped over the arm, 31 cm in a frame).
                  (13, sb(spin=-265, hand_r=(0.02, -0.16, 1.48), elbow_r=(-0.6, -0.55, -0.1), hand_l=(0.30, 0.0, 1.46),
                          head=(-35, 5, 0), gaze=0.15, foot_r=(-0.14, -0.20, 0.06)), "smooth"),
                  (15, sb(spin=-305, hand_r=(0.18, -0.10, 1.40), elbow_r=(-0.1, -0.4, -0.8), hand_l=(0.42, 0.03, 1.38),
                          head=(-20, 4, 0), gaze=0.4, foot_r=(-0.18, -0.20, 0.06)), "smooth"),
                  (16, sb(spin=-330, gaze=0.6, foot_r=(-0.20, -0.20, 0.05)), "smooth"),
                  (19, sb(spin=-360, foot_r=s["foot_r"]), "smooth"),
                  (22, sb(spin=-360, foot_l_world=((across[0] + home_l[0]) / 2, (across[1] + home_l[1]) / 2, 0.05)), "smooth"),
                  (25, sb(spin=-360, foot_l_world=home_l), "smooth"),
                  (30, sb(spin=-360, foot_l_world=home_l), "smooth")], 30, m["L3"]["travel"], False)
    # Heavy: rear roundhouse ("Punt"), shin/instep at head height on frame 12, pivoting on the lead ball.
    chamber = w(pelvis=(-0.02, 0, -0.06), pelvis_rot=(-10, 0, 10), chest=(10, 5, -8), foot_r_world=None,
                foot_r=(0.05, -0.10, 0.45), knee_r=(0.6, 0.2, 0.5), foot_r_rot=(-30, -40, 0), ball_l=30, foot_l_rot=(10, 0, 0),
                hand_r=(-0.05, -0.30, 1.10), gaze=0.8)
    kick = chamber(pelvis=(0.0, 0, -0.04), pelvis_rot=(45, -5, 35), chest=(-15, -10, -20), foot_r=(0.95, 0.15, 1.45),
                   foot_r_rot=(60, -70, 0), knee_r=(0.5, 0.0, 1.0), hand_r=(-0.30, -0.35, 0.95), hand_l=(0.20, 0.18, 1.45),
                   foot_l_rot=(60, 0, 0), ball_l=45)
    out["H"] = ([(1, w, "smooth"), (5, chamber, "in"), (12, kick, "snap"), (14, kick(foot_r=(0.80, 0.30, 1.40)), "linear"),
                 (21, chamber(pelvis_rot=(10, 0, 10), foot_r=(0.0, -0.05, 0.40)), "smooth"), (34, w(foot_r_world=s["foot_r"]), "smooth")],
                34, m["H"]["travel"], False)
    # Toward + Heavy: spinning back kick. Turn the back through 180 deg and drive the rear heel straight to the body.
    sk = s(pivot=(0.05, 0.0))
    sbk = sk(spin=-180, pelvis_rot=(-90, 10, -10), chest=(10, -5, 0), head=(-60, 0, 0), gaze=0.0, foot_r=None,
             foot_r_abs=(1.15, 0.0, 1.00), foot_r_rot=(0, 20, 0), knee_r=(0.0, -0.4, 0.3), hand_l=(0.0, 0.25, 1.30), hand_r=(-0.2, 0.0, 1.30))
    out["FH"] = ([(1, sk, "smooth"), (6, sk(spin=-90, chest=(-20, 5, 0), gaze=0.0, head=(-40, 0, 0)), "in"),
                  (10, sk(spin=-170, foot_r=(0.10, -0.05, 0.55), knee_r=(0.0, -0.5, 0.4), head=(-60, 0, 0), gaze=0.0), "smooth"),
                  (15, sbk, "snap"), (17, sbk, "hold"), (24, sk(spin=-180, foot_r=(0.20, -0.05, 0.40), foot_r_abs=None, gaze=0.0, head=(-50, 0, 0)), "smooth"),
                  (38, sk(spin=-360, foot_r=s["foot_r"], foot_r_abs=None), "smooth")], 38, m["FH"]["travel"], False)
    # Special: 720 Hook Kick. Step-turn 180, jump and spin a full turn, hook with the right heel at frame 26, spin out and land.
    hk = s(pivot=(0.05, 0.0))
    takeoff = hk(spin=-200, pelvis=(0.05, 0, -0.25), chest=(-10, 20, 0), head=(-60, 10, 0), gaze=0.0, hand_l=(0.1, 0.35, 1.0), hand_r=(0.0, -0.35, 1.0))
    air = hk(spin=-420, pelvis=(0.15, 0, 0.30), pelvis_rot=(-38, 10, 0), chest=(0, 10, 0), gaze=0.0, foot_l=(0.25, 0.10, 0.55), foot_r=(0.05, -0.15, 0.35),
             knee_l=(0.5, 0.3, 0.4), knee_r=(0.5, -0.2, 0.4), hand_l=(0.1, 0.45, 1.5), hand_r=(0.0, -0.45, 1.45))
    hook = air(spin=-540, pelvis=(0.25, 0, 0.38), pelvis_rot=(-90, 0, 40), chest=(-20, -10, -15), foot_r=None, foot_r_abs=(1.45, 0.05, 1.60),
               foot_r_rot=(0, -60, 0), knee_r=(0.0, -0.5, 0.6), foot_l=(0.20, 0.10, 0.50), hand_l=(0.30, 0.40, 1.60), hand_r=(-0.20, -0.50, 1.35), head=(-80, 0, 0))
    land = s(pelvis=(0.1, 0, -0.30), chest=(s["chest"][0], 25, 0), spin=-720, pivot=(0.05, 0.0), foot_r_abs=None)
    out["S"] = ([(1, hk, "smooth"), (5, hk(pelvis=(0.0, 0, -0.18), chest=(20, 15, 0)), "in"), (8, takeoff, "smooth"), (16, air, "linear"),
                 (26, hook, "snap"), (28, hook(spin=-575, foot_r_abs=(1.30, -0.25, 1.55)), "linear"), (32, air(spin=-680, pelvis=(0.15, 0, 0.0), foot_r=(0.0, -0.18, 0.15), foot_r_abs=None), "smooth"),
                 (38, land, "out"), (58, s(spin=-720), "smooth")], 58, m["S"]["travel"], False)
    # Toward + Special: tornado kick. Travelling jump, spin a full turn, roundhouse at head height on frame 13.
    tk = s(gaze=0.0)
    out["FS"] = ([(1, tk, "smooth"), (4, tk(spin=-120, pelvis=(0.05, 0, -0.22), chest=(0, 15, 0), head=(-60, 0, 0)), "in"),
                  (9, tk(spin=-260, pelvis=(0.10, 0, 0.30), foot_l=(0.20, 0.10, 0.6), foot_r=(0.0, -0.15, 0.45), hand_l=(0.0, 0.45, 1.5), hand_r=(0.0, -0.45, 1.5)), "smooth"),
                  (13, tk(spin=-345, pelvis=(0.12, 0, 0.35), pelvis_rot=(30, 0, 30), foot_r=None, foot_r_abs=(1.05, 0.10, 1.50), foot_r_rot=(60, -70, 0),
                          foot_l=(0.10, 0.10, 0.55), knee_r=(0.5, 0.0, 1.0), hand_l=(0.25, 0.30, 1.55), hand_r=(-0.3, -0.4, 1.2)), "snap"),
                  (18, tk(spin=-360, pelvis=(0.05, 0, -0.25), foot_r_abs=None, foot_r=s["foot_r"], foot_l=s["foot_l"], chest=(s["chest"][0], 25, 0)), "smooth"),
                  (39, s(spin=-360), "smooth")], 39, m["FS"]["travel"], False)
    # Away + Special: Spirit Enhanced Strikes. Sink and gather, then rise and open as the aura applies on frame 24.
    gather = s(pelvis=(-0.02, 0, -0.26), chest=(0, 25, 0), head=(0, 25, 0), hand_l=(0.10, 0.20, 0.95), hand_r=(0.05, -0.20, 0.95),
               elbow_l=(-0.3, 0.4, -0.2), elbow_r=(-0.3, -0.4, -0.2), gaze=0.6)
    rise = s(pelvis=(0.0, 0, -0.06), pelvis_rot=(-25, -5, 0), chest=(0, -12, 0), head=(0, -18, 0), hand_l=(0.20, 0.45, 1.05), hand_r=(0.10, -0.45, 1.05),
             elbow_l=(-0.1, 0.5, -0.4), elbow_r=(-0.1, -0.5, -0.4))
    out["BS"] = ([(1, s, "smooth"), (12, gather, "smooth"), (20, gather(head=(0, 15, 0)), "smooth"), (24, rise, "snap"), (32, rise, "hold"), (44, s, "smooth")], 44, None, False)
    # Grab: the double-leg shot. A level change (hips drop, back straight, head up) and a penetration step with the
    # lead knee driving forward, both hands reaching behind the opponent's knees; whiffed, she recovers her stance.
    level = w(pelvis=(0.04, 0, -0.30), chest=(-4, 30, 0), head=(0, -18, 0), hand_l=(0.40, 0.18, 0.95), hand_r=(0.34, -0.16, 0.98), fist=0.3)
    reach = w(pelvis=(0.16, 0, -0.40), pelvis_rot=(-10, 30, 0), chest=(0, 34, 0), head=(0, -22, 0), hand_l=(0.66, 0.20, 0.62), hand_r=(0.66, -0.16, 0.62),
              fist=0.0, gaze=1.0, elbow_l=(0.0, 0.6, -0.4), elbow_r=(0.0, -0.6, -0.4), foot_l_world=(0.55, 0.11, 0.0), knee_l=(0.8, 0.2, -0.2), ball_r=40)
    out["T"] = ([(1, w, "smooth"), (3, level, "smooth"), (5, reach, "smooth"), (7, reach, "hold"), (16, reach(hand_l=(0.50, 0.25, 0.75), hand_r=(0.50, -0.2, 0.78), pelvis=(0.10, 0, -0.32)), "smooth"),
                 (33, w(foot_l_world=(0.55, 0.11, 0.0), foot_r_world=(-0.03, -0.18, 0.0)), "smooth")], 33, None, False)
    # Presentation: entrance, win and time-out loss.
    relaxed = s(pelvis=(0, 0, -0.02), pelvis_rot=(-20, 0, 0), chest=(0, 0, 0), head=(0, -5, 0), hand_l=(0.05, 0.25, 0.85), hand_r=(0.0, -0.25, 0.85), fist=0.4,
                foot_l=(0.15, 0.13, 0.0), foot_r=(-0.12, -0.15, 0.0), ball_r=0, elbow_l=(-0.1, 0.3, -0.5), elbow_r=(-0.1, -0.3, -0.5))
    out["Intro"] = ([(1, relaxed, "smooth"), (30, relaxed(head=(25, -5, 8)), "smooth"), (55, relaxed(head=(-25, -5, -8)), "smooth"),
                     (70, relaxed(chest=(0, 8, 0), hand_l=(0.30, 0.15, 1.10), hand_r=(0.25, -0.15, 1.10)), "smooth"), (90, s, "out"), (121, s, "smooth")], 121, None, False)
    out["Win"] = ([(1, s, "smooth"), (25, relaxed, "smooth"), (45, relaxed(hand_r=(0.10, -0.20, 1.95), elbow_r=(0.0, -0.5, 0.0), chest=(0, -6, 0), head=(0, -12, 0)), "out"),
                   (121, relaxed(hand_r=(0.10, -0.20, 1.95), elbow_r=(0.0, -0.5, 0.0), chest=(0, -6, 0), head=(5, -10, 0)), "smooth")], 121, None, False)
    out["Defeated"] = ([(1, s, "smooth"), (30, relaxed(chest=(0, 30, 0), head=(0, 25, 0), hand_l=(0.25, 0.15, 0.62), hand_r=(0.25, -0.15, 0.62), pelvis=(0, 0, -0.18)), "smooth"),
                        (91, relaxed(chest=(0, 32, 0), head=(0, 28, 0), hand_l=(0.25, 0.15, 0.60), hand_r=(0.25, -0.15, 0.60), pelvis=(0, 0, -0.19)), "smooth")], 91, None, False)
    return out


# ------------------------------------------------------------------------------------------------ Ashka
def ashka_moves(data):
    s = ASHKA
    w = world_feet(s)
    m = {mv["id"]: mv for mv in data["moves"]}
    out = {}
    # Muay Thai rhythm: a slower rock with the lead foot light on the ball.
    out["Idle"] = idle_bounce(s, 96, 0.015, 5)
    out["WalkF"] = walk(s, 18, 0.468, True, data["walkForward"])
    out["WalkB"] = walk(s, 18, 0.414, False, data["walkBack"])
    out["Guard"] = guard(s, ASHKA_GUARD)
    out["BlockHit"] = block_hit(s, ASHKA_GUARD)
    out["HitLight"] = hit_light(s)
    out["HitHeavy"] = hit_heavy(s)
    out["Knockdown"] = knockdown(s)
    out["KnockdownLie"] = knockdown_lie(s)
    out["KnockdownLieRev"] = knockdown_lie(s, head_toward=True)
    out["Getup"] = getup(s, False)
    out["KO"] = ko(s)
    out["ThrowTech"] = tech(s)
    out["DF"] = rolls(s, m["DF"], True)
    out["DB"] = rolls(s, m["DB"], False)
    if "JL" in m:
        out["JL"] = jump_elbow(s, m["JL"])
    out["Crouch"] = crouch_loop(s, ASHKA_CROUCH)
    out["CrouchGuard"] = crouch_loop(s, ASHKA_CROUCH, True)
    out["CrouchBlockHit"] = crouch_block_hit(s, ASHKA_CROUCH)
    out["CrouchHit"] = crouch_hit(s, ASHKA_CROUCH)
    out["KnockdownLaunch"] = knockdown_launch(s)
    # Down + Light: low teep. The lead knee lifts and the ball of the foot drives straight into the opponent's lead
    # shin or knee, the hips pushing in behind it and the long guard staying up; then the foot comes back to its spot.
    c = crouch_pose(s, ASHKA_CROUCH)
    apr, acr = ASHKA_CROUCH["pelvis_rot"], ASHKA_CROUCH["chest"]
    tp = c(foot_l_world=None, foot_l=(1.06, 0.07, 0.24), foot_l_rot=(0, -70, 0), knee_l=(0.8, 0.1, 0.4),
           pelvis=(-0.02, 0, ASHKA_CROUCH["pelvis"][2] + 0.02), pelvis_rot=(apr[0] - 14, apr[1] - 2, 0), chest=(acr[0], acr[1] + 2, 0), ball_r=40)
    halft = c(foot_l_world=None, foot_l=(0.78, 0.08, 0.28), knee_l=(0.85, 0.1, 0.45), pelvis_rot=(apr[0] - 11, apr[1] - 1, 0))
    out["CL"] = ([(1, c, "smooth"), (5, c(foot_l_world=None, foot_l=(0.42, 0.09, 0.30), knee_l=(0.9, 0.1, 0.5), pelvis_rot=(apr[0] - 8, apr[1], 0)), "in"),
                  (7, halft, "linear"), (8, tp, "out"), (10, tp, "hold"), (15, c(foot_l_world=None, foot_l=(0.48, 0.09, 0.22), knee_l=(0.9, 0.1, 0.4)), "smooth"),
                  (20, c(foot_l_world=(ASHKA["foot_l"][0], ASHKA["foot_l"][1], 0.0)), "smooth"), (24, c, "smooth")], 24, None, False)
    # Down + Heavy: rising elbow (sok ngat). Sink on the legs with the rear elbow low and the hips loaded, then drive up
    # through the legs and turn the rear hip over: the right elbow rises straight up the centre line past the
    # opponent's chin to above her own head, the lead forearm covering her face; then the arm comes down into the guard.
    load = c(pelvis=(0.02, 0, ASHKA_CROUCH["pelvis"][2] - 0.03), pelvis_rot=(-40, 24, 0), chest=(-6, 32, 0), hand_r=(0.30, -0.20, 0.78),
             elbow_r=(0.1, -0.8, -0.5), hand_l_head=(0.20, 0.06, -0.06), hand_r_head=None)
    # The forearm stays folded, fist by the ear: the elbow's point is the weapon, rising up the centre line.
    rise = w(pelvis=(0.10, 0, 0.0), pelvis_rot=(15, -2, 0), chest=(22, 4, 0), head=(0, 6, 0), hand_r=(0.28, -0.02, 1.52),
             elbow_r=(0.7, -0.5, 0.6), clav_r=(0, 0, 24), hand_l=(0.30, 0.10, 1.42), elbow_l=(0.5, 0.3, -0.5), ball_r=45, foot_r_rot=(-15, 0, 0),
             foot_l_world=(ASHKA["foot_l"][0] + 0.10, ASHKA["foot_l"][1], 0.0), fist=1.0)
    top = rise(hand_r=(0.22, 0.0, 1.68), elbow_r=(0.6, -0.4, 1.0), chest=(26, -4, 0), head=(0, 0, 0), pelvis=(0.09, 0, 0.02), clav_r=(0, 0, 30))
    settle = w(pelvis=(0.04, 0, -0.06), pelvis_rot=(-5, 0, 0), chest=(8, 8, 0), hand_r=(0.30, -0.10, 1.40), elbow_r=(0.4, -0.3, -0.6),
               foot_l_world=(ASHKA["foot_l"][0] + 0.10, ASHKA["foot_l"][1], 0.0), ball_r=10)
    # The rear hand comes up past the chest with the elbow still out to the side, then the elbow lifts.
    lift = load(hand_r=(0.32, -0.14, 1.08), elbow_r=(0.4, -0.8, -0.2), elbow_l=(0.45, 0.35, -0.6), pelvis=(0.04, 0, ASHKA_CROUCH["pelvis"][2] + 0.05))
    out["U"] = ([(1, c, "smooth"), (4, load, "in"), (5, lift, "smooth"), (9, rise, "linear"), (12, top, "out"), (18, top, "hold"), (30, settle, "smooth"),
                 (48, w(foot_l_world=(ASHKA["foot_l"][0] + 0.10, ASHKA["foot_l"][1], 0.0)), "smooth")], 48, m["U"]["travel"], False)
    jab = w(hand_l=(0.66, 0.06, 1.44), pelvis_rot=(-15, 4, 0), chest=(-6, 6, 0), clav_l=(-16, 0, 0), elbow_l=(-0.1, 0.45, -0.3), foot_l_world=(0.26, 0.09, 0.0))
    out["L1"] = ([(1, w, "smooth"), (3, w(hand_l=(0.33, 0.11, 1.40)), "in"), (5, jab, "snap"), (7, jab, "hold"),
                  (14, w(foot_l_world=(0.26, 0.09, 0.0), foot_r_world=(-0.17, -0.12, 0.0)), "smooth")], 14, m["L1"]["travel"], False)
    # Light 2: stepping horizontal elbow with the rear arm, swinging across at head height.
    elbow = w(hand_r=(0.20, 0.18, 1.45), elbow_r=(0.6, -0.1, 0.05), pelvis_rot=(15, 6, 0), chest=(25, 8, 0), clav_r=(20, 0, 10), hand_l=(0.20, 0.14, 1.45),
              foot_l_world=(0.50, 0.09, 0.0), ball_r=35, foot_r_rot=(-10, 0, 0))
    out["L2"] = ([(1, w, "smooth"), (3, w(hand_r=(0.15, -0.20, 1.45), elbow_r=(0.1, -0.6, 0.1), pelvis_rot=(-30, 4, 0), foot_l_world=(0.35, 0.09, 0.04)), "in"),
                  (6, elbow, "snap"), (8, elbow(hand_r=(0.15, 0.25, 1.42)), "linear"),
                  (17, w(foot_l_world=(0.50, 0.09, 0.0), foot_r_world=(0.07, -0.12, 0.0)), "smooth")], 17, m["L2"]["travel"], False)
    # Light 3: step-in knee. Hands pull down as the rear knee drives up and through.
    knee = w(foot_r_world=None, foot_r=(0.20, -0.05, 0.55), knee_r=(0.8, 0.0, 0.6), pelvis=(0.05, 0, -0.02), pelvis_rot=(-10, -12, 0), chest=(0, 18, 0),
             hand_l=(0.45, 0.12, 1.20), hand_r=(0.45, -0.10, 1.22), fist=0.4, ball_l=35, foot_l_world=(0.45, 0.09, 0.0))
    out["L3"] = ([(1, w, "smooth"), (4, w(hand_l=(0.48, 0.12, 1.42), hand_r=(0.46, -0.10, 1.42), foot_l_world=(0.40, 0.09, 0.0)), "in"),
                  (8, knee, "snap"), (10, knee, "hold"), (17, knee(foot_r=(-0.05, -0.12, 0.25)), "smooth"),
                  (27, w(foot_l_world=(0.45, 0.09, 0.0), foot_r_world=(0.02, -0.12, 0.0)), "smooth")], 27, m["L3"]["travel"], False)
    # Heavy: Muay Thai body kick. Swing the rear leg like a bat, hips turning over, shin into the ribs on frame 11.
    load = w(pelvis=(0.0, 0, -0.04), pelvis_rot=(-30, 0, 0), ball_l=40, foot_l_rot=(20, 0, 0), hand_r=(0.10, -0.25, 1.15), chest=(10, 0, 0))
    kick = load(pelvis=(0.02, 0, 0.0), pelvis_rot=(60, -8, 25), chest=(-25, -6, -10), foot_r_world=None, foot_r=(0.85, 0.30, 1.00),
                knee_r=(0.3, 0.2, 1.0), foot_r_rot=(80, -70, 0), hand_r=(-0.40, -0.25, 0.90), hand_l=(0.25, 0.15, 1.48), foot_l_rot=(80, 0, 0), ball_l=50)
    out["H"] = ([(1, w, "smooth"), (5, load, "in"), (11, kick, "snap"), (13, kick(foot_r=(0.70, 0.45, 0.98)), "linear"),
                 (20, load(foot_r_world=None, foot_r=(0.05, -0.12, 0.30), pelvis_rot=(0, 0, 0)), "smooth"), (32, w(foot_r_world=s["foot_r"]), "smooth")],
                32, m["H"]["travel"], False)
    # Toward + Heavy: teep. Lead knee chambers high, ball of the foot drives straight out, lean back slightly.
    chamber = w(foot_l_world=None, foot_l=(0.30, 0.09, 0.55), knee_l=(0.8, 0.1, 0.6), pelvis_rot=(-30, -8, 0), chest=(0, -6, 0), ball_r=0)
    teep = chamber(foot_l=(1.15, 0.05, 1.00), foot_l_rot=(0, -80, 0), knee_l=(0.6, 0.1, 1.0), pelvis=(-0.05, 0, 0.0), pelvis_rot=(-35, -18, 0),
                   chest=(0, -10, 0), hand_l=(0.30, 0.15, 1.45), hand_r=(0.15, -0.12, 1.45))
    out["FH"] = ([(1, w, "smooth"), (5, chamber, "in"), (9, teep, "snap"), (11, teep, "hold"), (17, chamber(foot_l=(0.40, 0.09, 0.40)), "smooth"),
                  (28, w(foot_l_world=(0.30, 0.09, 0.0)), "smooth")], 28, m["FH"]["travel"], False)
    # Away + Light: front kick (character sheet, 2026-11-09). A quick lead-leg snap kick, unlike the teep's push: the
    # knee chambers high, the ball of the foot snaps up into the body at chest height on frame 10 (the first active
    # frame), the guard stays up and the torso leans back a little; then the foot comes straight back to its spot.
    if "BL" in m:
        fk_ch = w(foot_l_world=None, foot_l=(0.34, 0.09, 0.52), knee_l=(0.8, 0.1, 0.62), pelvis_rot=(-22, -6, 0), chest=(0, -4, 0),
                  ball_r=10, hand_l=(0.36, 0.08, 1.45), hand_r=(0.26, -0.11, 1.46))
        # The foot stays within the leg's reach (a target past it snapped the straightened leg 70 cm in one frame);
        # the hips drive in a little instead of leaning away.
        fk = fk_ch(foot_l=(0.92, 0.06, 1.04), foot_l_rot=(0, -55, 0), knee_l=(0.62, 0.1, 1.0), pelvis=(0.02, 0, 0.0),
                   pelvis_rot=(-28, -12, 0), chest=(0, -8, 0), hand_l=(0.32, 0.14, 1.45), hand_r=(0.18, -0.12, 1.48))
        # The extension runs linear over three frames into contact on frame 10: a "snap" moved the foot 79 cm in one
        # frame and an "out" (70% of its travel in the first frame) 55 cm.
        out["BL"] = ([(1, w, "smooth"), (4, fk_ch(foot_l=(0.30, 0.09, 0.36), knee_l=(0.85, 0.1, 0.5)), "in"), (7, fk_ch, "linear"),
                      (10, fk, "linear"), (11, fk, "hold"), (15, fk_ch(foot_l=(0.40, 0.09, 0.42)), "smooth"),
                      (26, w(foot_l_world=(s["foot_l"][0] + sum((g["frames"][1] - g["frames"][0] + 1) * g["vx"] for g in m["BL"]["travel"]) / 100.0,
                                           s["foot_l"][1], 0.0)), "smooth")], 26, m["BL"]["travel"], False)
    # Away + Heavy: spinning elbow (sok klap; character sheet, 2026-11-09). The lead foot steps across onto a pivot with
    # the travel and turns on its ball while the back turns through (clockwise); the right elbow slashes round at head
    # height on frame 14 (the first active frame) with the right side to the opponent, the forearm folded in front of
    # the right shoulder and the left hand guarding the face; the rear foot swings round at hip width and lands back in
    # stance, and the lead foot steps back out. Built on the same rules as Wren's spinning back elbow (keyed spin from 0,
    # a flowing turn, the elbow dropping under the arm on the way back to the guard), timed and placed for Ashka.
    if "BH" in m:
        tb = sum((g["frames"][1] - g["frames"][0] + 1) * g["vx"] for g in m["BH"]["travel"]) / 100.0
        piv = (0.26 + tb, 0.02)
        across = (piv[0] - 0.11, piv[1], 0.0)
        home_l = (s["foot_l"][0] + tb, s["foot_l"][1], 0.0)
        sb = w(spin=0.0, pivot=piv, pivot_world=True, foot_l_world=across, foot_r_world=None, foot_r=(s["foot_r"][0] - 0.035, s["foot_r"][1], 0.0),
               knee_l=(0.6, 0.3, 0.0), knee_r=(0.5, -0.5, 0.0))
        el = sb(spin=-200, hand_r=(-0.07, -0.17, 1.46), elbow_r=(-0.8, -0.30, 0.50), hand_l=(0.20, -0.08, 1.47),
                chest=(-15, 8, 0), head=(-60, 6, 0), gaze=0.0, foot_r=(-0.08, -0.20, 0.07))
        # Keys two frames apart through the strike, as in Wren's (three apart, the arm bunched its travel into the middle
        # frame: an elbow flip in the audit); Ashka's longer move spends its extra frames in the step-in and the recovery.
        out["BH"] = ([(1, w, "smooth"),
                      (4, w(foot_l_world=((s["foot_l"][0] + across[0]) / 2, (s["foot_l"][1] + across[1]) / 2, 0.04), chest=(8, 6, 0), knee_l=(0.6, 0.2, 0.0)), "smooth"),
                      (7, sb(chest=(12, 8, 0)), "smooth"),
                      (10, sb(spin=-60, chest=(20, 10, 0), hand_r=(0.10, 0.05, 1.38), gaze=0.4, foot_r=(-0.14, -0.20, 0.06)), "smooth"),
                      (12, sb(spin=-130, chest=(5, 9, 0), hand_r=(0.06, 0.02, 1.40), elbow_r=(-0.5, -0.45, 0.05), hand_l=(0.30, 0.02, 1.44),
                              head=(-35, 4, 0), gaze=0.0, foot_r=(-0.10, -0.20, 0.07)), "smooth"),
                      # Mid-turn the forearm stays folded so the elbow leads (between the keys either side it swung
                      # out from the body and folded back, 36 cm in a frame).
                      (13, sb(spin=-165, hand_r=(0.0, -0.08, 1.43), elbow_r=(-0.68, -0.38, 0.28), hand_l=(0.25, -0.03, 1.46),
                              chest=(-5, 8, 0), head=(-48, 5, 0), gaze=0.0, foot_r=(-0.09, -0.20, 0.07)), "smooth"),
                      (14, el, "smooth"), (16, el(spin=-225, head=(-55, 6, 0)), "smooth"),
                      (18, sb(spin=-265, hand_r=(0.02, -0.16, 1.44), elbow_r=(-0.6, -0.55, -0.1), hand_l=(0.30, 0.0, 1.43),
                              head=(-35, 5, 0), gaze=0.15, foot_r=(-0.14, -0.20, 0.06)), "smooth"),
                      (20, sb(spin=-305, hand_r=(0.20, -0.10, 1.40), elbow_r=(-0.1, -0.4, -0.8), hand_l=(0.38, 0.04, 1.40),
                              head=(-20, 4, 0), gaze=0.4, foot_r=(-0.18, -0.20, 0.06)), "smooth"),
                      (21, sb(spin=-330, gaze=0.6, foot_r=(-0.20, -0.20, 0.05)), "smooth"),
                      (25, sb(spin=-360, foot_r=s["foot_r"]), "smooth"),
                      (30, sb(spin=-360, foot_l_world=((across[0] + home_l[0]) / 2, (across[1] + home_l[1]) / 2, 0.05)), "smooth"),
                      (35, sb(spin=-360, foot_l_world=home_l), "smooth"),
                      (40, sb(spin=-360, foot_l_world=home_l), "smooth")], 40, m["BH"]["travel"], False)
    # Special: Flame Elbow. Two quick steps, leap, chop the right elbow down onto the head on frame 12.
    up = s(pelvis=(0.10, 0, 0.18), chest=(10, -5, 0), hand_r=(0.10, -0.15, 1.85), elbow_r=(0.2, -0.3, 0.6), hand_l=(0.30, 0.15, 1.40),
           foot_l=(0.30, 0.09, 0.30), foot_r=(-0.10, -0.12, 0.20))
    chop = up(pelvis=(0.12, 0, -0.05), pelvis_rot=(20, 15, 0), chest=(25, 30, 0), hand_r=(0.30, 0.10, 1.25), elbow_r=(0.6, -0.1, 0.2), head=(0, 10, 0),
              foot_l=(0.40, 0.09, 0.0), foot_r=(-0.10, -0.12, 0.05))
    out["S"] = ([(1, s, "smooth"), (5, s(pelvis=(0.0, 0, -0.15), hand_r=(0.10, -0.20, 1.50)), "in"), (9, up, "out"), (12, chop, "snap"), (14, chop, "hold"),
                 (24, s(pelvis=(0.0, 0, -0.16), chest=(10, 20, 0)), "smooth"), (39, s, "smooth")], 39, m["S"]["travel"], False)
    # Toward + Special: flying knee. Run-in, jump off the lead foot, rear knee to the chin on frame 15.
    fly = s(pelvis=(0.15, 0, 0.32), pelvis_rot=(-10, -15, 0), chest=(0, 10, 0), foot_r=(0.30, -0.05, 0.70), knee_r=(0.9, 0.0, 0.7),
            foot_l=(-0.15, 0.09, 0.30), hand_l=(0.50, 0.15, 1.45), hand_r=(0.48, -0.12, 1.45), fist=0.3)
    out["FS"] = ([(1, s, "smooth"), (5, s(pelvis=(0.05, 0, -0.18), chest=(0, 20, 0)), "in"), (10, fly(pelvis=(0.10, 0, 0.15), foot_r=(0.10, -0.08, 0.40)), "out"),
                  (15, fly, "snap"), (17, fly, "hold"), (20, s(pelvis=(0.05, 0, -0.25), chest=(0, 22, 0)), "in"), (41, s, "smooth")], 41, m["FS"]["travel"], False)
    # Away + Special: Flame Burst. Coil, then thrust both palms out as the crimson flame erupts on frame 7.
    coil = s(pelvis=(-0.02, 0, -0.22), chest=(0, 22, 0), hand_l=(0.15, 0.12, 1.10), hand_r=(0.15, -0.12, 1.10), fist=0.0, head=(0, 15, 0))
    burst = s(pelvis=(0.04, 0, -0.10), chest=(0, -8, 0), head=(0, -10, 0), hand_l=(0.55, 0.30, 1.35), hand_r=(0.55, -0.28, 1.30), fist=0.0,
              elbow_l=(-0.2, 0.5, -0.3), elbow_r=(-0.2, -0.5, -0.3))
    # The thrust takes three frames on an "out" (fast, still landing on frame 7); a "snap" over two moved the palms 48 cm
    # in one frame. Coming back, the hands stop a little further out than the coil: folded right back to the shoulder the
    # arm has no defined bend, and the elbow swung 42 cm in one frame.
    settle = coil(pelvis=(-0.05, 0, -0.15), hand_l=(0.28, 0.14, 1.08), hand_r=(0.28, -0.14, 1.08))
    out["BS"] = ([(1, s, "smooth"), (4, coil, "smooth"), (7, burst, "out"), (18, burst, "hold"), (30, settle, "smooth"), (49, s, "smooth")], 49, None, False)
    # Grab: reach for a plum clinch behind the opponent's head.
    reach = w(pelvis=(0.08, 0, -0.04), chest=(10, 10, 0), hand_l=(0.55, 0.10, 1.45), hand_r=(0.55, -0.08, 1.45), fist=0.0,
              elbow_l=(0.3, 0.2, -0.4), elbow_r=(0.3, -0.2, -0.4), foot_l_world=(0.32, 0.09, 0.0))
    out["T"] = ([(1, w, "smooth"), (5, reach, "snap"), (7, reach, "hold"), (15, reach(hand_l=(0.40, 0.12, 1.40), hand_r=(0.40, -0.10, 1.40)), "smooth"),
                 (32, w(foot_l_world=(0.32, 0.09, 0.0), foot_r_world=(-0.11, -0.12, 0.0)), "smooth")], 32, None, False)
    calm = s(pelvis=(0, 0, 0.0), pelvis_rot=(0, 0, 0), chest=(0, 0, 0), head=(0, 0, 0), hand_l=(0.05, 0.20, 0.82), hand_r=(0.05, -0.20, 0.82), fist=0.2,
             foot_l=(0.05, 0.10, 0.0), foot_r=(-0.05, -0.10, 0.0), ball_l=0, foot_l_rot=(0, 0, 0), foot_r_rot=(0, 0, 0),
             elbow_l=(-0.1, 0.25, -0.5), elbow_r=(-0.1, -0.25, -0.5))
    # A short, respectful bow with pressed palms, then the guard comes up.
    bow = calm(hand_l=(0.25, 0.02, 1.30), hand_r=(0.25, -0.02, 1.30), fist=0.0, chest=(0, 25, 0), head=(0, 20, 0), elbow_l=(0.1, 0.4, -0.4), elbow_r=(0.1, -0.4, -0.4))
    out["Intro"] = ([(1, calm, "smooth"), (30, calm(hand_l=(0.25, 0.02, 1.30), hand_r=(0.25, -0.02, 1.30), fist=0.0), "smooth"), (50, bow, "smooth"),
                     (70, bow(chest=(0, 4, 0), head=(0, 0, 0)), "smooth"), (92, s, "smooth"), (121, s, "smooth")], 121, None, False)
    out["Win"] = ([(1, s, "smooth"), (30, calm, "smooth"), (55, bow, "smooth"), (121, bow(chest=(0, 18, 0), head=(0, 14, 0)), "smooth")], 121, None, False)
    out["Defeated"] = ([(1, s, "smooth"), (30, calm(chest=(0, 22, 0), head=(0, 30, 0), pelvis=(0, 0, -0.03)), "smooth"),
                        (91, calm(chest=(0, 24, 0), head=(0, 32, 0), pelvis=(0, 0, -0.03)), "smooth")], 91, None, False)
    return out
