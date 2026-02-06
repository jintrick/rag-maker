# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io

# Add src to path to allow importing ragmaker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import open_directory

class TestOpenDirectory(unittest.TestCase):

    @patch('ragmaker.tools.open_directory.subprocess.Popen')
    @patch('ragmaker.tools.open_directory.subprocess.run')
    @patch('ragmaker.tools.open_directory.os.path.isdir', return_value=True)
    def test_open_directory_platform(self, mock_isdir, mock_subprocess_run, mock_subprocess_popen):
        """Test that the correct command is called on different platforms."""
        test_path = "/test/dir"

        # Test macOS
        with patch('sys.platform', 'darwin'):
            open_directory.open_directory(test_path)
            mock_subprocess_run.assert_called_with(["open", test_path], check=True)

        # Test Windows
        with patch('sys.platform', 'win32'):
            open_directory.open_directory(test_path)
            mock_subprocess_popen.assert_called_with(["explorer", os.path.normpath(test_path)])

        # Test Linux
        with patch('sys.platform', 'linux'):
            open_directory.open_directory(test_path)
            mock_subprocess_run.assert_called_with(["xdg-open", test_path], check=True)


    @patch('ragmaker.tools.open_directory.os.path.isdir', return_value=False)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_directory_not_found(self, mock_stderr, mock_isdir):
        """Test that an error is printed to stderr if the directory does not exist."""
        test_path = "/non/existent/dir"

        # We need to test the main function to ensure the correct eprint_error is called
        with patch.object(sys, 'argv', ['prog_name', '--path', test_path]):
            with self.assertRaises(SystemExit) as cm:
                open_directory.main()

        self.assertEqual(cm.exception.code, 1)

        error_output = json.loads(mock_stderr.getvalue())
        self.assertEqual(error_output['status'], 'error')
        self.assertEqual(error_output['error_code'], 'FILE_NOT_FOUND')
        self.assertIn(test_path, error_output['message'])


if __name__ == '__main__':
    unittest.main()
