import unittest
import tempfile
import json
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools.install_kb import install_knowledge_base

class TestInstallKB(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)
        self.source_kb = self.root / "source_kb"
        self.target_kb = self.root / "target_kb"

        # Setup source KB structure
        self.source_kb.mkdir()
        (self.source_kb / "introduction").mkdir()
        (self.source_kb / "introduction" / "doc1.md").write_text("content 1")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_install_basic(self):
        """Test basic installation (merging source into target)."""
        result = install_knowledge_base([self.source_kb], self.target_kb, merge=True)

        self.assertEqual(result["status"], "success")
        self.assertTrue((self.target_kb / "introduction" / "doc1.md").exists())

    def test_install_into_existing_directory(self):
        """Test installing into an existing directory."""
        self.target_kb.mkdir()
        
        # Use force=True because target exists, merge=True
        result = install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

        self.assertEqual(result["status"], "success")
        self.assertTrue(self.target_kb.exists())
        self.assertTrue((self.target_kb / "introduction" / "doc1.md").exists())

    def test_missing_source(self):
        """Test error when source directory does not exist."""
        missing_source = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            install_knowledge_base([missing_source], self.target_kb, merge=True)

    def test_target_exists_error(self):
        """Test error when target directory exists and is not empty, without force."""
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        with self.assertRaises(FileExistsError):
            install_knowledge_base([self.source_kb], self.target_kb, merge=True)

    def test_target_exists_force(self):
        """Test overwriting target when force is True."""
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        result = install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)
        self.assertEqual(result["status"], "success")

        self.assertTrue((self.target_kb / "introduction" / "doc1.md").exists())
        # existing.txt should persist because we merge
        self.assertTrue((self.target_kb / "existing.txt").exists())

    def test_default_no_merge(self):
        """Test default behavior (no merge): install into subdirectories."""
        source2 = self.root / "source2"
        source2.mkdir()
        (source2 / "reference").mkdir()
        (source2 / "reference" / "doc2.md").write_text("content 2")

        # Install both with default behavior (merge=False)
        result = install_knowledge_base([self.source_kb, source2], self.target_kb)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["installed_kbs"]), 2)

        sub1 = self.target_kb / self.source_kb.name
        sub2 = self.target_kb / source2.name

        self.assertTrue(sub1.exists())
        self.assertTrue(sub2.exists())
        self.assertTrue((sub1 / "introduction" / "doc1.md").exists())
        self.assertTrue((sub2 / "reference" / "doc2.md").exists())

    def test_atomicity_failure(self):
        """Test that target is unchanged if an error occurs during processing."""
        self.target_kb.mkdir()
        (self.target_kb / "initial.txt").write_text("initial")

        with patch('ragmaker.tools.install_kb.safe_export', side_effect=RuntimeError("Simulated Failure")):
            with self.assertRaises(RuntimeError):
                install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

        # Verify target is unchanged
        self.assertTrue((self.target_kb / "initial.txt").exists())

    def test_temp_dir_location(self):
        """Test that temporary directory is created in target's parent directory."""
        with patch('ragmaker.tools.install_kb.tempfile.TemporaryDirectory') as mock_temp_dir:
            mock_temp_dir.return_value.__enter__.return_value = self.test_dir.name
            install_knowledge_base([self.source_kb], self.target_kb, merge=True)
            mock_temp_dir.assert_called_with(dir=self.target_kb.parent)

    def test_flatten_flag(self):
        """Test installing with --flatten expands contents directly into target."""
        result = install_knowledge_base([self.source_kb], self.target_kb, flatten=True)

        self.assertEqual(result["status"], "success")
        self.assertTrue((self.target_kb / "introduction" / "doc1.md").exists())
        self.assertFalse((self.target_kb / self.source_kb.name).exists())

if __name__ == '__main__':
    unittest.main()
