"""The manifest generator must reject an omitted capture used by the game."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Tools/Docs/third_party_manifest.py"
CLIPS = ROOT / "Tools/Blender/anim/mocap_clips.json"


class ManifestCoverageTests(unittest.TestCase):
    def test_missing_active_mixamo_capture_is_rejected(self):
        clips = json.loads(CLIPS.read_text())
        captures = {spec["fbx"] for char in clips.values() for spec in char.values() if "fbx" in spec}
        self.assertIn("K_MmaKick_Medium.fbx", captures)
        with tempfile.TemporaryDirectory() as temp:
            thirdparty = Path(temp) / "thirdparty"
            thirdparty.mkdir()
            files = {f"Mixamo/{name}": "0" * 64 for name in captures if name != "K_MmaKick_Medium.fbx"}
            (thirdparty / "ledger.json").write_text(json.dumps({"items": [{"id": "mixamo/animations", "files": files}]}))
            result = subprocess.run([sys.executable, str(SCRIPT), str(thirdparty), str(Path(temp) / "fonts")],
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Mixamo captures missing from source ledger: K_MmaKick_Medium.fbx", result.stderr)


if __name__ == "__main__":
    unittest.main()
