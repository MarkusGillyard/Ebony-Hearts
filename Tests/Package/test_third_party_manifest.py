"""The manifest generator must reject an omitted capture used by the game."""

import json
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Tools/Docs/third_party_manifest.py"
CLIPS = ROOT / "Tools/Blender/anim/mocap_clips.json"
REQUIRED = runpy.run_path(str(SCRIPT))["USED"]


class ManifestCoverageTests(unittest.TestCase):
    def assert_capture_rejected(self, omitted):
        clips = json.loads(CLIPS.read_text())
        captures = {spec["fbx"] for char in clips.values() for spec in char.values() if "fbx" in spec}
        captures.update(spec[key] for spec in clips["throws"].values() for key in ("attacker", "victim"))
        captures.add("Rig_XBot_TPose.fbx")
        self.assertIn(omitted, captures)
        with tempfile.TemporaryDirectory() as temp:
            thirdparty = Path(temp) / "thirdparty"
            thirdparty.mkdir()
            files = {f"Mixamo/{name}": "0" * 64 for name in captures if name != omitted}
            (thirdparty / "ledger.json").write_text(json.dumps({"items": [{"id": item, "files": files if item == "mixamo/animations" else {}} for item in REQUIRED]}))
            result = subprocess.run([sys.executable, str(SCRIPT), str(thirdparty), str(Path(temp) / "fonts")],
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Mixamo captures missing from source ledger: " + omitted, result.stderr)

    def test_missing_active_mixamo_capture_is_rejected(self):
        self.assert_capture_rejected("K_MmaKick_Medium.fbx")

    def test_missing_throw_attacker_capture_is_rejected(self):
        self.assert_capture_rejected("W_DoubleLegTakedown_Attacker.fbx")

    def test_missing_throw_victim_capture_is_rejected(self):
        self.assert_capture_rejected("W_DoubleLegTakedown_Victim.fbx")

    def test_missing_calibration_capture_is_rejected(self):
        self.assert_capture_rejected("Rig_XBot_TPose.fbx")

    def test_missing_required_ledger_item_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            thirdparty = Path(temp) / "thirdparty"
            thirdparty.mkdir()
            (thirdparty / "ledger.json").write_text(json.dumps({"items": [
                {"id": item, "files": {}} for item in REQUIRED if item != "mixamo/animations"
            ]}))
            result = subprocess.run([sys.executable, str(SCRIPT), str(thirdparty), str(Path(temp) / "fonts")],
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Required inputs missing from source ledger: mixamo/animations", result.stderr)


if __name__ == "__main__":
    unittest.main()
