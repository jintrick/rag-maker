import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import io
import os
import importlib

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import ask_dir

class TestAskDir(unittest.TestCase):

    def setUp(self):
        # Redirect stdout/stderr
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.patcher_stdout = patch('sys.stdout', self.stdout)
        self.patcher_stderr = patch('sys.stderr', self.stderr)
        self.patcher_stdout.start()
        self.patcher_stderr.start()

    def tearDown(self):
        self.patcher_stdout.stop()
        self.patcher_stderr.stop()

    def test_argument_parsing(self):
        # Test that main parses --multiple correctly
        with patch('ragmaker.tools.ask_dir.ask_for_directory') as mock_ask:
            with patch('sys.argv', ['ragmaker-ask-dir', '--multiple', '--initial-dir', '/tmp']):
                ask_dir.main()
                mock_ask.assert_called_with(initial_dir='/tmp', multiple=True)

            with patch('sys.argv', ['ragmaker-ask-dir']):
                ask_dir.main()
                mock_ask.assert_called_with(initial_dir=None, multiple=False)

    def test_multiple_selection_success(self):
        # Mock tkfilebrowser and tkinter
        mock_tk = MagicMock()
        mock_tkfilebrowser = MagicMock()

        with patch('ragmaker.tools.ask_dir.tk', mock_tk), \
             patch('ragmaker.tools.ask_dir.tkfilebrowser', mock_tkfilebrowser):

            # Setup mock return for askopendirnames
            mock_tkfilebrowser.askopendirnames.return_value = ["/path/dir1", "/path/dir2"]

            ask_dir.ask_for_directory(multiple=True)

            # Verify call
            mock_tkfilebrowser.askopendirnames.assert_called_once()

            # Verify output
            output = self.stdout.getvalue()
            data = json.loads(output)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['selected_directories'], ["/path/dir1", "/path/dir2"])

    def test_single_selection_success(self):
        # Mock tkinter.filedialog
        mock_tk = MagicMock()
        mock_filedialog = MagicMock()

        with patch('ragmaker.tools.ask_dir.tk', mock_tk), \
             patch('ragmaker.tools.ask_dir.filedialog', mock_filedialog):

            mock_filedialog.askdirectory.return_value = "/path/single"

            ask_dir.ask_for_directory(multiple=False)

            mock_filedialog.askdirectory.assert_called_once()

            output = self.stdout.getvalue()
            data = json.loads(output)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['selected_directory'], "/path/single")

    def test_cancel_multiple(self):
        with patch('ragmaker.tools.ask_dir.tk'), \
             patch('ragmaker.tools.ask_dir.tkfilebrowser') as mock_tkfilebrowser:

            mock_tkfilebrowser.askopendirnames.return_value = [] # Cancelled returns empty list/tuple

            with self.assertRaises(SystemExit):
                ask_dir.ask_for_directory(multiple=True)

            err_output = self.stderr.getvalue()
            self.assertIn("USER_CANCELLED", err_output)

    def test_cancel_single(self):
        with patch('ragmaker.tools.ask_dir.tk'), \
             patch('ragmaker.tools.ask_dir.filedialog') as mock_filedialog:

            mock_filedialog.askdirectory.return_value = "" # Cancelled returns empty string

            with self.assertRaises(SystemExit):
                ask_dir.ask_for_directory(multiple=False)

            err_output = self.stderr.getvalue()
            self.assertIn("USER_CANCELLED", err_output)

    def test_missing_tkfilebrowser_for_multiple(self):
        # Simulate tkfilebrowser missing (None)
        with patch('ragmaker.tools.ask_dir.tk'), \
             patch('ragmaker.tools.ask_dir.tkfilebrowser', None):

            with self.assertRaises(SystemExit):
                ask_dir.ask_for_directory(multiple=True)

            err_output = self.stderr.getvalue()
            self.assertIn("DEPENDENCY_ERROR", err_output)
            self.assertIn("tkfilebrowser", err_output)

if __name__ == '__main__':
    unittest.main()
