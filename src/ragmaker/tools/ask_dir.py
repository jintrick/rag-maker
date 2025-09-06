#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ユーザーにディレクトリの選択を促すGUIダイアログを表示するツール。

このツールは、ユーザーがファイルシステムからディレクトリを選択するための
ネイティブなGUIダイアログを開きます。AIエージェントのワークフローに
組み込まれることを想定しており、ユーザーの操作結果（選択またはキャンセル）に
応じて、標準出力または標準エラーに構造化されたJSONを出力します。

Usage:
    python ask_dir.py

Returns:
    (stdout): ユーザーがディレクトリを選択した場合、成功を示すJSONオブジェクト。
              例: {
                    "status": "success",
                    "selected_directory": "/path/to/selected/directory"
                  }
    (stderr): ユーザーがダイアログをキャンセルしたか、エラーが発生した場合、
              エラーコードと詳細を含むJSONオブジェクト。
"""

import json
import sys
import logging

# --- Dependency Check ---
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    # `eprint_error` is not yet defined, so print directly.
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required library 'tkinter' not found.",
        "remediation_suggestion": (
            "Please install the tkinter library for your Python distribution. "
            "For example, on Debian/Ubuntu, run: sudo apt-get install python3-tk"
        )
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Structured Error Handling ---
def eprint_error(error_obj: dict):
    """Prints a structured error object as JSON to stderr."""
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

def handle_user_cancellation():
    """Handles user cancellation of the dialog."""
    eprint_error({
        "status": "error",
        "error_code": "USER_CANCELLED",
        "message": "Directory selection was cancelled by the user.",
        "remediation_suggestion": "Please re-run the command and select a directory."
    })

def handle_unexpected_error(exception: Exception):
    """Handles unexpected errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred while trying to open the directory dialog.",
        "remediation_suggestion": "Ensure your environment supports GUI applications.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })


# --- Core Logic ---

def ask_for_directory() -> None:
    """
    ディレクトリ選択ダイアログを表示し、ユーザーの選択に基づいて結果を出力する。
    """
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes("-topmost", True)  # Bring the dialog to the front

        selected_path = filedialog.askdirectory(
            title="Select a directory to save the markdown files"
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )
    ask_for_directory()


if __name__ == "__main__":
    main()
