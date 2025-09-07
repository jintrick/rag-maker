# -*- coding: utf-8 -*-
"""
A cross-platform tool to open a directory in the default file manager.
"""
import sys
import os
import subprocess
import json
import argparse

def open_directory(path: str):
    """
    Opens the specified path in the default file manager.

    Args:
        path (str): The directory path to open.
    """
    if not os.path.isdir(path):
        error_info = {
            "status": "error",
            "error_code": "DIRECTORY_NOT_FOUND",
            "message": f"The specified directory does not exist: {path}"
        }
        print(json.dumps(error_info, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    try:
        if sys.platform == "win32":
            # Windowsでは、パスを正規化しないとexplorerが正しく解釈できない場合がある
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
        error_info = {
            "status": "error",
            "error_code": "COMMAND_EXECUTION_ERROR",
            "message": "Failed to open the directory using the OS default file manager.",
            "details": {
                "platform": sys.platform,
                "path": path,
                "error": str(e)
            }
        }
        print(json.dumps(error_info, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_info = {
            "status": "error",
            "error_code": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred.",
            "details": {
                "platform": sys.platform,
                "path": path,
                "error": str(e)
            }
        }
        print(json.dumps(error_info, ensure_ascii=False), file=sys.stderr)
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
