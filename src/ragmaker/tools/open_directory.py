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
from typing import Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)

try:
    from ragmaker.io_utils import eprint_error
except ImportError as e:
    logger.error(f"Failed to import from ragmaker.io_utils: {e}")
    def eprint_error(data: dict[str, Any]):
        print(json.dumps(data, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


def open_directory(path: str):
    """
    Opens the specified path in the default file manager.

    Args:
        path (str): The directory path to open.
    """
    if not os.path.isdir(path):
        eprint_error({
            "status": "error",
            "error_code": "DIRECTORY_NOT_FOUND",
            "message": f"The specified directory does not exist: {path}"
        })
        sys.exit(1)

    try:
        if sys.platform == "win32":
            subprocess.run(["explorer", os.path.normpath(path)], check=True)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else: # Assuming Linux or other Unix-like OS
            subprocess.run(["xdg-open", path], check=True)

        success_info = {
            "status": "success",
            "message": f"Successfully opened directory: {path}"
        }
        print(json.dumps(success_info, ensure_ascii=False))

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        eprint_error({
            "status": "error",
            "error_code": "COMMAND_EXECUTION_ERROR",
            "message": "Failed to open the directory using the OS default file manager.",
            "details": {
                "platform": sys.platform,
                "path": path,
                "error": str(e)
            }
        })
        sys.exit(1)
    except Exception as e:
        eprint_error({
            "status": "error",
            "error_code": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred.",
            "details": {
                "platform": sys.platform,
                "path": path,
                "error": str(e)
            }
        })
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
