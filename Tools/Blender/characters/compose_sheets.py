"""Labelled review sheets from the evidence renders (system Python 3 with Pillow, no Blender):

    python3 Tools/Blender/characters/compose_sheets.py [--evi DIR]
    python3 Tools/Blender/characters/compose_sheets.py --compare BEFORE_DIR AFTER_DIR OUT_DIR

The first form writes <id>_turnaround_sheet_<light>.png, <id>_face_sheet.png, <id>_poses_sheet.png,
<id>_closeups_sheet.png, <id>_feet_sheet.png into the evidence folder (EH_CHAR_EVI or --evi, default
<slice>/evidence/characters). --compare writes side-by-side before|after images of every render found
in both folders (same file name) into OUT_DIR as compare_<name>.png."""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
EVI = os.environ.get("EH_CHAR_EVI") or os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", "evidence", "characters"))
POSES = ["rest", "roundhouse", "stance", "guard", "punch", "twist", "knee", "backbend", "crouch", "teep",
         "kick_point", "tiptoe"]
LIGHTS = ("neutral", "chapel")


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 7 * len(text) + 12, 20), fill=(10, 12, 16))
    d.text((6, 4), text, fill=(230, 232, 236))
    return im


def sheet(tiles, cols, size, out):
    tiles = [t for t in tiles if os.path.isfile(t[0])]
    if not tiles:
        return None
    rows = (len(tiles) + cols - 1) // cols
    W = Image.new("RGB", (cols * size[0], rows * size[1]), (20, 24, 30))
    for i, (path, text) in enumerate(tiles):
        im = Image.open(path).convert("RGB").resize(size)
        W.paste(label(im, text), ((i % cols) * size[0], (i // cols) * size[1]))
    W.save(out)
    return out


def sheets(evi):
    for cid in ("wren", "ashka"):
        for lt in LIGHTS:
            sheet([(os.path.join(evi, "%s_%s_%s.png" % (cid, v, lt)), "%s %s %s" % (cid, v, lt))
                   for v in ("front", "side", "back")], 3, (600, 933), os.path.join(evi, "%s_turnaround_sheet_%s.png" % (cid, lt)))
        sheet([(os.path.join(evi, "%s_face_%s_%s.png" % (cid, v, lt)), "%s face %s %s" % (cid, v, lt))
               for lt in LIGHTS for v in ("3q", "front")], 4, (600, 600), os.path.join(evi, "%s_face_sheet.png" % cid))
        tiles = []
        for view in ("3q", "side"):
            for p in POSES:
                tiles.append((os.path.join(evi, "%s_pose_%s_%s.png" % (cid, p, view)), "%s %s" % (p, view)))
        sheet(tiles, 12, (300, 386), os.path.join(evi, "%s_poses_sheet.png" % cid))
        sheet([(os.path.join(evi, "%s_pose_%s_close.png" % (cid, p)), "%s close" % p) for p in POSES[1:]],
              6, (350, 450), os.path.join(evi, "%s_closeups_sheet.png" % cid))
        feet = [(os.path.join(evi, "%s_feet_rest_%s.png" % (cid, v)), "rest %s" % v) for v in ("front", "side", "back", "inner", "top")]
        for p in ("crouch", "tiptoe", "kick_point", "teep", "stance", "roundhouse", "knee"):
            feet += [(os.path.join(evi, "%s_feet_%s_%s.png" % (cid, p, v)), "%s %s" % (p, v)) for v in ("front", "side", "inner")]
        sheet(feet, 5, (400, 320), os.path.join(evi, "%s_feet_sheet.png" % cid))


def compare(before, after, out):
    os.makedirs(out, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(after)):
        if not f.endswith(".png") or not os.path.isfile(os.path.join(before, f)) or "_sheet" in f:
            continue
        a = Image.open(os.path.join(before, f)).convert("RGB")
        b = Image.open(os.path.join(after, f)).convert("RGB").resize(a.size)
        W = Image.new("RGB", (a.width * 2 + 8, a.height), (255, 255, 255))
        W.paste(label(a, "BEFORE " + f[:-4]), (0, 0))
        W.paste(label(b, "AFTER " + f[:-4]), (a.width + 8, 0))
        W.save(os.path.join(out, "compare_" + f))
        n += 1
    return n


def main():
    a = sys.argv[1:]
    if a[:1] == ["--compare"]:
        print("compared", compare(a[1], a[2], a[3]))
        return
    evi = a[a.index("--evi") + 1] if "--evi" in a else EVI
    sheets(evi)


if __name__ == "__main__":
    main()
