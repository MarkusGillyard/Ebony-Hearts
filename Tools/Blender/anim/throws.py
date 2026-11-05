"""Paired throw animations. The thrower is authored in its own character space; the victim in *its* character
space, standing at the throw's holdX in front of the thrower and facing it. A point (f, l, u) in thrower space is
(hold - f, -l, u) in victim space.

Each victim animation ends exactly where the knockdown animation starts after the simulation moves the victim's root
to landX: lying on the back with the head away from the thrower. Back throws switch sides, so the victim ends
rotated 180 degrees about the landing point, and the thrower ends turned around (both flip facing on landing).
"""
from moves import ASHKA, WREN, lying, unrel, world_feet


def tv(hold, f, l, u):
    """Thrower-space point to victim space."""
    return (hold - f, -l, u)


def landed(victim, hold, land_x):
    """Victim's final lying pose in its pre-landing frame."""
    d = land_x - hold                # how far the root moves along the thrower's forward axis
    lie = lying(victim)
    if land_x > 0:
        # Lands in front of the thrower, further away: backwards in the victim's frame.
        return lie(pelvis=(lie["pelvis"][0] - d, 0.0, lie["pelvis"][2]),
                   foot_l=(lie["foot_l"][0] - d, lie["foot_l"][1], lie["foot_l"][2]),
                   foot_r=(lie["foot_r"][0] - d, lie["foot_r"][1], lie["foot_r"][2]))
    # Lands behind the thrower: forward in the victim's frame, and turned around (the side switch).
    reach = -d
    return lie(spin=180.0, pivot=(reach / 2.0, 0.0))


def victim_recoil(v, hold, hands_u=1.10):
    return v(gaze=0.0, fist=0.3, hand_l=tv(hold, 0.20, 0.20, hands_u), hand_r=tv(hold, 0.20, -0.20, hands_u),
             elbow_l=(0.2, 0.5, -0.2), elbow_r=(0.2, -0.5, -0.2), chest=(0, -10, 0), head=(0, -15, 0))


# ------------------------------------------------------------------------------------------------ Wren
def wren_double_leg(victim, td):
    hold, land = td["holdX"] / 100.0, td["landX"] / 100.0
    t = world_feet(WREN)
    shoot = t(pelvis=(0.10, 0, -0.38), chest=(15, 40, 0), head=(0, -20, 0), gaze=1.0, fist=0.2,
              hand_l=(hold - 0.10, 0.16, 0.62), hand_r=(hold - 0.10, -0.16, 0.62), elbow_l=(0.0, 0.5, -0.1), elbow_r=(0.0, -0.5, -0.1),
              foot_l_world=(0.45, 0.12, 0.0), knee_l=(0.6, 0.3, 0.2))
    lift = shoot(pelvis=(0.12, 0, -0.18), chest=(10, 20, 0), hand_l=(hold - 0.05, 0.16, 0.95), hand_r=(hold - 0.05, -0.16, 0.95))
    corner = lift(pelvis=(0.18, 0, -0.10), chest=(5, 5, 0), hand_l=(hold + 0.05, 0.16, 1.25), hand_r=(hold + 0.05, -0.16, 1.25),
                  foot_l_world=(0.55, 0.12, 0.0))
    slam = corner(pelvis=(0.22, 0, -0.32), chest=(10, 50, 0), hand_l=(land - 0.25, 0.16, 0.35), hand_r=(land - 0.25, -0.16, 0.35), head=(0, -10, 0))
    attacker = [(1, t, "smooth"), (5, shoot, "snap"), (16, lift, "smooth"), (28, corner, "smooth"), (34, slam, "in"),
                (40, slam, "hold"), (56, t, "smooth")]
    v = victim
    grabbed = victim_recoil(v, hold)(pelvis=(-0.04, 0, -0.04))
    up = grabbed(pelvis=(-0.10, 0, 0.30), pelvis_rot=(0, -55, 0), chest=(0, -25, 0), head=(0, -20, 0),
                 foot_l=tv(hold, hold - 0.05, 0.12, 0.85), foot_r=tv(hold, hold - 0.05, -0.12, 0.80), knee_l=(0.3, 0.2, 0.6), knee_r=(0.3, -0.2, 0.6))
    over = up(pelvis=(-0.30, 0, 0.30), pelvis_rot=(0, -85, 0), foot_l=tv(hold, hold + 0.05, 0.12, 1.25), foot_r=tv(hold, hold + 0.05, -0.12, 1.20),
              hand_l=(-0.4, 0.4, 1.2), hand_r=(-0.4, -0.4, 1.2))
    end = landed(v, hold, land)
    victim_keys = [(1, v, "smooth"), (6, grabbed, "snap"), (16, up, "smooth"), (28, over, "smooth"), (34, end(head=(0, 20, -6)), "in"),
                   (40, end(pelvis=(end["pelvis"][0], 0, end["pelvis"][2] + 0.04)), "out"), (56, end, "smooth")]
    return attacker, victim_keys


