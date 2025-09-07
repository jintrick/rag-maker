# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import json
import io

# Add src to path to allow importing ragmaker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import open_directory

class TestOpenDirectory(unittest.TestCase):

    @patch('ragmaker.tools.open_directory.os.path.isdir')
    @patch('ragmaker.tools.open_directory.subprocess.run')
    @patch('ragmaker.tools.open_directory.sys.platform', 'darwin') # macOS
    def test_open_directory_mac(self, mock_subprocess_run, mock_isdir):
        """Test that 'open' is called on macOS."""
        mock_isdir.return_value = True
        test_path = "/test/dir"
        open_directory.open_directory(test_path)
        mock_subprocess_run.assert_called_once_with(["open", test_path], check=True)

    @patch('ragmaker.tools.open_directory.os.path.isdir')
    @patch('ragmaker.tools.open_directory.subprocess.run')
    @patch('ragmaker.tools.open_directory.sys.platform', 'win32') # Windows
    def test_open_directory_windows(self, mock_subprocess_run, mock_isdir):
        """Test that 'explorer' is called on Windows."""
        mock_isdir.return_value = True
        test_path = "C:\\test\\dir"
        open_directory.open_directory(test_path)
        mock_subprocess_run.assert_called_once_with(["explorer", os.path.normpath(test_path)], check=True)

    @patch('ragmaker.tools.open_directory.os.path.isdir')
    @patch('ragmaker.tools.open_directory.subprocess.run')
    @patch('ragmaker.tools.open_directory.sys.platform', 'linux') # Linux
    def test_open_directory_linux(self, mock_subprocess_run, mock_isdir):
        """Test that 'xdg-open' is called on Linux."""
        mock_isdir.return_value = True
        test_path = "/test/dir"
        open_directory.open_directory(test_path)
        mock_subprocess_run.assert_called_once_with(["xdg-open", test_path], check=True)

    @patch('ragmaker.tools.open_directory.os.path.isdir')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_directory_not_found(self, mock_stderr, mock_isdir):
        """Test that an error is printed to stderr if the directory does not exist."""
        mock_isdir.return_value = False
        test_path = "/non/existent/dir"
        with self.assertRaises(SystemExit) as cm:
            open_directory.open_directory(test_path)

        self.assertEqual(cm.exception.code, 1)

        error_output = json.loads(mock_stderr.getvalue())
        self.assertEqual(error_output['status'], 'error')
        self.assertEqual(error_output['error_code'], 'DIRECTORY_NOT_FOUND')
        self.assertIn(test_path, error_output['message'])


if __name__ == '__main__':
    unittest.main()
