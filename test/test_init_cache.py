import unittest
import subprocess
import os
import shutil
from pathlib import Path

class TestInitCache(unittest.TestCase):

    def setUp(self):
        """Set up the test environment."""
        self.tmp_dir = Path(".tmp")
        # Clean up before the test, just in case
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def tearDown(self):
        """Clean up the test environment."""
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def test_initializes_cache_correctly(self):
        """
        Test that init_cache removes the old .tmp directory and creates a fresh .tmp/cache.
        """
        # 1. Create a "dirty" .tmp directory to simulate a previous run
        stale_cache_dir = self.tmp_dir / "cache"
        stale_cache_dir.mkdir(parents=True, exist_ok=True)

        stale_file = self.tmp_dir / "stale_file.txt"
        stale_file.touch()

        stale_cache_file = stale_cache_dir / "stale_cache_file.log"
        stale_cache_file.touch()

        self.assertTrue(stale_file.exists())
        self.assertTrue(stale_cache_file.exists())

        # 2. Run the tool
        args = ['ragmaker-init-cache']
        result = subprocess.run(args, capture_output=True, text=True, check=False, encoding='utf-8')

        # For debugging
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0, "Script execution failed")
        self.assertIn("success", result.stdout)

        # 3. Verify the results
        # The new cache directory should exist
        fresh_cache_dir = self.tmp_dir / "cache"
        self.assertTrue(fresh_cache_dir.exists())
        self.assertTrue(fresh_cache_dir.is_dir())

        # The stale files should be preserved (safe init)
        self.assertTrue(stale_file.exists(), "Stale file in .tmp root should be preserved")
        self.assertTrue(stale_cache_file.exists(), "Stale file in .tmp/cache should be preserved")

        # The new cache directory should NOT be empty (contains stale file)
        self.assertGreater(len(list(fresh_cache_dir.iterdir())), 0, "The .tmp/cache directory should contain existing files")

    def test_runs_when_tmp_does_not_exist(self):
        """
        Test that the tool runs without error when the .tmp directory doesn't exist.
        """
        self.assertFalse(self.tmp_dir.exists())

        # Run the tool
        args = ['ragmaker-init-cache']
        result = subprocess.run(args, capture_output=True, text=True, check=False, encoding='utf-8')

        self.assertEqual(result.returncode, 0, "Script execution failed")
        self.assertIn("success", result.stdout)

        # Verify the result
        fresh_cache_dir = self.tmp_dir / "cache"
        self.assertTrue(fresh_cache_dir.exists())
        self.assertTrue(fresh_cache_dir.is_dir())
        self.assertEqual(len(list(fresh_cache_dir.iterdir())), 0)

if __name__ == '__main__':
    unittest.main()
