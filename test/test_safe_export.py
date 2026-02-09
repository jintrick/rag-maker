import unittest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from ragmaker.utils import safe_export

class TestSafeExport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.src_dir = self.root / "src"
        self.dst_dir = self.root / "dst"
        self.src_dir.mkdir()
        self.dst_dir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_safe_export_merges_files(self):
        (self.src_dir / "new.txt").write_text("new content")
        (self.dst_dir / "old.txt").write_text("old content")

        safe_export(self.src_dir, self.dst_dir)

        self.assertTrue((self.dst_dir / "new.txt").exists())
        self.assertTrue((self.dst_dir / "old.txt").exists())
        self.assertEqual((self.dst_dir / "new.txt").read_text(), "new content")
        self.assertEqual((self.dst_dir / "old.txt").read_text(), "old content")

    def test_safe_export_overwrites_existing(self):
        (self.src_dir / "conflict.txt").write_text("new version")
        (self.dst_dir / "conflict.txt").write_text("old version")

        safe_export(self.src_dir, self.dst_dir)

        self.assertTrue((self.dst_dir / "conflict.txt").exists())
        self.assertEqual((self.dst_dir / "conflict.txt").read_text(), "new version")

    def test_safe_export_nested_directories(self):
        (self.src_dir / "subdir").mkdir()
        (self.src_dir / "subdir" / "file.txt").write_text("nested")

        safe_export(self.src_dir, self.dst_dir)

        self.assertTrue((self.dst_dir / "subdir" / "file.txt").exists())
        self.assertEqual((self.dst_dir / "subdir" / "file.txt").read_text(), "nested")

    def test_safe_export_resolves_file_directory_conflict(self):
        # src/foo is a directory
        (self.src_dir / "foo").mkdir()
        (self.src_dir / "foo" / "bar.txt").write_text("bar")

        # dst/foo is a file
        (self.dst_dir / "foo").write_text("blocking file")

        safe_export(self.src_dir, self.dst_dir)

        self.assertTrue((self.dst_dir / "foo").is_dir())
        self.assertTrue((self.dst_dir / "foo" / "bar.txt").exists())

    def test_safe_export_fails_fast_on_unlink_error(self):
        # src/foo is a directory
        (self.src_dir / "foo").mkdir()
        (self.src_dir / "foo" / "bar.txt").write_text("bar")

        # dst/foo is a file (blocking the directory)
        dst_foo = self.dst_dir / "foo"
        dst_foo.write_text("blocking file")

        # Mock unlink to raise OSError
        # We need to target pathlib.Path.unlink specifically
        with patch('pathlib.Path.unlink', side_effect=OSError("Permission denied")):
            with self.assertRaises(OSError):
                safe_export(self.src_dir, self.dst_dir)

    def test_safe_export_resolves_directory_file_conflict(self):
        # src/foo is a file
        (self.src_dir / "foo").write_text("file content")

        # dst/foo is a directory
        (self.dst_dir / "foo").mkdir()
        (self.dst_dir / "foo" / "bar.txt").write_text("bar")

        safe_export(self.src_dir, self.dst_dir)

        self.assertFalse((self.dst_dir / "foo").is_dir())
        self.assertTrue((self.dst_dir / "foo").is_file())
        self.assertEqual((self.dst_dir / "foo").read_text(), "file content")

if __name__ == "__main__":
    unittest.main()