def wren_suplex(victim, td):
    hold, land = td["holdX"] / 100.0, td["landX"] / 100.0
    t = world_feet(WREN)(spin=0.0)    # the turn after the impact starts from 0, so it is interpolated, not a snap
    lock = t(pelvis=(0.10, 0, -0.10), chest=(10, 15, 0), gaze=1.0, fist=0.0, hand_l=(hold + 0.10, 0.20, 1.00), hand_r=(hold + 0.10, -0.20, 1.00),
             elbow_l=(0.0, 0.5, -0.2), elbow_r=(0.0, -0.5, -0.2), foot_l_world=(0.40, 0.12, 0.0))
    dip = lock(pelvis=(0.12, 0, -0.30), chest=(0, 10, 0))
    arch = dip(pelvis=(0.02, 0, -0.10), pelvis_rot=(-38, -35, 0), chest=(0, -45, 0), head=(0, -30, 0), gaze=0.0,
               hand_l=(-0.20, 0.25, 1.70), hand_r=(-0.20, -0.25, 1.70))
    impact = arch(pelvis=(-0.10, 0, -0.35), pelvis_rot=(-38, -55, 0), chest=(0, -40, 0), hand_l=(land + 0.4, 0.25, 0.5), hand_r=(land + 0.4, -0.25, 0.5))
    # She turns round on the balls of her feet, lifting them mid-turn, and settles into her stance facing back.
    turning = impact(spin=90.0, pelvis=(-0.05, 0, -0.28), pelvis_rot=(-20, -20, 0), chest=(0, -10, 0), head=(0, -10, 0),
                     foot_l_world=(0.36, 0.14, 0.06), foot_r_world=(-0.24, -0.16, 0.06), hand_l=(0.30, 0.25, 0.9), hand_r=(0.30, -0.25, 0.9))
    turned = unrel(t(spin=180.0, pelvis=(0.0, 0, -0.20), chest=(WREN["chest"][0], 25, 0)))
    attacker = [(1, t, "smooth"), (6, lock, "snap"), (14, dip, "smooth"), (24, arch, "smooth"), (38, impact, "in"),
                (43, turning, "smooth"), (48, turned, "smooth"), (60, unrel(t(spin=180.0, foot_l_world=None, foot_r_world=None)), "smooth")]
    v = victim(spin=0.0, pivot=((hold - land) / 2.0, 0.0))   # the landing's side switch turns in, not a snap
    held = victim_recoil(v, hold, 1.35)(pelvis=(0.06, 0, -0.02))
    lifted = held(pelvis=(0.10, 0, 0.30), pelvis_rot=(0, -20, 0), foot_l=(0.05, 0.12, 0.30), foot_r=(0.0, -0.12, 0.28))
    inverted = lifted(pelvis=(0.55, 0, 0.75), pelvis_rot=(0, -175, 0), chest=(0, -10, 0), foot_l=None, foot_r=None,
                      foot_l_rel=(0.0, 0.12, -0.80), foot_r_rel=(0.0, -0.12, -0.80), hand_l=None, hand_r=None,
                      hand_l_rel=(0.0, 0.35, 0.30), hand_r_rel=(0.0, -0.35, 0.30), knee_follow_pelvis=True)
    end = landed(v, hold, land)
    victim_keys = [(1, v, "smooth"), (6, held, "snap"), (14, lifted, "smooth"), (24, inverted, "smooth"),
                   (38, end(head=(0, 20, -6), knee_follow_pelvis=False), "in"), (44, end, "out"), (60, end, "smooth")]
    return attacker, victim_keys


