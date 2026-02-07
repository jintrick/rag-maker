# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io
import json

# Add src to path to allow importing ragmaker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import ask_dir

class TestAskDir(unittest.TestCase):

    @patch('ragmaker.tools.ask_dir.filedialog.askdirectory')
    @patch('ragmaker.tools.ask_dir.tk.Tk')
    def test_ask_dir_initial_dir(self, mock_tk, mock_askdirectory):
        """Test that askdirectory is called with the correct initial_dir (absolute path)."""
        input_initial_dir = "."
        expected_initial_dir = os.path.abspath(input_initial_dir)
        mock_askdirectory.return_value = "/selected/path"

        # Simulate running with --initial-dir .
        with patch.object(sys, 'argv', ['ragmaker-ask-dir', '--initial-dir', input_initial_dir]):
            ask_dir.main()

        # Check if askdirectory was called with absolute path
        mock_askdirectory.assert_called_once()
        args, kwargs = mock_askdirectory.call_args
        self.assertEqual(kwargs.get('initialdir'), expected_initial_dir)

    @patch('ragmaker.tools.ask_dir.filedialog.askdirectory')
    @patch('ragmaker.tools.ask_dir.tk.Tk')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_ask_dir_cancelled(self, mock_stderr, mock_tk, mock_askdirectory):
        """Test the behavior when user cancels the directory selection."""
        mock_askdirectory.return_value = "" # Cancelled

        with patch.object(sys, 'argv', ['ragmaker-ask-dir']):
            with self.assertRaises(SystemExit) as cm:
                ask_dir.main()
        
        self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
