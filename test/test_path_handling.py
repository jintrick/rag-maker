import unittest
import sys
import os
import shutil
import subprocess
from pathlib import Path

class TestHttpPathHandlingIntegration(unittest.TestCase):

    def setUp(self):
        self.base_test_dir = Path("test_temp_http_fetch")
        if self.base_test_dir.exists():
            shutil.rmtree(self.base_test_dir)
        self.base_test_dir.mkdir()

    def tearDown(self):
        if self.base_test_dir.exists():
            shutil.rmtree(self.base_test_dir)

    def run_test_case(self, input_path_part, expected_sanitized_part):
        """Helper to run a single path sanitization test case."""
        if sys.platform != "win32":
            self.skipTest("Path sanitization test is for Windows.")

        # The script will create the directory inside our base test dir
        full_input_path = self.base_test_dir / input_path_part
        
        args = [
            "ragmaker-http-fetch",
            "--url", "http://example.com",
            "--base-url", "http://example.com",
            "--temp-dir", str(full_input_path),
            "--no-recursive"
        ]

        # We patch the WebFetcher to avoid actual network calls
        # This is a bit tricky with subprocess, so for now we let it make the call
        # as it's just to example.com and won't affect the path handling test.
        process = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')

        if not expected_sanitized_part:
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("INVALID_PATH_ERROR", process.stderr)
        else:
            if process.returncode != 0:
                print("STDERR:", process.stderr)
            self.assertEqual(process.returncode, 0)
            full_expected_path = self.base_test_dir / expected_sanitized_part
            # The tool should create the directory, but since we are not mocking the fetcher,
            # it will also create the html file. We just check for the directory.
            self.assertTrue(full_expected_path.is_dir(), f"Directory '{full_expected_path}' was not created.")

    def test_path_sanitization_scenarios(self):
        """Tests various path sanitization scenarios for http_fetch."""
        test_cases = {
            "No quotes": ("temp", "temp"),
            "Simple quotes": ("'temp'", "temp"),
            "Double quotes": ('"temp"', "temp"),
            "Quotes with spaces": (' " temp " ', "temp"),
            "Empty path after strip": (' " " ', ""),
        }

        for name, (input_part, expected_part) in test_cases.items():
            with self.subTest(name=name):
                # Recreate the directory for each subtest to avoid conflicts
                if self.base_test_dir.exists():
                    shutil.rmtree(self.base_test_dir)
                self.base_test_dir.mkdir()
                self.run_test_case(input_part, expected_part)

if __name__ == '__main__':
    unittest.main()