# ------------------------------------------------------------------------------------------------ Ashka
def ashka_clinch_knees(victim, td):
    hold, land = td["holdX"] / 100.0, td["landX"] / 100.0
    t = world_feet(ASHKA)
    plum = t(pelvis=(0.04, 0, -0.04), chest=(5, 12, 0), fist=0.0, gaze=1.0, hand_l=(hold - 0.06, 0.08, 1.45), hand_r=(hold - 0.06, -0.08, 1.45),
             elbow_l=(0.4, 0.15, -0.3), elbow_r=(0.4, -0.15, -0.3), foot_l_world=(0.25, 0.09, 0.0))
    pull = plum(hand_l=(hold - 0.10, 0.08, 1.22), hand_r=(hold - 0.10, -0.08, 1.22), chest=(5, 20, 0))
    # The knee and the trip keep the rear foot in world space like the planted keys either side of them (a throw has
    # no root travel, so world and character space agree), so it moves between them instead of holding still and
    # jumping 60-70 cm on the key (a switch of control happens at the key itself).
    knee = pull(foot_r_world=(0.20, -0.05, 0.62), knee_r=(0.9, 0.0, 0.7), pelvis=(0.08, 0, 0.0), pelvis_rot=(-10, -12, 0), ball_l=40)
    down = pull(foot_r_world=(-0.23, -0.12, 0.0))
    trip = down(pelvis=(0.10, 0, -0.10), pelvis_rot=(20, 5, 0), chest=(30, 30, 0), foot_r_world=(0.35, 0.05, 0.10),
                hand_l=(land - 0.30, 0.10, 0.70), hand_r=(land - 0.30, -0.10, 0.70))
    # The knees drive up and the sweep goes through on smooth curves; "snap" put 60% of each in its first frame. The
    # knees come a little closer together so the trip starts at 30 and the victim has 14 frames to fall before landing
    # on the damage frame (44); with 8 it dropped 70 cm a frame.
    attacker = [(1, t, "smooth"), (6, plum, "snap"), (11, pull, "smooth"), (16, knee, "smooth"), (21, down, "smooth"), (26, knee, "smooth"),
                (30, down, "smooth"), (34, trip, "smooth"), (46, trip, "hold"), (64, t(foot_r_world=ASHKA["foot_r"]), "smooth")]
    v = victim
    bent = victim_recoil(v, hold, 1.25)(chest=(0, 40, 0), head=(0, 35, 0), pelvis=(0.0, 0, -0.06))
    jolt = bent(chest=(0, 52, 0), pelvis=(0.0, 0, 0.0), head=(0, 40, 0))
    end = landed(v, hold, land)
    victim_keys = [(1, v, "smooth"), (6, victim_recoil(v, hold), "snap"), (11, bent, "smooth"), (16, jolt, "snap"), (21, bent, "smooth"),
                   (26, jolt, "snap"), (30, bent, "smooth"),
                   # One fall from the held clinch to the floor, accelerating like a falling body from rest as she is
                   # tripped; the hands go out to where the lying pose holds them over the whole fall. Two segments
                   # each starting from rest stalled the body in mid-air.
                   (44, end(head=(0, 20, -6)), "fall"), (50, end, "out"), (64, end, "smooth")]
    return attacker, victim_keys


