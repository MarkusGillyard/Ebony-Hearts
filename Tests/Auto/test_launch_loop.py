"""Safety checks for the start-and-quit harness; no game or signal is launched."""

import importlib.util
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("launch_loop.py")
spec = importlib.util.spec_from_file_location("launch_loop", SCRIPT)
launch_loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch_loop)


class LaunchLoopSafetyTests(unittest.TestCase):
    def test_group_filter_excludes_another_session(self):
        groups = {111: 111, 222: 4242, 333: 4242}
        with mock.patch.object(launch_loop, "game_pids", return_value=list(groups)):
            with mock.patch.object(launch_loop.os, "getpgid", side_effect=groups.__getitem__):
                self.assertEqual(launch_loop.game_pids_in_group(4242), [222, 333])

    def test_preexisting_game_aborts_before_launch_or_cleanup(self):
        with tempfile.TemporaryDirectory() as output:
            args = ["launch_loop.py", "--launcher", "/does/not/exist", "--runs", "1", "--out", output]
            with mock.patch.object(sys, "argv", args):
                with mock.patch.object(launch_loop, "wait_no_game", return_value=[111]):
                    with mock.patch.object(launch_loop.subprocess, "Popen") as popen:
                        with mock.patch.object(launch_loop.os, "kill") as kill:
                            with self.assertRaisesRegex(SystemExit, "refusing to launch"):
                                launch_loop.main()
            popen.assert_not_called()
            kill.assert_not_called()

    def test_cleanup_uses_launched_process_group(self):
        with tempfile.TemporaryDirectory() as output:
            args = ["launch_loop.py", "--launcher", "/does/not/exist", "--runs", "1", "--out", output, "--gap", "0"]
            fake_process = mock.Mock(pid=4242)
            fake_process.wait.return_value = 0
            with mock.patch.object(sys, "argv", args):
                with mock.patch.object(launch_loop, "wait_no_game", side_effect=[[], [777]]) as wait:
                    with mock.patch.object(launch_loop.subprocess, "Popen", return_value=fake_process):
                        with mock.patch.object(launch_loop, "device_state", return_value={}):
                            with mock.patch.object(launch_loop.os, "kill") as kill:
                                with mock.patch.object(launch_loop.os, "getpgid", return_value=4242):
                                    with mock.patch.object(launch_loop.time, "sleep"):
                                        self.assertEqual(launch_loop.main(), 1)  # No automation log from the mocked game.
            wait.assert_has_calls([mock.call(15.0), mock.call(10.0, pgid=4242)])
            kill.assert_called_once_with(777, signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
