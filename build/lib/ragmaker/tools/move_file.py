#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
move_file.py - A tool to move a file from a source to a destination.
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import os
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
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)


def main():
    """
    Main function to move a file or directory.
    """
    parser = argparse.ArgumentParser(description="Moves a file or directory from a source to a destination.")
    parser.add_argument("--source", required=True, help="The source path to move.")
    parser.add_argument("--destination", required=True, help="The destination path.")
    parser.add_argument("--merge", action="store_true", help="If destination is an existing directory, merge content.")
    args = parser.parse_args()

    source_path = Path(args.source)
    dest_path = Path(args.destination)

    try:
        if not source_path.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")

        # If destination is a directory and exists
        if dest_path.is_dir() and dest_path.exists():
            # Check if it's empty
            is_empty = not any(dest_path.iterdir())
            if is_empty or args.merge:
                # If empty or merge requested, move contents of source into destination
                if source_path.is_dir():
                    for item in source_path.iterdir():
                        shutil.move(str(item), str(dest_path / item.name))
                    # Optionally remove the now empty source directory
                    source_path.rmdir()
                else:
                    shutil.move(str(source_path), str(dest_path / source_path.name))
            else:
                # Original behavior: shutil.move will move source into destination as a sub-item
                shutil.move(str(source_path), str(dest_path))
        else:
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
