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

class TestAskDirIssue(unittest.TestCase):

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

    def test_windows_multiple_flag_check(self):
        # Mock sys.platform to win32
        with patch('sys.platform', 'win32'):
            # Setup mocks for win32com
            mock_pythoncom = MagicMock()
            mock_win32com_shell_pkg = MagicMock()
            mock_shell_mod = MagicMock()
            mock_shellcon_mod = MagicMock()
            mock_win32com_shell_pkg.shell = mock_shell_mod
            mock_win32com_shell_pkg.shellcon = mock_shellcon_mod

            # Define constants
            # Values are arbitrary but distinct for testing
            mock_shellcon_mod.FOS_PICKFOLDERS = 0x0020
            mock_shellcon_mod.FOS_FORCEFILESYSTEM = 0x0040
            mock_shellcon_mod.FOS_ALLOWMULTISELECT = 0x0200
            mock_shellcon_mod.SIGDN_FILESYSPATH = 0x80058000

            modules = {
                'pythoncom': mock_pythoncom,
                'win32com': MagicMock(),
                'win32com.shell': mock_win32com_shell_pkg,
                'tkinter': MagicMock(),
                'tkinter.filedialog': MagicMock()
            }

            with patch.dict('sys.modules', modules):
                importlib.reload(ask_dir)

                mock_dialog = MagicMock()
                mock_pythoncom.CoCreateInstance.return_value = mock_dialog

                # Mock GetOptions to return 0 initially
                mock_dialog.GetOptions.return_value = 0

                # Mock GetResults
                mock_results = MagicMock()
                mock_dialog.GetResults.return_value = mock_results
                mock_results.GetCount.return_value = 2

                item1 = MagicMock()
                item1.GetDisplayName.return_value = r"C:\Folder1"
                item2 = MagicMock()
                item2.GetDisplayName.return_value = r"C:\File1.txt"
                mock_results.GetItemAt.side_effect = [item1, item2]

                # Mock os.path.isdir
                with patch('os.path.isdir') as mock_isdir:
                    # Configure isdir to return True only for C:\Folder1
                    def isdir_side_effect(path):
                        return path == r"C:\Folder1"
                    mock_isdir.side_effect = isdir_side_effect

                    ask_dir.ask_for_directory(multiple=True)

                # Check output
                output = self.stdout.getvalue()
                try:
                    data = json.loads(output)
                except json.JSONDecodeError:
                    print("STDOUT:", output)
                    print("STDERR:", self.stderr.getvalue())
                    raise

                self.assertEqual(data['status'], 'success')
                # Should only contain the directory
                self.assertEqual(data['selected_directories'], [r"C:\Folder1"])

                # Verify options set
                # Expected: FOS_ALLOWMULTISELECT | FOS_FORCEFILESYSTEM
                # NOT FOS_PICKFOLDERS
                args, _ = mock_dialog.SetOptions.call_args
                options_set = args[0]

                self.assertTrue(options_set & mock_shellcon_mod.FOS_ALLOWMULTISELECT)
                self.assertTrue(options_set & mock_shellcon_mod.FOS_FORCEFILESYSTEM)
                self.assertFalse(options_set & mock_shellcon_mod.FOS_PICKFOLDERS, "FOS_PICKFOLDERS should NOT be set when multiple=True")

    def test_windows_single_flag_check(self):
         with patch('sys.platform', 'win32'):
            # Setup mocks for win32com
            mock_pythoncom = MagicMock()
            mock_win32com_shell_pkg = MagicMock()
            mock_shell_mod = MagicMock()
            mock_shellcon_mod = MagicMock()
            mock_win32com_shell_pkg.shell = mock_shell_mod
            mock_win32com_shell_pkg.shellcon = mock_shellcon_mod

            # Define constants
            mock_shellcon_mod.FOS_PICKFOLDERS = 0x0020
            mock_shellcon_mod.FOS_FORCEFILESYSTEM = 0x0040
            mock_shellcon_mod.FOS_ALLOWMULTISELECT = 0x0200
            mock_shellcon_mod.SIGDN_FILESYSPATH = 0x80058000

            modules = {
                'pythoncom': mock_pythoncom,
                'win32com': MagicMock(),
                'win32com.shell': mock_win32com_shell_pkg,
                'tkinter': MagicMock(),
                'tkinter.filedialog': MagicMock()
            }

            with patch.dict('sys.modules', modules):
                importlib.reload(ask_dir)

                mock_dialog = MagicMock()
                mock_pythoncom.CoCreateInstance.return_value = mock_dialog
                mock_dialog.GetOptions.return_value = 0

                item1 = MagicMock()
                item1.GetDisplayName.return_value = r"C:\Folder1"
                mock_dialog.GetResult.return_value = item1

                ask_dir.ask_for_directory(multiple=False)

                output = self.stdout.getvalue()
                data = json.loads(output)
                self.assertEqual(data['status'], 'success')
                self.assertEqual(data['selected_directory'], r"C:\Folder1")

                # Verify options set
                # Expected: FOS_PICKFOLDERS
                args, _ = mock_dialog.SetOptions.call_args
                options_set = args[0]

                self.assertTrue(options_set & mock_shellcon_mod.FOS_PICKFOLDERS, "FOS_PICKFOLDERS SHOULD be set when multiple=False")

if __name__ == '__main__':
    unittest.main()
