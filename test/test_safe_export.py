import unittest
import shutil
from pathlib import Path
from ragmaker.utils import safe_export

class TestSafeExport(unittest.TestCase):
    def setUp(self):
        self.src_dir = Path("src_test_safe_export")
        self.dst_dir = Path("dst_test_safe_export")
        if self.src_dir.exists(): shutil.rmtree(self.src_dir)
        if self.dst_dir.exists(): shutil.rmtree(self.dst_dir)
        self.src_dir.mkdir()
        self.dst_dir.mkdir()

    def tearDown(self):
        if self.src_dir.exists(): shutil.rmtree(self.src_dir)
        if self.dst_dir.exists(): shutil.rmtree(self.dst_dir)

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

if __name__ == "__main__":
    unittest.main()
