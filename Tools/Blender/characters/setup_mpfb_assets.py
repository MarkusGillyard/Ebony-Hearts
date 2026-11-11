"""Installs the MakeHuman CC0 system-asset pack into MPFB's user data with MPFB's own pack loader.

Run through setup_mpfb.sh (which sets BLENDER_USER_RESOURCES, so MPFB's user data lives in
<slice>/userdata/blender-chars/extensions/.user/user_default/mpfb/data)."""
import os
import sys
sys.dont_write_bytecode = True

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eh_mpfb  # noqa: E402

pack = sys.argv[sys.argv.index("--") + 1]
eh_mpfb.enable_mpfb(use_installed_pack=False)
LS = eh_mpfb.mpfb("services.locationservice", "LocationService")
data = LS.get_user_data()
marker = os.path.join(data, "packs", "makehuman_system_assets.json")
if os.path.isfile(marker):
    print("[setup] asset pack already installed in", data)
else:
    os.makedirs(data, exist_ok=True)
    res = bpy.ops.mpfb.load_pack(filepath=pack)
    print("[setup] mpfb.load_pack ->", res, "into", data)
    if not os.path.isfile(marker):
        raise SystemExit("asset pack install failed: %s missing" % marker)
AS = eh_mpfb.mpfb("services.assetservice", "AssetService")
AS.update_all_asset_lists()
print("[setup] data roots:", AS.get_available_data_roots())
