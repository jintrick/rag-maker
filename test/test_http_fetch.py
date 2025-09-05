import unittest
import subprocess
import tempfile
import shutil
from pathlib import Path

class TestHttpFetch(unittest.TestCase):

    def test_output_directory_creation(self):
        """
        Test that http_fetch.py creates the output directory if it does not exist.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a non-existent directory path
            output_dir = Path(temp_dir) / "non_existent_dir"
            self.assertFalse(output_dir.exists())

            # Use a real, simple, and reliable URL for testing.
            url = "http://example.com"

            process = subprocess.run(
                [
                    "python",
                    "tools/http_fetch.py",
                    "--url", url,
                    "--base-url", url,
                    "--output-dir", str(output_dir),
                    "--no-recursive" # Don't follow links for this simple test
                ],
                capture_output=True,
                text=True
            )

            if process.returncode != 0:
                print("HttpFetch STDERR:", process.stderr)

            self.assertEqual(process.returncode, 0, "http_fetch.py script failed")

            # The tool should create the directory.
            self.assertTrue(output_dir.exists())
            # And it should contain the fetched page.
            self.assertTrue((output_dir / "page_0.html").exists())

if __name__ == '__main__':
    unittest.main()
