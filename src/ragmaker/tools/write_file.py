#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_file.py - A tool to write content to a specified file.
"""

import argparse
import os
import sys
from pathlib import Path
from ragmaker.io_utils import print_json_stdout, eprint_error

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
        # Ensure the parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(args.content)

        output_data = {
            "status": "success",
            "path": str(file_path)
        }
        print_json_stdout(output_data)

    except IOError as e:
        error_data = {
            "status": "error",
            "path": str(file_path),
            "message": f"An I/O error occurred: {e}"
        }
        eprint_error(error_data)
        sys.exit(1)
    except Exception as e:
        error_data = {
            "status": "error",
            "path": str(file_path),
            "message": f"An unexpected error occurred: {e}"
        }
        eprint_error(error_data)
        sys.exit(1)

if __name__ == "__main__":
    main()
