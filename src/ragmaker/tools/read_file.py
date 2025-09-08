#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_file.py - A tool to read the content of one or more specified files.
"""

import argparse
import os
import json
import sys
from ragmaker.io_utils import print_json_stdout, eprint_error

def main():
    """
    Main function to read one or more files and print their contents as a single JSON object.
    """
    parser = argparse.ArgumentParser(description="Reads one or more files and outputs their contents as a single JSON object.")
    parser.add_argument("--path", required=True, action='append', help="The path to a file to be read. Can be specified multiple times.")
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
        error_data = {
            "status": "error",
            "message": str(e)
        }
        eprint_error(error_data)
        sys.exit(1)
    except Exception as e:
        error_data = {
            "status": "error",
            "message": f"An unexpected error occurred: {e}"
        }
        eprint_error(error_data)
        sys.exit(1)

if __name__ == "__main__":
    main()
