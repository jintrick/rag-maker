# -*- coding: utf-8 -*-
"""
read_file.py - A tool to read the content of a specified file.
"""

import argparse
import os
import json
import sys
from ragmaker.io_utils import print_json_stdout, eprint_json_stderr

def main():
    """
    Main function to read a file and print its content as a JSON object.
    """
    parser = argparse.ArgumentParser(description="Reads a file and outputs its content as JSON.")
    parser.add_argument("--path", required=True, help="The path to the file to be read.")
    args = parser.parse_args()

    file_path = args.path

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file was not found at the specified path: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        output_data = {
            "status": "success",
            "path": file_path,
            "content": content
        }
        print_json_stdout(output_data)

    except FileNotFoundError as e:
        error_data = {
            "status": "error",
            "path": file_path,
            "message": str(e)
        }
        eprint_json_stderr(error_data)
        sys.exit(1)
    except Exception as e:
        error_data = {
            "status": "error",
            "path": file_path,
            "message": f"An unexpected error occurred: {e}"
        }
        eprint_json_stderr(error_data)
        sys.exit(1)

if __name__ == "__main__":
    main()
