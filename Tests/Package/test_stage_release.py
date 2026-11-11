"""Safety checks for the release staging entry point."""

import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "Tools/Package/stage_release.py"


def stage(package, out, name="release"):
    return subprocess.run([sys.executable, "-B", str(SCRIPT), str(package), str(out), name, "abc1234"],
                          capture_output=True, text=True, check=False)


def fake_package(root, config="Shipping"):
    """The layout of a BuildCookRun Linux package, with tiny stand-in files."""
    package = pathlib.Path(root) / "package with spaces" / "Linux"
    binaries = package / "EbonyHearts" / "Binaries" / "Linux"
    binaries.mkdir(parents=True)
    exe = "EbonyHearts-Linux-Shipping" if config == "Shipping" else "EbonyHearts"
    (binaries / exe).write_bytes(b"binary")
    (binaries / f"{exe}.debug").write_bytes(b"symbols")
    (binaries / f"{exe}.sym").write_bytes(b"symbols")
    paks = package / "EbonyHearts" / "Content" / "Paks"
    paks.mkdir(parents=True)
    (paks / "EbonyHearts-Linux.pak").write_bytes(b"content")
    (package / "EbonyHearts.sh").write_text("#!/bin/sh\n")
    (package / "Manifest_DebugFiles_Linux.txt").write_text(f"EbonyHearts/Binaries/Linux/{exe}.debug\t0\n")
    return package


class StageReleaseSafetyTests(unittest.TestCase):
    def test_stages_a_package_without_its_symbols(self):
        with tempfile.TemporaryDirectory() as root:
            package = fake_package(root)
            out = pathlib.Path(root) / "out"
            result = stage(package, out)
            self.assertEqual(result.returncode, 0, result.stderr)
            release = out / "release"
            shipped = sorted(str(p.relative_to(release)) for p in release.rglob("*") if p.is_file())
            self.assertEqual(shipped, ["EbonyHearts.sh", "EbonyHearts/Binaries/Linux/EbonyHearts-Linux-Shipping",
                                       "EbonyHearts/Content/Paks/EbonyHearts-Linux.pak", "THIRD_PARTY_NOTICES.txt", "VERSION.txt"])
            version = (release / "VERSION.txt").read_text()
            self.assertIn("Source commit: abc1234", version)
            self.assertIn("Unreal Engine 5.8.4, Shipping", version)
            listed = (out / "release.files.sha256").read_text().splitlines()
            self.assertEqual(len(listed), len(shipped))
            with tarfile.open(out / "release.tar.gz") as tar:
                self.assertFalse(any(n.endswith((".debug", ".sym")) for n in tar.getnames()))

    def test_version_names_a_development_package(self):
        with tempfile.TemporaryDirectory() as root:
            result = stage(fake_package(root, "Development"), pathlib.Path(root) / "out")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Unreal Engine 5.8.4, Development", (pathlib.Path(root) / "out" / "release" / "VERSION.txt").read_text())

    def test_rejects_symlink_before_creating_files(self):
        with tempfile.TemporaryDirectory() as root:
            package = fake_package(root)
            os.symlink("/etc/hostname", package / "EbonyHearts" / "link")
            out = pathlib.Path(root) / "out"
            result = stage(package, out)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)
            self.assertFalse((out / "release").exists())

    def test_rejects_special_file_before_creating_files(self):
        with tempfile.TemporaryDirectory() as root:
            package = fake_package(root)
            os.mkfifo(package / "EbonyHearts" / "pipe")
            out = pathlib.Path(root) / "out"
            result = stage(package, out)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a regular file", result.stderr)
            self.assertFalse((out / "release").exists())

    def test_never_overwrites_an_existing_archive(self):
        with tempfile.TemporaryDirectory() as root:
            out = pathlib.Path(root) / "out"
            out.mkdir()
            (out / "release.tar.gz").write_bytes(b"earlier release")
            result = stage(fake_package(root), out)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exists", result.stderr)
            self.assertEqual((out / "release.tar.gz").read_bytes(), b"earlier release")
            self.assertFalse((out / "release").exists())

    def test_rejects_a_folder_that_is_not_a_package(self):
        with tempfile.TemporaryDirectory() as root:
            package = fake_package(root)
            (package / "EbonyHearts.sh").unlink()
            out = pathlib.Path(root) / "out"
            result = stage(package, out)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a packaged build", result.stderr)
            self.assertFalse(out.exists())

    def test_rejects_output_reached_through_a_link_into_the_package(self):
        with tempfile.TemporaryDirectory() as root:
            package = fake_package(root)
            alias = pathlib.Path(root) / "alias"
            os.symlink(package, alias)
            result = stage(package, alias / "out")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside package", result.stderr)
            self.assertFalse((package / "out").exists())

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
