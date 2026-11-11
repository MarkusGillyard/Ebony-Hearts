"""Stages a distributable copy of a packaged Linux build and archives it.

Usage: python3 stage_release.py <BuildCookRun archive dir>/Linux <out dir> <release name> <source commit>

- Copies the package except its symbol files (.debug/.sym) and debug manifest; symbols stay with the original package.
- Adds THIRD_PARTY_NOTICES.txt (the asset ledger's third-party table, the engine notices and the font licences) and
  VERSION.txt (source commit, content hash, engine, build time).
- Writes <release name>.tar.gz plus SHA256SUMS (archive) and <release name>.files.sha256 (every file in the release).
Checks the whole package before writing: refuses links, special files, a package without paks or game binary, and
any existing release folder, archive or file list of the same name. Never deletes or overwrites anything.
"""
import hashlib
import os
import re
import shutil
import stat
import sys
import tarfile
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ledger_table():
    """The third-party table from Docs/AssetLedger.md as plain text."""
    lines = open(os.path.join(REPO, "Docs", "AssetLedger.md"), encoding="utf-8").read().splitlines()
    start = lines.index("## Third-party inputs")
    rows = [l for l in lines[start:] if l.startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[-| ]+\|$", r)]
    out = []
    for r in rows[1:]:
        cells = [c.strip().replace("`", "") for c in r.strip("|").split("|")]
        out.append(f"* {cells[0]}\n  Licence: {cells[1]}\n  Used for: {cells[2]}\n  Shipped as: {cells[3]}\n")
    return "\n".join(out)


def notices(package):
    parts = [
        "EBONY HEARTS - THIRD-PARTY NOTICES",
        "",
        "Ebony Hearts, its characters and its world are (c) Markus Gillyard / Cinqic. All rights reserved.",
        "Unreal(R) Engine, Copyright 1998-2026, Epic Games, Inc. All rights reserved.",
        "",
        "Third-party inputs used to make this game:",
        "",
        ledger_table(),
        "CC0 1.0 needs no attribution; the sources are credited as a courtesy.",
        "",
        "Motion capture: Open Motion Project by ACCAD / The Ohio State University, licensed under CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/); retargeted and retimed for this game.",
        "Animation: some movements are based on Mixamo animations (Adobe), used royalty free under Mixamo's terms; retargeted and retimed for this game. Credited as a courtesy.",
        "",
    ]
    engine = os.path.join(package, "NOTICES.txt")
    if os.path.exists(engine):
        parts += ["Engine notices:", "", open(engine, encoding="utf-8", errors="replace").read().strip(), ""]
    fonts = os.path.join(REPO, "Content", "UI", "Fonts")
    for name in sorted(os.listdir(fonts)):
        if name.startswith("OFL") and name.endswith(".txt"):
            parts += ["=" * 78, f"{name}", "=" * 78, open(os.path.join(fonts, name), encoding="utf-8").read().strip(), ""]
    return "\n".join(parts) + "\n"


def content_hash(package):
    h = hashlib.sha256()
    paks = os.path.join(package, "EbonyHearts", "Content", "Paks")
    for name in sorted(os.listdir(paks)):
        h.update(name.encode())
        h.update(sha256(os.path.join(paks, name)).encode())
    return h.hexdigest()


def build_config(package):
    bins = os.path.join(package, "EbonyHearts", "Binaries", "Linux")
    if os.path.isfile(os.path.join(bins, "EbonyHearts-Linux-Shipping")):
        return "Shipping"
    if os.path.isfile(os.path.join(bins, "EbonyHearts")):
        return "Development"
    raise SystemExit(f"no game binary in {bins}")


def files_to_ship(package):
    """Relative paths of the files to copy. Refuses links and anything that is not a plain file or folder; leaves out
    the symbol files (.debug/.sym) and the debug manifest, so symbols stay with the original package."""
    ship = []
    for root, dirs, files in os.walk(package, followlinks=False):
        for d in dirs:
            if os.path.islink(os.path.join(root, d)):
                raise SystemExit(f"symlink in package: {os.path.join(root, d)}")
        for f in files:
            src = os.path.join(root, f)
            if os.path.islink(src):
                raise SystemExit(f"symlink in package: {src}")
            if not stat.S_ISREG(os.lstat(src).st_mode):
                raise SystemExit(f"not a regular file in package: {src}")
            rel = os.path.normpath(os.path.relpath(src, package))
            if rel == "Manifest_DebugFiles_Linux.txt" or rel.endswith((".debug", ".sym")):
                continue
            ship.append(rel)
    return sorted(ship)


def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: stage_release.py <package>/Linux <out dir> <release name> <source commit>")
    package, out, name, commit = sys.argv[1:5]
    if not name or name in (".", "..") or os.path.basename(name) != name:
        raise SystemExit(f"release name must be a single directory name: {name}")
    package = os.path.realpath(package)
    out = os.path.realpath(out)
    release = os.path.join(out, name)
    if os.path.commonpath((package, release)) == package:
        raise SystemExit(f"release dir must be outside package: {release}")
    for existing in (release, os.path.join(out, f"{name}.tar.gz"), os.path.join(out, f"{name}.files.sha256")):
        if os.path.lexists(existing):
            raise SystemExit(f"release output exists: {existing}")
    if not os.path.isfile(os.path.join(package, "EbonyHearts.sh")):
        raise SystemExit(f"not a packaged build (no EbonyHearts.sh): {package}")
    paks = os.path.join(package, "EbonyHearts", "Content", "Paks")
    if not os.path.isdir(paks) or not os.listdir(paks):
        raise SystemExit(f"no content paks in {paks}")
    config = build_config(package)
    ship = files_to_ship(package)
    os.makedirs(release)
    for rel in ship:
        dst = os.path.join(release, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(package, rel), dst)
    with open(os.path.join(release, "THIRD_PARTY_NOTICES.txt"), "w", encoding="utf-8") as f:
        f.write(notices(package))
    built = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(os.path.join(package, "EbonyHearts.sh"))))
    with open(os.path.join(release, "VERSION.txt"), "w", encoding="utf-8") as f:
        f.write(f"Ebony Hearts - first playable slice ({name})\n"
                f"Source commit: {commit}\n"
                f"Content hash (SHA-256 over the pak files): {content_hash(package)}\n"
                f"Engine: Unreal Engine 5.8.4, {config}, Linux x86-64 (Vulkan SM6)\n"
                f"Packaged: {built}\n"
                f"Launch: ./EbonyHearts.sh\n")
    files = []
    for root, _, fs in os.walk(release):
        for f in fs:
            p = os.path.join(root, f)
            files.append((os.path.relpath(p, release), sha256(p)))
    with open(os.path.join(out, f"{name}.files.sha256"), "x") as f:
        for rel, h in sorted(files):
            f.write(f"{h}  {name}/{rel}\n")
    archive = os.path.join(out, f"{name}.tar.gz")
    with tarfile.open(archive, "x:gz", compresslevel=6) as tar:
        tar.add(release, arcname=name)
    with open(os.path.join(out, "SHA256SUMS"), "a") as f:
        f.write(f"{sha256(archive)}  {name}.tar.gz\n")
    print(f"staged {len(ship)} package files (+2 notices/version) -> {release}")
    print(f"archive {archive} {os.path.getsize(archive)} bytes")


main()
