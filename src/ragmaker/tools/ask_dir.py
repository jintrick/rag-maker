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

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None
    filedialog = None

try:
    import tkfilebrowser
except (ImportError, Exception):
    tkfilebrowser = None

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

        if tk is None:
             eprint_error({
                "status": "error",
                "error_code": "DEPENDENCY_ERROR",
                "message": "Required library 'tkinter' not found.",
                "remediation_suggestion": (
                    "Please install the tkinter library for your Python distribution. "
                    "For example, on Debian/Ubuntu, run: sudo apt-get install python3-tk"
                )
            })
             sys.exit(1)

        # tkfilebrowser also depends on tkinter, so we check tk first.
        # If multiple selection is requested, we need tkfilebrowser.
        if multiple and tkfilebrowser is None:
             eprint_error({
                "status": "error",
                "error_code": "DEPENDENCY_ERROR",
                "message": "Required library 'tkfilebrowser' not found for multiple selection.",
                "remediation_suggestion": "Please install the 'tkfilebrowser' package: pip install tkfilebrowser"
            })
             sys.exit(1)

        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes("-topmost", True)  # Bring the dialog to the front
        root.update() # Force update to ensure attributes and initialdir are respected

        if multiple:
            # Use tkfilebrowser for multiple selection
            paths = tkfilebrowser.askopendirnames(
                title="Select Folders",
                initialdir=initial_dir
            )
            if paths:
                selected = list(paths)
        else:
            # Use tkfilebrowser for single selection to maintain UI consistency
            path = tkfilebrowser.askopendirname(
                title="Select Folder",
                initialdir=initial_dir
            )
            if path:
                selected = path

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
    parser.add_argument("--multiple", action="store_true", help="Allow selecting multiple directories.")
    args = parser.parse_args()
    
    ask_for_directory(initial_dir=args.initial_dir, multiple=args.multiple)


if __name__ == "__main__":
    main()