def ashka_clinch_turn(victim, td):
    hold, land = td["holdX"] / 100.0, td["landX"] / 100.0
    t = world_feet(ASHKA)(spin=0.0)   # both turns start from 0, so they are interpolated, not a snap
    plum = t(pelvis=(0.04, 0, -0.04), chest=(5, 12, 0), fist=0.0, gaze=1.0, hand_l=(hold - 0.06, 0.08, 1.45), hand_r=(hold - 0.06, -0.08, 1.45),
             elbow_l=(0.4, 0.15, -0.3), elbow_r=(0.4, -0.15, -0.3))
    # Feet are placed unspun (foot_*_abs) so a planted foot stays put while she turns: the lead foot pivots in place
    # while the rear foot swings round into the sweep, then the lead foot steps through and the rear foot steps into
    # her stance facing back. Each planted foot turns with her (foot_*_rot) so the leg does not twist.
    fl, fr_ = ASHKA["foot_l"], ASHKA["foot_r"]
    lead = (fl[0], fl[1], 0.0)
    swept = (-0.40, 0.05, 0.0)                                   # the trip leg's spot behind the victim's legs
    pivot = unrel(plum(spin=110.0, foot_l_world=None, foot_r_world=None, pelvis=(0.0, 0, -0.10),
                       foot_l_abs=lead, foot_l_rot=(110, 0, 0), foot_r_abs=(-0.05, -0.30, 0.07), foot_r_rot=(110, 0, 0)))
    trip = pivot(spin=180.0, pelvis=(0.05, 0, -0.18), chest=(10, 35, 0), hand_l=(0.55, 0.10, 0.80), hand_r=(0.55, -0.10, 0.80),
                 foot_l_rot=(180, 0, 0), foot_r_abs=(swept[0], swept[1], 0.08), foot_r_rot=(180, 0, 0))
    planted = trip(chest=(10, 45, 0), foot_r_abs=swept)
    lead_step = planted(foot_l_abs=(0.0, 0.0, 0.08))
    lead_down = planted(foot_l_abs=(-fl[0], -fl[1], 0.0))
    rear_step = lead_down(foot_r_abs=((swept[0] - fr_[0]) / 2, (swept[1] - fr_[1]) / 2, 0.07))
    rear_down = lead_down(foot_r_abs=(-fr_[0], -fr_[1], 0.0))
    attacker = [(1, t, "smooth"), (6, plum, "snap"), (16, pivot, "smooth"), (26, trip, "smooth"), (38, planted, "in"),
                (42, lead_step, "smooth"), (46, lead_down, "smooth"), (49, rear_step, "smooth"), (52, rear_down, "smooth"),
                (56, unrel(t(spin=180.0, foot_l_world=None, foot_r_world=None, foot_l_abs=None, foot_r_abs=None,
                             foot_l_rot=(0, 0, 0), foot_r_rot=(0, 0, 0))), "smooth")]
    v = victim(spin=0.0, pivot=(hold, 0.0))
    held = victim_recoil(v, hold, 1.25)(chest=(0, 30, 0), head=(0, 25, 0))
    # Swung round by the clinch, the victim stumbles: each foot lifts in turn instead of both dragging over the floor.
    lifted = lambda foot, u: (foot[0], foot[1], u)
    stumble_r = held(spin=55.0, pivot=(hold, 0.0), foot_r=lifted(victim["foot_r"], 0.07))
    swung = held(spin=110.0, pivot=(hold, 0.0), pelvis=(0.05, 0, -0.05))
    stumble_l = swung(spin=145.0, foot_l=lifted(victim["foot_l"], 0.07))
    off = held(spin=180.0, pivot=(hold, 0.0), pelvis=(-0.15, 0, -0.10), pelvis_rot=(0, -25, 0), foot_l=(0.25, 0.12, 0.25))
    end = landed(v, hold, land)
    victim_keys = [(1, v, "smooth"), (6, held, "snap"), (11, stumble_r, "smooth"), (16, swung, "smooth"), (21, stumble_l, "smooth"),
                   (26, off, "smooth"), (38, end(head=(0, 20, -6)), "fall"), (44, end, "out"), (56, end, "smooth")]
    return attacker, victim_keys


THROWS = {
    ("wren", "wren_takedown"): wren_double_leg,
    ("wren", "wren_suplex"): wren_suplex,
    ("ashka", "ashka_clinch_knees"): ashka_clinch_knees,
    ("ashka", "ashka_clinch_turn"): ashka_clinch_turn,
}


def stance_of(char):
    return WREN if char == "wren" else ASHKA
