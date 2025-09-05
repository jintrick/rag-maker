import unittest
import sys
import os
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))
import http_fetch

class TestHttpPathHandlingIntegration(unittest.TestCase):

    def setUp(self):
        self.base_test_dir = "test_temp_http_fetch"
        if os.path.exists(self.base_test_dir):
            shutil.rmtree(self.base_test_dir)
        os.makedirs(self.base_test_dir)

    def tearDown(self):
        if os.path.exists(self.base_test_dir):
            shutil.rmtree(self.base_test_dir)

    def run_test_case(self, input_path_part, expected_sanitized_part):
        """Helper to run a single path sanitization test case."""
        # The script will create the directory inside our base test dir
        full_input_path = os.path.join(self.base_test_dir, input_path_part)
        
        mock_args = MagicMock()
        # Pass the full path to the script
        mock_args.temp_dir = full_input_path
        mock_args.url = "http://example.com"
        mock_args.base_url = "http://example.com"
        mock_args.verbose = False
        mock_args.log_level = 'INFO'
        mock_args.recursive = False
        mock_args.depth = 1

        with patch('http_fetch.GracefulArgumentParser.parse_args', return_value=mock_args):
            with patch('http_fetch.WebFetcher'): # Stop network calls
                if sys.platform != "win32":
                    self.skipTest("Path sanitization test is for Windows.")

                if not expected_sanitized_part:
                    with patch('http_fetch.eprint_error') as mock_eprint:
                        with self.assertRaises(SystemExit):
                            http_fetch.main()
                        mock_eprint.assert_called_once_with({
                            "status": "error",
                            "error_code": "INVALID_PATH_ERROR",
                            "message": "Provided --temp-dir path is empty after removing quotes and spaces.",
                        })
                else:
                    http_fetch.main()
                    full_expected_path = os.path.join(self.base_test_dir, expected_sanitized_part)
                    self.assertTrue(os.path.isdir(full_expected_path), f"Directory '{full_expected_path}' was not created.")

    def test_path_sanitization_scenarios(self):
        """Tests various path sanitization scenarios for http_fetch."""
        test_cases = {
            "No quotes": ("temp", "temp"),
            "Simple quotes": ("'temp'", "temp"),
            "Double quotes": ('"temp"', "temp"),
            # "Multiple quotes": ('""temp""'', "temp"), # This case is removed due to string literal issues
            "Quotes with spaces": (' " temp " ', "temp"),
            "Empty path after strip": (' " " ', ""),
        }

        for name, (input_part, expected_part) in test_cases.items():
            with self.subTest(name=name):
                self.run_test_case(input_part, expected_part)

    def test_empty_path_triggers_exit(self):
        """
        Verify that main() calls sys.exit(1) when the path is empty.
        This test isolates the empty path check logic.
        """
        if sys.platform != "win32":
            self.skipTest("Path sanitization test is for Windows.")

        # Mock args to simulate an empty path after sanitization
        mock_args = MagicMock()
        mock_args.temp_dir = "" # This is the crucial part
        mock_args.verbose = False
        mock_args.log_level = 'INFO'

        # Patch parse_args to return our controlled args
        # Patch eprint_error to prevent it from printing during the test
        with patch('http_fetch.GracefulArgumentParser.parse_args', return_value=mock_args), \
             patch('http_fetch.eprint_error'):
            # We expect SystemExit to be raised by sys.exit(1)
            with self.assertRaises(SystemExit):
                http_fetch.main()

if __name__ == '__main__':
    unittest.main()