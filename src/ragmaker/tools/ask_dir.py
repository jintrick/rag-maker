#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to display a GUI dialog prompting the user to select a directory.

This tool opens a native GUI dialog for the user to select a directory from the file system.
It is designed to be integrated into an AI agent's workflow, outputting structured JSON to
stdout or stderr depending on the user's action (selection or cancellation).
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import json
import argparse
import os
from typing import Any, Optional, List, Union

# --- Dependency Check ---
try:
    from ragmaker.io_utils import eprint_error, handle_unexpected_error
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

# Conditional import for Windows
if sys.platform == 'win32':
    try:
        import pythoncom
        from win32com.shell import shell, shellcon
        PYWIN32_AVAILABLE = True
    except ImportError:
        PYWIN32_AVAILABLE = False
else:
    PYWIN32_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None
    filedialog = None

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Structured Error Handling (Tool-specific) ---
def handle_user_cancellation():
    """Handles user cancellation of the dialog."""
    eprint_error({
        "status": "error",
        "error_code": "USER_CANCELLED",
        "message": "Directory selection was cancelled by the user.",
        "remediation_suggestion": "Please re-run the command and select a directory."
    })

def _ask_directory_windows(initial_dir: Optional[str], multiple: bool) -> Union[str, List[str], None]:
    """
    Uses Windows IFileOpenDialog to select directory(ies).
    Returns path(s) or None if cancelled.
    """
    pythoncom.CoInitialize()
    try:
        # Create IFileOpenDialog object
        # CLSID_FileOpenDialog = "{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}"
        # IID_IFileOpenDialog = "{d57c7288-d4ad-4768-be02-9d969532d960}"
        dialog = pythoncom.CoCreateInstance(
            shell.CLSID_FileOpenDialog,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IFileOpenDialog
        )

        # Set options
        options = dialog.GetOptions()
        options |= shellcon.FOS_PICKFOLDERS
        if multiple:
            options |= shellcon.FOS_ALLOWMULTISELECT
        dialog.SetOptions(options)

        if initial_dir:
            try:
                item = shell.SHCreateItemFromParsingName(initial_dir, None, shell.IID_IShellItem)
                dialog.SetFolder(item)
            except Exception:
                # If initial dir is invalid, ignore it
                pass

        dialog.Show(None)

        results = dialog.GetResults()
        count = results.GetCount()
        paths = []
        for i in range(count):
            item = results.GetItemAt(i)
            path = item.GetDisplayName(shellcon.SIGDN_FILESYSPATH)
            paths.append(path)

        if not paths:
            return None

        if multiple:
            return paths
        else:
            return paths[0]

    except pythoncom.com_error as e:
        # HRESULT 0x800704C7 is cancelled (-2147023673)
        if e.hresult == -2147023673:
            return None
        raise
    finally:
        pythoncom.CoUninitialize()

# --- Core Logic ---
def ask_for_directory(initial_dir: Optional[str] = None, multiple: bool = False) -> None:
    """
    Displays a directory selection dialog and outputs the result based on user selection.
    """
    try:
        if initial_dir:
            # Ensure path is absolute and uses the OS-native separator (especially for Windows)
            initial_dir = os.path.normpath(os.path.abspath(initial_dir))

        selected = None
        used_method = "tkinter"

        if sys.platform == 'win32' and PYWIN32_AVAILABLE:
            try:
                selected = _ask_directory_windows(initial_dir, multiple)
                used_method = "win32"
            except Exception:
                # Fallback to tkinter if something goes wrong with COM
                used_method = "tkinter"

        if used_method == "tkinter":
            if tk is None:
                 eprint_error({
                    "status": "error",
                    "error_code": "DEPENDENCY_ERROR",
                    "message": "Required library 'tkinter' not found and native Windows dialog unavailable.",
                    "remediation_suggestion": (
                        "Please install the tkinter library for your Python distribution. "
                        "For example, on Debian/Ubuntu, run: sudo apt-get install python3-tk"
                    )
                })
                 sys.exit(1)

            if multiple and sys.platform != 'win32':
                 # Warn about fallback on non-windows
                 sys.stderr.write('{"status": "warning", "message": "Multiple selection is not supported on this platform/configuration. Falling back to single selection."}\n')

            # Note: Even if multiple is True on Windows but we fell back to Tkinter (e.g. COM error),
            # Tkinter doesn't support multiple folders. So we proceed with single selection.

            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.attributes("-topmost", True)  # Bring the dialog to the front
            root.update() # Force update to ensure attributes and initialdir are respected

            selected_path = filedialog.askdirectory(
                title="Select a directory",
                initialdir=initial_dir
            )

            if selected_path:
                if multiple:
                    selected = [selected_path]
                else:
                    selected = selected_path
            else:
                selected = None

        if selected is not None:
            # User selected directory(ies)
            if multiple:
                result = {
                    "status": "success",
                    "selected_directories": selected
                }
            else:
                result = {
                    "status": "success",
                    "selected_directory": selected
                }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # User cancelled the dialog
            handle_user_cancellation()
            sys.exit(1)

    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="A tool to display a GUI dialog for directory selection.")
    parser.add_argument("--initial-dir", help="The initial directory to display in the dialog.")
    parser.add_argument("--multiple", action="store_true", help="Allow selecting multiple directories (Windows only).")
    args = parser.parse_args()
    
    ask_for_directory(initial_dir=args.initial_dir, multiple=args.multiple)


if __name__ == "__main__":
    main()
