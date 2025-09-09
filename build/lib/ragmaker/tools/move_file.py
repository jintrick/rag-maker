#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
move_file.py - A tool to move a file from a source to a destination.
"""

import argparse
import os
import sys
import shutil
import json
from pathlib import Path
from typing import Any

try:
    from ragmaker.io_utils import (
        print_json_stdout,
        handle_file_not_found_error,
        handle_unexpected_error
    )
except ImportError:
    # Fallback for local execution
    def print_json_stdout(data: dict[str, Any]): print(json.dumps(data))
    def handle_file_not_found_error(exception: FileNotFoundError): print(json.dumps({"status": "error", "message": f"File not found: {exception}"})); sys.exit(1)
    def handle_unexpected_error(exception: Exception): print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"})); sys.exit(1)


def main():
    """
    Main function to move a file.
    """
    parser = argparse.ArgumentParser(description="Moves a file from a source to a destination.")
    parser.add_argument("--source", required=True, help="The source path of the file to move.")
    parser.add_argument("--destination", required=True, help="The destination path for the file.")
    args = parser.parse_args()

    source_path = Path(args.source)
    dest_path = Path(args.destination)

    try:
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source_path), str(dest_path))

        output_data = {
            "status": "success",
            "source": str(source_path),
            "destination": str(dest_path)
        }
        print_json_stdout(output_data)

    except FileNotFoundError as e:
        handle_file_not_found_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
