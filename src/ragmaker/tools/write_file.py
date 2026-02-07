#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_file.py - A tool to write content to a specified file.
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import os
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
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)


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