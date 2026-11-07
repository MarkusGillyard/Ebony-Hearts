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


def guard(s, high):
    g = s(pelvis=(s["pelvis"][0] - 0.02, 0, s["pelvis"][2] - 0.04), chest=(s["chest"][0], s["chest"][1] + 10, s["chest"][2]), head=(0, 12, 0),
          hand_l=high[0], hand_r=high[1], elbow_l=(0.35, 0.12, -0.5), elbow_r=(0.35, -0.12, -0.5), clav_l=(0, 0, 8), clav_r=(0, 0, -8))
    breathe = g(pelvis=(g["pelvis"][0], 0, g["pelvis"][2] - 0.015), chest=(g["chest"][0] - 2, g["chest"][1] + 2, 0))
    return [(1, g, "smooth"), (21, breathe, "smooth"), (41, g, "smooth")], 41, None, True


def block_hit(s, high):
    g = guard(s, high)[0][0][1]
    hit = g(pelvis=(g["pelvis"][0] - 0.07, 0, g["pelvis"][2] - 0.02), chest=(g["chest"][0], g["chest"][1] - 8, 0), head=(0, 2, 0),
            hand_l=(high[0][0] - 0.06, high[0][1], high[0][2] + 0.02), hand_r=(high[1][0] - 0.06, high[1][1], high[1][2] + 0.02))
    return [(1, g, "smooth"), (3, hit, "snap"), (9, hit(pelvis=(g["pelvis"][0] - 0.04, 0, g["pelvis"][2])), "smooth"), (18, g, "smooth")], 18, None, False


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


# ------------------------------------------------------------------------------------------------ Wren
def wren_moves(data):
    s = WREN
    w = world_feet(s)
    m = {mv["id"]: mv for mv in data["moves"]}
    out = {}
    out["Idle"] = idle_bounce(s, 72, 0.025, 3)
    out["WalkF"] = walk(s, 16, 0.448, True, data["walkForward"])
    out["WalkB"] = walk(s, 16, 0.384, False, data["walkBack"])
    high = ((0.20, 0.11, 1.52), (0.17, -0.07, 1.53))
    out["Guard"] = guard(s, high)
    out["BlockHit"] = block_hit(s, high)
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
    # Grab: shoot both hands to the opponent's waist; whiff recovery.
    reach = w(pelvis=(0.10, 0, -0.18), chest=(20, 25, 0), hand_l=(0.55, 0.20, 1.05), hand_r=(0.55, -0.18, 1.05), fist=0.0, gaze=1.0,
              elbow_l=(0.0, 0.5, -0.3), elbow_r=(0.0, -0.5, -0.3), foot_l_world=(0.40, 0.11, 0.0))
    out["T"] = ([(1, w, "smooth"), (5, reach, "snap"), (7, reach, "hold"), (16, reach(hand_l=(0.40, 0.25, 1.0), hand_r=(0.40, -0.2, 1.0)), "smooth"),
                 (33, w(foot_l_world=(0.40, 0.11, 0.0), foot_r_world=(-0.18, -0.18, 0.0)), "smooth")], 33, None, False)
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
    high = ((0.24, 0.10, 1.53), (0.20, -0.06, 1.53))
    out["Guard"] = guard(s, high)
    out["BlockHit"] = block_hit(s, high)
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
