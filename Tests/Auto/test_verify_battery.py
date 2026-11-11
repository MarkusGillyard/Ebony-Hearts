"""Small synthetic evidence checks for the 1108 post-run verifier."""

import json
import tempfile
import unittest
from pathlib import Path

from verify_battery import PAD, PERF, SCENARIOS, verify


class VerifyBatteryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.log = root / "battery.log"
        self.evidence = root / "battery"
        self.evidence.mkdir()
        lines = ["12:00:00 battery start /release"]
        for name in SCENARIOS:
            lines.append(f"12:01:00 {name} rc=0")
            directory = self.evidence / name
            directory.mkdir()
            if name == "xinput":
                (directory / "driver.out").write_text("window 0x123 Ebony Hearts\nsent quit\n")
                for shot in ("x01_title", "x02_main", "x03_fight", "x04_after_inputs", "x05_pause", "x06_quit_confirm"):
                    (directory / f"{shot}.png").write_bytes(b"image")
                continue
            completion = "quit requested" if name in ("journey", "vpad-menu-and-fight", "vpad-disconnect") else "quit after 0 matches"
            auto = [completion]
            if name in PAD:
                scenario, kind = PAD[name]
                (directory / "pad.out").write_text(f"virtual pad scenario done: {scenario} ({kind})\n")
            if name == "matrix":
                auto = ["match_end" for _ in range(12)] + ["mem matrix_end", "quit after 12 matches"]
            if name == "lesson":
                auto = ['ok lesson_status step=1/14 "Movement"']
                auto += [f"ok wait_lesson {step} 10" for step in range(2, 15)]
                auto += ['ok lesson_status step=14/14 "Lesson complete"', completion]
            for perf_name in PERF.get(name, ()):
                auto.append(f"perf_end {perf_name}")
                (directory / f"{perf_name}.json").write_text(
                    json.dumps({"name": perf_name, "frames": 60, "seconds": 1.0}))
            if name in ("review-combat", "review-jump"):
                (directory / "capture.out").write_text("recorded /tmp/movie.mp4 rc=0\n")
                (directory / f"{name}.mp4").write_bytes(b"video")
            (directory / "auto_log.txt").write_text("\n".join(auto) + "\n")
        lines.append("12:59:00 battery done")
        self.log.write_text("\n".join(lines) + "\n")

    def test_complete_battery_passes(self):
        self.assertEqual(verify(self.log, self.evidence), [])

    def test_missing_or_nonzero_run_fails(self):
        log = self.log.read_text().replace("12:01:00 smoke rc=0", "12:01:00 smoke rc=124")
        self.log.write_text(log)
        self.assertTrue(any("smoke: package rc=124" in error for error in verify(self.log, self.evidence)))
        self.log.write_text(log.replace("12:01:00 smoke rc=124\n", ""))
        self.assertTrue(any("scenario names/order/count" in error for error in verify(self.log, self.evidence)))

    def test_missing_completion_and_negative_marker_fail(self):
        path = self.evidence / "vpad-disconnect" / "auto_log.txt"
        path.write_text("WARN device disconnected\n")
        errors = verify(self.log, self.evidence)
        self.assertTrue(any("vpad-disconnect: auto log contains" in error for error in errors))
        self.assertTrue(any("vpad-disconnect: missing quit requested" in error for error in errors))

    def test_wrapper_warning_and_nonfinite_perf_fail(self):
        self.log.write_text(self.log.read_text() + "WARN sampler failed\n")
        path = self.evidence / "perf-cold" / "perf_cold_first_match_25s.json"
        path.write_text('{"name":"perf_cold_first_match_25s","frames":NaN,"seconds":25}')
        errors = verify(self.log, self.evidence)
        self.assertTrue(any("battery log contains FAIL/WARN/STUCK" in error for error in errors))
        self.assertTrue(any("invalid perf metrics" in error for error in errors))

    def test_matrix_lesson_perf_and_driver_are_gated(self):
        matrix = self.evidence / "matrix" / "auto_log.txt"
        matrix.write_text(matrix.read_text().replace("match_end\n", "", 1))
        lesson = self.evidence / "lesson" / "auto_log.txt"
        lesson.write_text(lesson.read_text().replace("ok wait_lesson 14 10\n", ""))
        (self.evidence / "perf-cold" / "perf_cold_first_match_25s.json").unlink()
        (self.evidence / "xinput" / "driver.out").write_text("window 0x123 Ebony Hearts\n")
        (self.evidence / "vpad-layout-xbox" / "pad.out").write_text("driver stopped early\n")
        errors = verify(self.log, self.evidence)
        for fragment in ("incomplete 12-match", "missing successful wait for step 14",
                         "missing or invalid perf_cold_first_match_25s.json",
                         "xinput: driver did not", "virtual pad driver did not complete"):
            self.assertTrue(any(fragment in error for error in errors), fragment)


if __name__ == "__main__":
    unittest.main()
