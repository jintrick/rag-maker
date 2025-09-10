# -*- coding: utf-8 -*-
"""
A cross-platform tool to open a directory in the default file manager.
"""
import sys
import os
import subprocess
import json
import argparse
import logging

try:
    from ragmaker.io_utils import (
        handle_file_not_found_error,
        handle_unexpected_error
    )
except ImportError:
    # Fallback for local execution
    def handle_file_not_found_error(exception: FileNotFoundError): print(json.dumps({"status": "error", "message": f"File not found: {exception}"})); sys.exit(1)
    def handle_unexpected_error(exception: Exception): print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"})); sys.exit(1)


def open_directory(path: str):
    """
    Opens the specified path in the default file manager.
    """
    try:
        if not os.path.isdir(path):
            raise FileNotFoundError(f"The specified directory does not exist: {path}")

        if sys.platform == "win32":
            command = ["explorer", os.path.normpath(path)]
        elif sys.platform == "darwin":
            command = ["open", path]
        else: # Assuming Linux or other Unix-like OS
            command = ["xdg-open", path]

        subprocess.run(command, check=True)

        success_info = {
            "status": "success",
            "message": f"Successfully opened directory: {path}"
        }
        print(json.dumps(success_info, ensure_ascii=False))

    except FileNotFoundError as e:
        handle_file_not_found_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)


def main():
    """
    Parses command-line arguments and calls the main function.
    """
    parser = argparse.ArgumentParser(
        description="Open a directory in the default file manager."
    )
    parser.add_argument(
        "--path",
        required=True,
        help="The path to the directory to open."
    )
    args = parser.parse_args()
    open_directory(args.path)

if __name__ == "__main__":
    main()
