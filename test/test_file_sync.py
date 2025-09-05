import unittest
import subprocess
import tempfile
import shutil
from pathlib import Path
import os

class TestFileSync(unittest.TestCase):

    def test_dest_directory_creation(self):
        """
        Test that file_sync.py creates the destination directory if it does not exist.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Create a source directory with a dummy file
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            dummy_file = source_dir / "test.txt"
            dummy_file.write_text("hello")

            # 2. Define a non-existent destination directory
            dest_dir = Path(temp_dir) / "destination"
            self.assertFalse(dest_dir.exists())

            # 3. Run the file_sync.py tool
            process = subprocess.run(
                [
                    "python",
                    "tools/file_sync.py",
                    "--source-dir", str(source_dir),
                    "--dest-dir", str(dest_dir)
                ],
                capture_output=True,
                text=True
            )

            # Print stderr for debugging if the process fails
            if process.returncode != 0:
                print("FileSync STDERR:", process.stderr)

            self.assertEqual(process.returncode, 0, "file_sync.py script failed")

            # 4. Assert that the destination directory and the file were created
            self.assertTrue(dest_dir.exists())
            self.assertTrue((dest_dir / "test.txt").exists())
            self.assertEqual((dest_dir / "test.txt").read_text(), "hello")


if __name__ == '__main__':
    unittest.main()
