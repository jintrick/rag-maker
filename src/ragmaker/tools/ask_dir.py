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
from typing import Any, Optional

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
def ask_for_directory(initial_dir: Optional[str] = None) -> None:
    """
    Displays a directory selection dialog and outputs the result based on user selection.
    """
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes("-topmost", True)  # Bring the dialog to the front
        root.update() # Force update to ensure attributes and initialdir are respected

        if initial_dir:
            # Ensure path is absolute and uses the OS-native separator (especially for Windows)
            initial_dir = os.path.normpath(os.path.abspath(initial_dir))

        selected_path = filedialog.askdirectory(
            title="Select a directory",
            initialdir=initial_dir
        )

        if selected_path:
            # User selected a directory
            result = {
                "status": "success",
                "selected_directory": selected_path
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # User cancelled the dialog
            handle_user_cancellation()
            sys.exit(1)

    except Exception as e:
        logger.exception("An unexpected error occurred in ask_for_directory.")
        handle_unexpected_error(e)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="A tool to display a GUI dialog for directory selection.")
    parser.add_argument("--initial-dir", help="The initial directory to display in the dialog.")
    args = parser.parse_args()
    
    ask_for_directory(initial_dir=args.initial_dir)


if __name__ == "__main__":
    main()