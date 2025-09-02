import unittest
import os
import sys
import shutil
import json
import io
from pathlib import Path
from unittest.mock import patch

# Add tools directory to sys.path for importing the script under test
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))

import cache_cleanup

class TestCacheCleanup(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory with a mix of files and subdirs."""
        self.test_dir = Path("./temp_cache_cleanup_test")
        # Clean up any previous runs that might have failed
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()

        # --- Items to be KEPT ---
        (self.test_dir / "discovery.json").touch()
        (self.test_dir / "doc1.md").touch()
        (self.test_dir / "another.md").touch()
        self.kept_item_names = {"discovery.json", "doc1.md", "another.md"}

        # --- Items to be DELETED ---
        (self.test_dir / "source.html").touch()
        (self.test_dir / "notes.txt").touch()
        self.subdir = self.test_dir / "sub"
        self.subdir.mkdir()
        (self.subdir / "image.jpg").touch()
        self.deleted_item_names = {"source.html", "notes.txt", "sub"}


    def tearDown(self):
        """Remove the temporary directory after the test."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_cleanup_logic_directly(self):
        """Test the core cleanup_directory function in isolation."""
        # Act
        deleted, kept = cache_cleanup.cleanup_directory(self.test_dir)

        # Assert: Check the returned lists (using sets for order-insensitivity)
        self.assertEqual(set(Path(p).name for p in deleted), self.deleted_item_names)
        self.assertEqual(set(Path(p).name for p in kept), self.kept_item_names)

        # Assert: Check what's actually left on disk
        remaining_items = set(p.name for p in self.test_dir.iterdir())
        self.assertEqual(remaining_items, self.kept_item_names)

    def test_main_script_execution(self):
        """Test the full script execution via main(), checking output and side-effects."""
        # Arrange: Set up the command-line arguments to be mocked
        test_args = [
            'tools/cache_cleanup.py',
            '--target-dir', str(self.test_dir)
        ]

        # Act: Patch sys.argv and capture stdout to check the final JSON output
        with patch('sys.argv', test_args), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            cache_cleanup.main()
            output = json.loads(mock_stdout.getvalue())

        # Assert: Check the JSON output from the script
        self.assertEqual(output['status'], 'success')
        self.assertEqual(len(output['deleted_items']), 3)
        self.assertEqual(len(output['kept_items']), 3)

        # Check that the reported deleted/kept items match expectations
        output_deleted_names = set(Path(p).name for p in output['deleted_items'])
        output_kept_names = set(Path(p).name for p in output['kept_items'])
        self.assertEqual(output_deleted_names, self.deleted_item_names)
        self.assertEqual(output_kept_names, self.kept_item_names)

        # Assert: Check the final state of the file system
        remaining_on_disk = set(p.name for p in self.test_dir.iterdir())
        self.assertEqual(remaining_on_disk, self.kept_item_names)
        self.assertFalse((self.test_dir / "source.html").exists())
        self.assertFalse(self.subdir.exists())

if __name__ == '__main__':
    unittest.main()
