"""Contact sheet of an fp_anim.py preview: python3 -I fp_sheet.py <preview dir> <clip> <out.jpg> [cols]"""
import glob
import os
import sys

from PIL import Image, ImageDraw

d, clip, out = sys.argv[1], sys.argv[2], sys.argv[3]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 4
files = sorted(glob.glob(os.path.join(d, f"{clip}_[0-9][0-9][0-9].png")))
ims = [Image.open(f).convert("RGB") for f in files]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
dr = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * w, (i // cols) * h
    sheet.paste(im, (x, y))
    dr.text((x + 8, y + 6), f"{clip} f{os.path.basename(f)[-7:-4]}", fill=(255, 255, 255))
sheet.save(out, quality=85)
