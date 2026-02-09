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

    def test_windows_multiple_success(self):
        # Mock sys.platform to win32
        with patch('sys.platform', 'win32'):

            # Setup mocks for win32com
            mock_pythoncom = MagicMock()

            # The structure for `from win32com.shell import shell, shellcon`
            # implies win32com.shell is a module with attributes `shell` and `shellcon`
            mock_win32com_shell_pkg = MagicMock()
            mock_shell_mod = MagicMock()
            mock_shellcon_mod = MagicMock()

            mock_win32com_shell_pkg.shell = mock_shell_mod
            mock_win32com_shell_pkg.shellcon = mock_shellcon_mod

            # Populate sys.modules so import works
            modules = {
                'pythoncom': mock_pythoncom,
                'win32com': MagicMock(),
                'win32com.shell': mock_win32com_shell_pkg,
                'tkinter': MagicMock(),
                'tkinter.filedialog': MagicMock()
            }

            with patch.dict('sys.modules', modules):
                # Need to reload ask_dir to pick up sys.platform='win32' and mocked modules
                importlib.reload(ask_dir)

                # Setup specific returns
                mock_dialog = MagicMock()
                mock_pythoncom.CoCreateInstance.return_value = mock_dialog

                # Mock GetResults
                mock_results = MagicMock()
                mock_dialog.GetResults.return_value = mock_results
                mock_results.GetCount.return_value = 2

                item1 = MagicMock()
                item1.GetDisplayName.return_value = r"C:\Folder1"
                item2 = MagicMock()
                item2.GetDisplayName.return_value = r"C:\Folder2"
                mock_results.GetItemAt.side_effect = [item1, item2]

                # Run function
                with patch('os.path.isdir', return_value=True):
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
                self.assertEqual(data['selected_directories'], [r"C:\Folder1", r"C:\Folder2"])

                # Verify COM calls
                mock_pythoncom.CoInitialize.assert_called()
                mock_pythoncom.CoUninitialize.assert_called()
                # Verify options set
                mock_dialog.GetOptions.assert_called()
                mock_dialog.SetOptions.assert_called()

                # Verify that GetResults was called
                mock_dialog.GetResults.assert_called_once()
                # Verify that GetResult was NOT called
                mock_dialog.GetResult.assert_not_called()

    def test_windows_single_success(self):
        with patch('sys.platform', 'win32'):
            mock_pythoncom = MagicMock()

            mock_win32com_shell_pkg = MagicMock()
            mock_shell_mod = MagicMock()
            mock_shellcon_mod = MagicMock()
            mock_win32com_shell_pkg.shell = mock_shell_mod
            mock_win32com_shell_pkg.shellcon = mock_shellcon_mod

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

                # Mock GetResult for single selection
                item1 = MagicMock()
                item1.GetDisplayName.return_value = r"C:\Folder1"
                mock_dialog.GetResult.return_value = item1

                ask_dir.ask_for_directory(multiple=False)

                output = self.stdout.getvalue()
                data = json.loads(output)
                self.assertEqual(data['status'], 'success')
                self.assertEqual(data['selected_directory'], r"C:\Folder1")

                # Verify that GetResult was called
                mock_dialog.GetResult.assert_called_once()
                # Verify that GetResults was NOT called
                mock_dialog.GetResults.assert_not_called()

    def test_fallback_linux_multiple(self):
        # Mock sys.platform to linux
        with patch('sys.platform', 'linux'):
            # Mock tkinter
            mock_tk = MagicMock()
            mock_filedialog = MagicMock()
            # Ensure from tkinter import filedialog works as expected with mocks
            mock_tk.filedialog = mock_filedialog

            with patch.dict('sys.modules', {
                'tkinter': mock_tk,
                'tkinter.filedialog': mock_filedialog
            }):
                importlib.reload(ask_dir)

                # Note: askdirectory returns string, not list
                mock_filedialog.askdirectory.return_value = "/tmp/selected"

                ask_dir.ask_for_directory(multiple=True)

                # Check stderr for warning
                warnings = self.stderr.getvalue()
                self.assertIn("Multiple selection is not supported", warnings)

                # Check stdout for result
                output = self.stdout.getvalue()
                data = json.loads(output)
                self.assertEqual(data['status'], 'success')
                self.assertEqual(data['selected_directories'], ["/tmp/selected"])

    def test_fallback_windows_no_pywin32(self):
        # Windows but import fails
        with patch('sys.platform', 'win32'):
            # Don't mock win32 modules, so import fails naturally (on Linux env)

            mock_tk = MagicMock()
            mock_filedialog = MagicMock()
            mock_tk.filedialog = mock_filedialog

            with patch.dict('sys.modules', {
                'tkinter': mock_tk,
                'tkinter.filedialog': mock_filedialog,
                'pythoncom': None,
                'win32com': None,
                'win32com.shell': None
            }):
                importlib.reload(ask_dir)

                # Verify PYWIN32_AVAILABLE is False
                self.assertFalse(ask_dir.PYWIN32_AVAILABLE)

                mock_filedialog.askdirectory.return_value = r"C:\Fallback"

                ask_dir.ask_for_directory(multiple=True)

                output = self.stdout.getvalue()
                data = json.loads(output)
                self.assertEqual(data['status'], 'success')
                self.assertEqual(data['selected_directories'], [r"C:\Fallback"])

                # Should NOT print warning on Windows even if fallback
                self.assertNotIn("Multiple selection is not supported", self.stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
