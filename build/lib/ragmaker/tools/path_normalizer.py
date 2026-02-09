#!/usr/bin/env python3
"""
A tool for normalizing file paths to be used in cache directory naming.

This script takes a file path (Windows or POSIX style) and converts it into a
standardized, safe format for use as a directory name.

Usage:
    python path_normalizer.py --path <path/to/normalize>

Args:
    --path (str): The file path to normalize.

Returns:
    (stdout): The normalized path string.
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse

def normalize_path_for_cache(path_str: str) -> str:
    """
    Normalizes a given absolute path for cache directory naming.

    This function implements the following logic:
    1. Replaces all backslashes ('\\') with forward slashes ('/').
    2. Removes the colon from a Windows drive letter (e.g., 'C:' -> 'C').
    3. Removes the leading slash from a POSIX path (e.g., '/home/user' -> 'home/user').
    4. Ensures the resulting path ends with a forward slash.

    Examples:
        - 'C:\\Users\\test\\' -> 'C/Users/test/'
        - 'C:\\Users\\test'  -> 'C/Users/test/'
        - '/home/user/docs/' -> 'home/user/docs/'
        - '/home/user/docs'  -> 'home/user/docs/'
    """
    if not path_str:
        return ""

    # 1. Normalize backslashes to forward slashes
    normalized = path_str.replace('\\', '/')

    # 2. Handle Windows drive letter
    if ':' in normalized:
        # This assumes the first colon is for the drive letter.
        normalized = normalized.replace(':', '', 1)

    # 3. Handle POSIX leading slash
    if normalized.startswith('/'):
        normalized = normalized[1:]

    # 4. Ensure trailing slash
    if not normalized.endswith('/'):
        normalized += '/'

    return normalized

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Normalize a file path for cache directory naming."
    )
    parser.add_argument(
        "--path",
        required=True,
        help="The file path to normalize."
    )
    args = parser.parse_args()

    try:
        normalized_path = normalize_path_for_cache(args.path)
        print(normalized_path, end='')
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()