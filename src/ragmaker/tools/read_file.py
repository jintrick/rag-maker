#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_file.py - A tool to read the content of one or more specified files.
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import os
import json
from typing import Any

try:
    from ragmaker.io_utils import (
        print_json_stdout,
        handle_file_not_found_error,
        handle_unexpected_error
    )
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)


def main():
    """
    Main function to read one or more files and print their contents as a single JSON object.
    """
    parser = argparse.ArgumentParser(description="Reads one or more files and outputs their contents as a single JSON object.")
    parser.add_argument("--path", required=True, nargs='+', help="The path to a file to be read. Can be specified multiple times.")
    args = parser.parse_args()

    file_paths = args.path
    contents = []

    try:
        for file_path in file_paths:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file was not found at the specified path: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            contents.append({
                "path": file_path,
                "content": content
            })

        output_data = {
            "status": "success",
            "contents": contents
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