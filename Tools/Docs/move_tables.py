"""Regenerates the move tables in Docs/CombatContract.md from Content/Data (the shipped values).

Usage: python3 Tools/Docs/move_tables.py   (run from the repository root)
Frame advantage uses the simulation's definition and is checked against the simulation by Tests/Core.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Content" / "Data"
DOC = ROOT / "Docs" / "CombatContract.md"
BEGIN = "<!-- move-tables:begin -->"
END = "<!-- move-tables:end -->"

DIR_TEXT = {"any": "", "neutral": "", "forward": "toward + ", "back": "away + "}
BUTTON = {"light": "Light", "heavy": "Heavy", "special": "Special", "throw": "Grab", "dodge": "Dodge"}


def reach_cm(move):
    if not move.get("hits"):
        return None
    first = move["hits"][0]["frames"][0]
    travel = 0.0
    for seg in move.get("travel", []):
        a, b = seg["frames"]
        for f in range(a, b + 1):
            if f < first:
                travel += seg["vx"]
    return max(h["box"][2] for h in move["hits"]) + travel


def table(char, pres):
    notes = pres["characters"][char["id"]]["moves"]
    rows = ["| Input | Move | Startup | Active | Recovery | Reach (cm) | Damage | On block | On hit | Cancels | Gauge | Notes / counterplay | Anim |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in char["moves"]:
        inp = DIR_TEXT.get(m.get("dir", "any"), "") + BUTTON[m["button"]]
        if m["id"] == "L2":
            inp = "Light, Light"
        if m["id"] == "L3":
            inp = "Light x3"
        if m["kind"] == "dodge" and m.get("dir", "any") == "any":
            inp = "Dodge (away/neutral)"
        hits = m.get("hits", [])
        if hits:
            first, last = hits[0]["frames"][0], hits[-1]["frames"][1]
            startup, active, recovery = str(first), str(last - first + 1), str(m["total"] - last)
            h = hits[0]
            remaining = (h["frames"][1] - h["frames"][0]) + (m["total"] - h["frames"][1])
            on_block = "-" if m["kind"] == "throw" else f"{h['blockstun'] - remaining:+d}"
            if m["kind"] == "throw":
                on_hit = "throw"
            elif h.get("knockdown"):
                on_hit = "knockdown"
            else:
                on_hit = f"{h['hitstun'] - remaining:+d}" + (" (KD on counter)" if h.get("knockdownOnCounter") else "")
            damage = "-" if m["kind"] == "throw" else str(h["damage"]) + (f" (chip {h['chip']})" if h.get("chip") else "")
            reach = f"{reach_cm(m):.0f}" if m["kind"] != "throw" else f"grab {m['throwRange']}"
        else:
            startup, active, recovery = "-", "-", str(m["total"])
            on_block = on_hit = damage = reach = "-"
            if m["kind"] == "dodge":
                startup = f"invuln {m['invulnStrike'][0]}-{m['invulnStrike'][1]}"
                recovery = str(m["total"] - m["invulnStrike"][1])
            if m["kind"] == "buff":
                startup = f"applies {m['aura']['applyFrame']}"
        cancel = m.get("cancel")
        cancels = "-"
        if cancel:
            when = "hit/block" if cancel.get("onHit") and cancel.get("onBlock") else ("hit" if cancel.get("onHit") else "block")
            cancels = f"{', '.join(cancel['into'])} on {when} ({cancel['frames'][0]}-{cancel['frames'][1]})"
        gauge = str(m.get("meterCost", 0)) if m.get("meterCost") else "-"
        note = notes.get(m["id"], {}).get("note", "")
        rows.append(f"| {inp} | {m['name']} | {startup} | {active} | {recovery} | {reach} | {damage} | {on_block} | {on_hit} | {cancels} | {gauge} | {note} | `{m['anim']}` |")
    throws = ["", "| Throw | Duration | Damage frame | Damage | Lands | Victim knockdown | Anims |", "|---|---|---|---|---|---|---|"]
    for t in char["throws"]:
        side = "in front" if t["landX"] > 0 else "behind (side switch)"
        throws.append(f"| {t['name']} | {t['duration']} | {t['damageFrame']} | {t['damage']} | {abs(t['landX'])} cm {side} | {t['victimKnockdown']} | `{t['attackerAnim']}` / `{t['victimAnim']}` |")
    return "\n".join(rows + throws)


def main():
    pres = json.loads((DATA / "presentation.json").read_text())
    out = [BEGIN, ""]
    for fid in ("wren", "ashka"):
        char = json.loads((DATA / "Fighters" / f"{fid}.json").read_text())
        out += [f"### {char['name']}", "",
                f"Health {char['maxHealth']}; walk {char['walkForward']} cm/frame forward, {char['walkBack']} back; pushbox half-width {char['halfWidth']} cm; standing hurtbox {char['hurt']} cm.",
                "", table(char, pres), ""]
    out.append(END)
    text = DOC.read_text()
    start, end = text.index(BEGIN), text.index(END) + len(END)
    DOC.write_text(text[:start] + "\n".join(out) + text[end:])
    print("updated", DOC)


if __name__ == "__main__":
    main()
