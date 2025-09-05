import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path

class TestMakeCacheDir(unittest.TestCase):

    def setUp(self):
        """Set up temporary directories for tests."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.kb_root = Path(self.test_dir.name) / "test_kb"
        self.kb_root.mkdir()

        self.script_path = Path(__file__).resolve().parent.parent / "tools" / "make_cache_dir.py"
        self.relative_path = "new/test/dir"

    def tearDown(self):
        """Clean up the temporary directories."""
        self.test_dir.cleanup()

    def test_with_kb_root(self):
        """Test directory creation when --kb-root is provided."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--relative-path", self.relative_path,
                "--kb-root", str(self.kb_root)
            ],
            capture_output=True, text=True, check=False
        )

        print("STDOUT (with kb-root):", result.stdout)
        print("STDERR (with kb-root):", result.stderr)

        self.assertEqual(result.returncode, 0, "Script execution failed")

        expected_dir = self.kb_root / "cache" / self.relative_path
        self.assertTrue(expected_dir.exists(), f"Directory {expected_dir} was not created")
        self.assertTrue(expected_dir.is_dir(), f"{expected_dir} is not a directory")

    def test_without_kb_root_legacy(self):
        """Test directory creation when --kb-root is NOT provided (legacy behavior)."""
        # The script should create the cache dir relative to the CWD
        # We'll use a temporary directory as the CWD for the subprocess
        with tempfile.TemporaryDirectory() as temp_cwd:
            result = subprocess.run(
                [
                    sys.executable, str(self.script_path),
                    "--relative-path", self.relative_path
                ],
                cwd=temp_cwd, # Run the script from this directory
                capture_output=True, text=True, check=False
            )

            print("STDOUT (without kb-root):", result.stdout)
            print("STDERR (without kb-root):", result.stderr)

            self.assertEqual(result.returncode, 0, "Script execution failed")

            expected_dir = Path(temp_cwd) / "cache" / self.relative_path
            self.assertTrue(expected_dir.exists(), f"Directory {expected_dir} was not created in CWD")
            self.assertTrue(expected_dir.is_dir(), f"{expected_dir} is not a directory")


if __name__ == '__main__':
    unittest.main()
