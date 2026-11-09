"""Prepares the interface textures from the creator's supplied art (UI/UX overhaul, 2026-11-09).

Usage: python3 -I make_ui_textures.py <supplied logo .png> <output dir>

Writes, into <output dir>:
- T_Logo.png: the creator's logo, byte-for-byte (2172 x 724 RGBA); drawn large (title).
- T_LogoSmall.png: the same logo downscaled to 1024 px wide for menus, padded to a height that is a multiple of 4.
  It is resized in premultiplied alpha, so the dark outline does not bleed into the transparent edge, then stored
  straight (unpremultiplied) as PNG expects.
The supplied file is checked against its SHA-256 before anything is written.
"""
import hashlib
import shutil
import sys
from pathlib import Path

from PIL import Image

LOGO_SHA256 = "5508d12d6f4b9acf2c023e3fd85bbf17134cb1b670b61f9bda3693a5d243d61f"
SMALL_WIDTH = 1024


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if digest != LOGO_SHA256:
        sys.exit(f"logo SHA-256 {digest} is not the supplied logo {LOGO_SHA256}")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out / "T_Logo.png")
    logo = Image.open(src).convert("RGBA")
    height = round(SMALL_WIDTH * logo.height / logo.width)
    small = logo.convert("RGBa").resize((SMALL_WIDTH, height), Image.LANCZOS).convert("RGBA")
    # Block compression works on 4 x 4 blocks: pad the height with transparent rows to a multiple of 4.
    padded_h = (height + 3) // 4 * 4
    if padded_h != height:
        canvas = Image.new("RGBA", (SMALL_WIDTH, padded_h), (0, 0, 0, 0))
        canvas.paste(small, (0, (padded_h - height) // 2))
        small = canvas
    small.save(out / "T_LogoSmall.png", optimize=True)
    print(f"T_Logo.png {logo.size}, T_LogoSmall.png {small.size}")


if __name__ == "__main__":
    main()
