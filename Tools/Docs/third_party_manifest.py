"""Writes Docs/ThirdPartyManifest.json: every third-party input used by the slice, with its original source URL,
licence, acquisition date and SHA-256 of the original download(s).

Usage: python3 Tools/Docs/third_party_manifest.py <thirdparty-dir> <fonts-dir>
The source ledger in <thirdparty-dir> records the original downloads; only items listed in USED are emitted.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

USED = {
    "polyhaven/monastery_stone_floor": "Chapel floor (M_FloorFlags)",
    "polyhaven/medieval_blocks_03": "Chapel walls and vaults (M_StoneAshlar)",
    "polyhaven/rusty_metal_04": "Chapel iron: stands, censers, chains (M_IronAged)",
    "polyhaven/weathered_planks": "Chapel pews and planks (M_WoodPew)",
    "ambientcg/Rock035": "Chapel piers, arches, tracery (M_StoneDressed)",
    "ambientcg/Ivory001B": "Chapel candle wax (M_CandleWax)",
    "ambientcg/Fabric066": "Chapel altar cloth; Ashka coat and trousers detail",
    "ambientcg/Fabric001": "Ashka shirt; Wren hand and ankle wraps detail",
    "ambientcg/Fabric034": "Wren sports top and waistband detail",
    "ambientcg/Fabric040": "Wren shorts; Ashka tie; strap detail",
    "ambientcg/Leather021": "Ashka loafers detail",
    "ambientcg/Leather026": "Wren gloves; Ashka belt detail",
    "kenney/impact-sounds": "Layered under synthesized impacts, falls, steps",
    "kenney/interface-sounds": "Menu sounds (processed)",
    "kenney/rpg-audio": "Cloth and creak layers",
    "accad/male2_bvh": "Base motion for both fighters' idle stances, Wren's 720 hook kick and tornado kick, Ashka's body kick, teep, bow intro and bow win, and both fighters' defeated pose; retargeted and retimed (Tools/Blender/anim/build_mocap.py, mocap_clips.json)",
    "mixamo/animations": "Base motion for Wren's jab, cross, roundhouse, spinning back kick, walks, held guard, intro, win and double-leg slam (both sides), Ashka's held guard, Ashka's jab, horizontal elbow, step-in knee, flame elbow, flying knee and walks, and both fighters' hit, block, knockdown and KO reactions and get-up; retargeted and retimed (Tools/Blender/anim/build_mocap.py, mocap_clips.json). Raw exports are not in the repository",
}


def main():
    tp, fonts = Path(sys.argv[1]), Path(sys.argv[2])
    ledger = json.loads((tp / "ledger.json").read_text())
    out = []
    for item in ledger["items"]:
        if item["id"] not in USED:
            continue
        files = item.get("files")
        if isinstance(files, list):
            hashes = [{"file": os.path.basename(f["file"]), "sha256": f["sha256"], "url": f.get("url")} for f in files]
        elif isinstance(files, dict):
            hashes = [{"file": os.path.basename(k), "sha256": v} for k, v in files.items()]
        else:
            hashes = [{"file": os.path.basename(item.get("download_url", "")), "sha256": item.get("sha256"), "url": item.get("download_url")}]
        lic = item.get("license")
        out.append({
            "id": item["id"], "title": item.get("title"), "creator": item.get("creator"),
            "source_page": item.get("source_page_url"), "acquired": item.get("acquired"),
            "license": lic.get("spdx") if isinstance(lic, dict) else lic,
            "license_url": lic.get("legalcode_url") if isinstance(lic, dict) else None,
            "use": USED[item["id"]], "modified": True, "raw_files_in_repo": False, "original_downloads": hashes,
        })
        if item.get("attribution"):
            out[-1]["attribution"] = item["attribution"]
    prov = json.loads((tp / "MakeHuman" / "PROVENANCE.json").read_text())
    msa = prov["makehuman_system_assets"]
    out.append({"id": "makehuman/system_assets", "title": "MakeHuman system assets", "creator": "MakeHuman Community",
                "source_page": msa["index_page"], "acquired": "2026-10-26", "license": "CC0-1.0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                "use": "Base body mesh hm08, eyes, eyebrows, eyelashes (via MPFB) for both fighters", "modified": True,
                "raw_files_in_repo": False, "original_downloads": [{"file": os.path.basename(msa["file"]), "sha256": msa["sha256"], "url": msa["url"]}],
                "notes": "Skin textures and hair/clothes assets not used; files with conflicting author metadata excluded."})
    mp = prov["mpfb_addon"]
    out.append({"id": "mpfb/2.0.18", "title": "MPFB 2.0.18 (Blender extension)", "creator": "MakeHuman Community",
                "source_page": mp["listed_by"], "acquired": "2026-10-26", "license": "GPL-3.0-or-later (code); CC0-1.0 (bundled assets)",
                "use": "Build tool only (body shaping, game_engine rig and weights); not shipped", "modified": False,
                "raw_files_in_repo": False, "original_downloads": [{"file": os.path.basename(mp["file"]), "sha256": mp["sha256"], "url": mp["url"]}]})
    # Motion capture: the CMU clips named in Tools/Blender/anim/mocap_clips.json, plus each subject's skeleton.
    clips = json.loads((Path(__file__).resolve().parents[1] / "Blender" / "anim" / "mocap_clips.json").read_text())
    used = sorted({spec["clip"] for char in clips.values() for spec in char.values() if "clip" in spec})
    if used:   # CMU data is credited only while a clip uses it
        files = sorted({f"{c.split('_')[0]}.asf" for c in used} | {f"{c}.amc" for c in used})
        cmu = tp / "CMU"
        out.append({"id": "cmu/mocap", "title": "CMU Graphics Lab Motion Capture Database: " + ", ".join(used),
                    "creator": "Carnegie Mellon University Graphics Lab", "source_page": "http://mocap.cs.cmu.edu/",
                    "acquired": "2026-11-03",
                    "license": "CMU terms: free for all uses; may be included in commercially sold products; the data itself may not be resold, even converted",
                    "license_url": "http://mocap.cs.cmu.edu/faqs.php",
                    "use": "Base motion for fighter animations, retargeted and retimed to the combat data (Tools/Blender/anim/build_mocap.py)",
                    "modified": True, "raw_files_in_repo": False,
                    "original_downloads": [{"file": f, "sha256": hashlib.sha256((cmu / f).read_bytes()).hexdigest(),
                                            "url": f"http://mocap.cs.cmu.edu/subjects/{f.split('_')[0].split('.')[0]}/{f}"} for f in files],
                    "notes": "Credit requested by CMU: The data used in this project was obtained from mocap.cs.cmu.edu. "
                             "The database was created with funding from NSF EIA-0196217."})
    sums = {}
    for line in (fonts / "SHA256SUMS").read_text().splitlines():
        h, f = line.split(None, 1)
        sums[f.strip()] = h
    out.append({"id": "fonts/cinzel", "title": "Cinzel (Regular, Bold) 2.000", "creator": "The Cinzel Project Authors (Natanael Gama)",
                "source_page": "https://github.com/NDISCOVER/Cinzel", "acquired": "2026-11-03", "license": "OFL-1.1",
                "use": "Display type", "modified": False, "raw_files_in_repo": True,
                "original_downloads": [{"file": k.split('/')[-1], "sha256": v} for k, v in sums.items() if k.startswith("cinzel/")]})
    out.append({"id": "fonts/alegreya-sans", "title": "Alegreya Sans (Regular, Medium, Bold)", "creator": "The Alegreya Sans Project Authors (Huerta Tipografica)",
                "source_page": "https://github.com/google/fonts/tree/main/ofl/alegreyasans", "acquired": "2026-11-03", "license": "OFL-1.1",
                "use": "Body type", "modified": False, "raw_files_in_repo": True,
                "original_downloads": [{"file": k.split('/')[-1], "sha256": v} for k, v in sums.items() if k.startswith("alegreyasans/")]})
    dest = Path(__file__).resolve().parents[2] / "Docs" / "ThirdPartyManifest.json"
    dest.write_text(json.dumps({"generated_from": "original download records, SHA-256 verified on 2026-11-02/03", "items": out}, indent=1))
    print("wrote", dest, len(out), "items")


main()
