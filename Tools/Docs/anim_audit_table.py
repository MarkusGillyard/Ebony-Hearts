"""Writes Docs/AnimationAudit.md from a clip audit CSV (Tools/Blender/anim/audit_clips.py) and the repository's data.

Usage: python3 Tools/Docs/anim_audit_table.py <audit.csv> <evidence label>
Every exported clip gets a row: how the game reaches it, where its motion comes from, the measured worst values and a
disposition. Clips the measurements flag need a written disposition in DISPOSITIONS (an unexplained flag fails).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "Docs" / "AnimationAudit.md"
CLIPS = json.loads((ROOT / "Tools" / "Blender" / "anim" / "mocap_clips.json").read_text())
DATA = {c: json.loads((ROOT / "Content" / "Data" / "Fighters" / f"{c}.json").read_text()) for c in ("wren", "ashka")}
RULES = json.loads((ROOT / "Content" / "Data" / "rules.json").read_text())

# Hand-written dispositions for clips the measurements flag (or that need a note). Key: clip name without prefix dir.
DISPOSITIONS = {
    "A_Wren_FS": "Tornado kick: a full turn in 10 frames, so the far foot moves up to 90 cm a frame and the trailing knee trips the flip test while the leg swings round. Legitimate speed of a spin, not a skipped sample; lengthening it broke its combos (tried 2026-11-05). Kept.",
    "A_Wren_DF": "Forward roll dive: the hands reach the floor fast (45 cm/f on one frame). Captured (Mixamo Quick Roll To Run); kept.",
    "A_Ashka_DF": "Same captured forward roll on Ashka; kept.",
    "A_Wren_DB": "Back roll: the leg swings over (42 cm/f on one frame). Keyed; kept.",
    "A_Ashka_H": "Body roundhouse (captured): the kicking foot's toes flick on two frames after contact (35 cm/f), smoothed by the transition into recovery in play. Minor; kept.",
    "A_Wren_JH": "Flying kick: the extended foot is 3.7 cm below the clip's floor on frame 20; the game draws jump attacks lifted by the jump height, and the attack ends on landing, so it is above the floor in play. Kept.",
    "A_Wren_U": "New (2026-11-08): keyed rising uppercut. One 21 cm forearm step at the start of the rise (frame 5) stays as the drive begins.",
    "A_Ashka_U": "New (2026-11-08): keyed rising elbow. Rises over frames 5-9; the elbow point peaks near 40 cm/f at the strike.",
    "A_Ashka_BH": "New (2026-11-09): keyed spinning elbow (sok klap). Through the turn the elbow point leads at about 36 cm/f "
                  "into contact while the folded fist and the shoulder stay near the spin axis, which trips the flip test; frames "
                  "11-16 checked: the forearm stays folded and the arm's plane does not flip.",
    "A_Wren_Victim_AshkaThrowC": "New (2026-11-08): keyed clinch-trip fall. Arms follow the torso while falling (pelvis-relative); the left forearm's 21 cm step on frame 17 (the trip taking the legs) trips the flip test; fastest joint is the head landing (33 cm/f, frame 47).",
}
HOLDS = {"Crouch", "CrouchGuard", "KnockdownLie", "KnockdownLieRev", "JL", "CL", "BS", "ThrowF", "ThrowB", "U"}


def runtime_use(char, key, victim_dir):
    data = DATA[char]
    moves = {m["anim"]: m for m in data["moves"]}
    if key.startswith("ThrowTech_from_"):
        anim = key[len("ThrowTech_from_"):].rsplit("_F", 1)[0]
        for owner in ("wren", "ashka"):
            primary = next(m for m in DATA[owner]["moves"] if m["kind"] == "throw")["throw"]
            for t in DATA[owner]["throws"]:
                if anim in (t["attackerAnim"], t["victimAnim"]) and (anim.startswith("Victim_") or owner == char):
                    live = t["id"] == primary and not RULES.get("grappling")
                    return f"escape from {t['name']}" + ("" if live or RULES.get("grappling") else " (dormant: grappling)")
        return "throw escape"
    if key.startswith("Victim_"):
        owner = "wren" if "Wren" in key else "ashka"
        t = next((t for t in DATA[owner]["throws"] if t["victimAnim"] == key), None)
        if t is None:
            return "unused"
        active = next(m for m in DATA[owner]["moves"] if m["kind"] == "throw")["throw"] == t["id"]
        return f"victim of {t['name']}" + ("" if active and not RULES.get("grappling") else " (dormant: grappling)") if active or RULES.get("grappling") else f"victim of {t['name']} (dormant: grappling)"
    for t in data["throws"]:
        if t["attackerAnim"] == key:
            active = next(m for m in data["moves"] if m["kind"] == "throw")["throw"] == t["id"]
            return t["name"] + ("" if active else " (dormant: grappling)")
    if key in moves:
        m = moves[key]
        return f"move {m['id']} ({m['name']})"
    base = key.split("_from_")[0]
    if "_from_" in key and base in moves:
        return f"string variant of {base}"
    states = {"Idle": "neutral", "WalkF": "walk toward", "WalkB": "walk away", "Guard": "standing guard", "BlockHit": "standing blockstun",
              "HitLight": "hitstun (light)", "HitHeavy": "hitstun (heavy)", "Knockdown": "knockdown", "KnockdownLie": "lying after a throw",
              "KnockdownLieRev": "lying head toward (dormant shoulder throw)", "KnockdownLaunch": "uppercut launch knockdown", "Getup": "get-up",
              "GetupRev": "get-up from head toward (dormant)", "KO": "KO", "Win": "round win", "Defeated": "time-out loss", "Intro": "round intro",
              "ThrowTech": "throw escape (fallback)", "Jump": "neutral jump", "JumpF": "forward jump", "JumpB": "back jump", "Land": "landing",
              "Crouch": "crouching", "CrouchGuard": "crouching guard", "CrouchBlockHit": "crouching blockstun", "CrouchHit": "crouching hitstun"}
    if key in states:
        return states[key]
    if key.startswith("Hit"):
        return "hit reaction named by a hit"
    return "unknown"


def source(char, key):
    spec = CLIPS.get(char, {}).get(key)
    if key.startswith("ThrowTech_from_"):
        return "keyed from the throw's frame 2/5/8"
    if key.startswith("Victim_") or key.startswith("ThrowTech_from_") or key.startswith("Throw"):
        owner = char if key.startswith("Throw") and not key.startswith("ThrowTech") else ("wren" if "Wren" in key.split("_from_")[-1] else "ashka")
        for tid, cap in CLIPS.get("throws", {}).items():
            if any(t["id"] == tid and (t["attackerAnim"] in key or t["victimAnim"] in key) for t in DATA[owner]["throws"]):
                return f"captured pair {cap['attacker']}"
        for tid, fall in CLIPS.get("victim_falls", {}).items():
            if any(t["id"] == tid and t["victimAnim"] in key for t in DATA[owner]["throws"]):
                return f"keyed pair, captured fall {fall['fbx']}"
        return "keyed (throws.py)" if not key.startswith("ThrowTech_from_") else "keyed from the throw's frame"
    if spec is None:
        return "keyed (moves.py)"
    if spec.get("scripted"):
        return "keyed (moves.py)"
    return "captured " + (spec.get("fbx") or spec.get("bvh") or spec.get("clip") or "?")


def main():
    rows = list(csv.DictReader(open(sys.argv[1])))
    label = sys.argv[2]
    out = ["# Animation audit", "",
           f"Every clip the build exports, measured from the exported FBX ({label}; `Tools/Blender/anim/audit_clips.py`, regenerated "
           "by `Tools/Docs/anim_audit_table.py`). Units are cm per frame at 60 fps. *Fastest* is the largest single-frame step "
           "of a main joint (a fist or foot peaks near 25-35 cm/f); *pops* are steps over 15 cm more than 3x their neighbours; "
           "*held* is the share of frames with no joint moving 0.05 cm (frozen or duplicated samples show up here; deliberate "
           "holds are marked); *flips* are elbows or knees moving 20 cm and 2.5x both neighbours; *floor* is the lowest point "
           "of the body. A row is *checked* when nothing is flagged; flagged rows carry a disposition.", "",
           "Runtime behaviour checked with these clips: samples are taken at the simulation frame plus the render alpha "
           "(`EHFighterVisual`), frozen during hitstop; transitions are inertial offsets from what was last drawn "
           "(`EHAnimInstance`), so a restart mid-transition stays continuous; facing flips cut without a blend by design. "
           "Display pacing (V-Sync at a refresh the compositor does not match) is a separate cause of uneven motion and is "
           "measured in `Docs/Validation.md`, not here.", "",
           "| Dir | Clip | Runtime use | Source | Frames | Fastest | Pops | Held % | Flips | Floor | Status |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    unexplained = []
    for r in rows:
        clip = r["clip"]
        char = "wren" if clip.startswith("A_Wren_") else "ashka"
        key = clip.split("_", 2)[2]
        use = runtime_use(char, key, r["dir"])
        src = source(char, key)
        flagged = float(r["fastest_cm"]) > 40 or r["pops"] or r["flips"] or float(r["lowest_cm"]) < -2
        held = float(r["held_pct"])
        held_note = f"{held:.0f}" + (" (holds)" if held >= 10 and key.split("_")[0] in HOLDS else "")
        if held >= 10 and key.split("_")[0] not in HOLDS:
            flagged = True
        disp = DISPOSITIONS.get(clip)
        if flagged and not disp:
            unexplained.append(clip)
            status = "**FLAGGED, no disposition**"
        elif disp:
            status = disp
        else:
            status = "checked"
        out.append(f"| {r['dir']} | `{clip}` | {use} | {src} | {r['frames']} | {r['fastest_cm']} ({r['fastest_joint']} f{r['fastest_frame']}) | "
                   f"{r['pops'] or '-'} | {held_note} | {r['flips'] or '-'} | {r['lowest_cm']} | {status} |")
    out += ["", f"{len(rows)} clips; {len(unexplained)} flagged without a disposition."]
    DOC.write_text("\n".join(out) + "\n")
    print("wrote", DOC, len(rows), "unexplained:", unexplained)
    return 1 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main())
