#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_file.py - A tool to write content to a specified file.
"""

import argparse
import os
import sys
import json
from pathlib import Path
from typing import Any

try:
    from ragmaker.io_utils import (
        print_json_stdout,
        handle_io_error,
        handle_unexpected_error
    )
except ImportError:
    # Fallback for local execution
    def print_json_stdout(data: dict[str, Any]): print(json.dumps(data))
    def handle_io_error(exception: IOError): print(json.dumps({"status": "error", "message": f"I/O error: {exception}"})); sys.exit(1)
    def handle_unexpected_error(exception: Exception): print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"})); sys.exit(1)


def main():
    """
    Main function to write content to a file.
    """
    parser = argparse.ArgumentParser(description="Writes content to a specified file.")
    parser.add_argument("--path", required=True, help="The path to the file to be written.")
    parser.add_argument("--content", required=True, help="The content to write to the file.")
    args = parser.parse_args()

    file_path = Path(args.path)

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(args.content)

        output_data = {
            "status": "success",
            "path": str(file_path)
        }
        print_json_stdout(output_data)

    except IOError as e:
        handle_io_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
