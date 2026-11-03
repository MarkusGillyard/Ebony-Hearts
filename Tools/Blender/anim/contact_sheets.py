"""Builds one labelled contact sheet per animation from review frames: python3 contact_sheets.py <review-dir>."""
import glob
import os
import re
import sys

from PIL import Image, ImageDraw

root = sys.argv[1]
frames_dir = os.path.join(root, "frames")
groups = {}
for f in sorted(glob.glob(os.path.join(frames_dir, "*.png"))):
    m = re.match(r"(.+)_(\d{3})\.png$", os.path.basename(f))
    if m:
        groups.setdefault(m.group(1), []).append((int(m.group(2)), f))
for name, items in groups.items():
    ims = [Image.open(f).convert("RGB") for _, f in items]
    w, h = ims[0].size
    scale = 0.6
    tw, th = int(w * scale), int(h * scale)
    sheet = Image.new("RGB", (tw * len(ims), th + 24), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    for i, ((frame, _), im) in enumerate(zip(items, ims)):
        sheet.paste(im.resize((tw, th)), (i * tw, 24))
        d.text((i * tw + 6, 5), f"{name} f{frame}", fill=(230, 220, 200))
    sheet.save(os.path.join(root, name + ".jpg"), quality=85)
print("sheets", len(groups))
