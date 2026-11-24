"""Audio generation must fail closed when a requested input or its import is missing."""
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

SCRIPT = Path(__file__).resolve().parents[2] / 'Tools/Unreal/build_audio.py'


class AudioImportTests(unittest.TestCase):
    def run_import(self, root, requested, imported=True, loaded=True, saved=True):
        tools = MagicMock()
        def import_tasks(tasks):
            for task in tasks:
                task.imported_object_paths = [task.destination_path + '/' + task.destination_name] if imported else []
        tools.import_asset_tasks.side_effect = import_tasks
        fake = SimpleNamespace(AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda: tools),
                               EditorAssetLibrary=MagicMock(), AssetImportTask=SimpleNamespace,
                               load_asset=MagicMock(return_value=MagicMock() if loaded else None),
                               log=MagicMock(), log_error=MagicMock())
        fake.EditorAssetLibrary.save_asset.return_value = saved
        with patch.dict(os.environ, EH_WS=str(root), EH_AUDIO_NAMES=requested), patch.dict(sys.modules, unreal=fake):
            runpy.run_path(str(SCRIPT))
        return tools

    def make_sources(self, root):
        for cat in ('Combat', 'UI', 'Ambience', 'Music'):
            (root / 'sourceart/audio' / cat).mkdir(parents=True)
        (root / 'sourceart/audio/UI/S_Test.wav').write_bytes(b'fixture')

    def test_missing_requested_source_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_sources(root)
            with self.assertRaisesRegex(RuntimeError, 'requested audio WAV missing: S_Missing'):
                self.run_import(root, 'S_Missing')

    def test_failed_import_does_not_accept_old_loaded_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_sources(root)
            with self.assertRaisesRegex(RuntimeError, 'audio import failed:'):
                self.run_import(root, 'S_Test', imported=False)

    def test_missing_loaded_sound_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_sources(root)
            with self.assertRaisesRegex(RuntimeError, 'audio import failed:'):
                self.run_import(root, 'S_Test', loaded=False)

    def test_successful_selected_import(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_sources(root)
            tools = self.run_import(root, 'S_Test')
            self.assertEqual(tools.import_asset_tasks.call_count, 1)

    def test_failed_save_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_sources(root)
            with self.assertRaisesRegex(RuntimeError, 'audio save failed:'):
                self.run_import(root, 'S_Test', saved=False)

    def test_empty_full_import_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_sources(root)
            (root / 'sourceart/audio/UI/S_Test.wav').unlink()
            with self.assertRaisesRegex(RuntimeError, 'no audio WAV sources found'):
                self.run_import(root, '')
