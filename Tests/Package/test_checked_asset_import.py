"""Check failure and recovery behavior without importing Unreal."""

from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[2] / "Tools/Unreal/import_checked.py"


class CheckedImportTests(unittest.TestCase):
    def setUp(self):
        self.asset = Mock()
        self.asset.get_path_name.return_value = "/Game/Test/Sample.Sample"
        self.task = SimpleNamespace(destination_path="/Game/Test", destination_name="Sample",
                                    filename="Sample.fbx", get_objects=lambda: [self.asset])
        self.event = Mock()
        self.callback = None
        self.event.add_callable.side_effect = self.capture_callback
        self.library = Mock()
        self.library.does_asset_exist.return_value = True
        self.tools = Mock()
        unreal = SimpleNamespace(
            AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda: self.tools),
            EditorAssetLibrary=self.library, ImportSubsystem=object(),
            get_editor_subsystem=lambda _: SimpleNamespace(on_asset_reimport=self.event),
        )
        with patch.dict(sys.modules, unreal=unreal):
            self.api = runpy.run_path(str(SCRIPT))

    def capture_callback(self, callback):
        self.callback = callback

    def test_stale_existing_fbx_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Import failed"):
            self.api["import_checked"](self.task, type(self.asset), legacy_fbx=True)
        self.event.remove_callable.assert_called_once_with(self.callback)

    def test_matching_reimport_is_accepted(self):
        self.tools.import_asset_tasks.side_effect = lambda _: self.callback(self.asset)
        self.assertIs(self.api["import_checked"](self.task, type(self.asset), legacy_fbx=True), self.asset)
        self.event.remove_callable.assert_called_once_with(self.callback)

    def test_failed_save_is_rejected(self):
        self.library.save_loaded_asset.return_value = False
        with self.assertRaisesRegex(RuntimeError, "Could not save"):
            self.api["save_checked"](self.asset)
