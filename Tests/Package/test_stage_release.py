"""Safety checks for the release staging entry point."""

import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "Tools/Package/stage_release.py"


class StageReleaseSafetyTests(unittest.TestCase):
    def test_rejects_output_inside_input_before_creating_files(self):
        with tempfile.TemporaryDirectory() as root:
            package = pathlib.Path(root) / "package"
            package.mkdir()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(package), str(package / "out"), "release", "head"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside package", result.stderr)
            self.assertFalse((package / "out").exists())

    def test_rejects_traversal_release_name(self):
        with tempfile.TemporaryDirectory() as root:
            package = pathlib.Path(root) / "package"
            package.mkdir()
            out = pathlib.Path(root) / "out"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(package), str(out), "../escape", "head"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("single directory name", result.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
