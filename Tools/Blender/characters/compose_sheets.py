"""Labelled review sheets from the evidence renders (system Python 3 with Pillow, no Blender):

    python3 Tools/Blender/characters/compose_sheets.py

Writes <slice>/evidence/characters/<id>_turnaround_sheet.png, <id>_poses_sheet.png, <id>_closeups_sheet.png."""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
EVI = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", "evidence", "characters"))
POSES = ["rest", "roundhouse", "stance", "guard", "punch", "twist", "knee", "backbend"]


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 * len(text) + 12, 22), fill=(10, 12, 16))
    d.text((6, 5), text, fill=(230, 232, 236))
    return im


def sheet(tiles, cols, size, out):
    rows = (len(tiles) + cols - 1) // cols
    W = Image.new("RGB", (cols * size[0], rows * size[1]), (20, 24, 30))
    for i, (path, text) in enumerate(tiles):
        if not os.path.isfile(path):
            continue
        im = Image.open(path).convert("RGB").resize(size)
        W.paste(label(im, text), ((i % cols) * size[0], (i // cols) * size[1]))
    W.save(out)
    return out


def main():
    for cid in ("wren", "ashka"):
        sheet([(os.path.join(EVI, "%s_%s.png" % (cid, v)), "%s %s" % (cid, v)) for v in ("front", "side", "back")],
              3, (600, 933), os.path.join(EVI, "%s_turnaround_sheet.png" % cid))
        tiles = []
        for view in ("3q", "side"):
            for p in POSES:
                tiles.append((os.path.join(EVI, "%s_pose_%s_%s.png" % (cid, p, view)), "%s %s" % (p, view)))
        sheet(tiles, 8, (350, 450), os.path.join(EVI, "%s_poses_sheet.png" % cid))
        sheet([(os.path.join(EVI, "%s_pose_%s_close.png" % (cid, p)), "%s close" % p) for p in POSES[1:]],
              4, (420, 540), os.path.join(EVI, "%s_closeups_sheet.png" % cid))


if __name__ == "__main__":
    main()
