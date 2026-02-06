#!/usr/bin/env python3
"""
A tool for synchronizing files between two directories.

This tool uses shutil.copytree for reliable, cross-platform file copying.
It is designed for use by AI agents and provides robust error handling
and structured JSON output.

Usage:
    python file_sync.py --source-dir <path/to/source> --dest-dir <path/to/destination>

Args:
    --source-dir (str): The source directory path.
    --dest-dir (str): The destination directory path.

Returns:
    (stdout): On success, a JSON object summarizing the result.
              Example: {
                          "status": "success",
                          "source_dir": "/path/to/source",
                          "dest_dir": "/path/to/destination"
                       }
    (stderr): On error, a JSON object with an error code and details.
"""

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

try:
    from ragmaker.io_utils import (
        ArgumentParsingError,
        GracefulArgumentParser,
        eprint_error,
        handle_argument_parsing_error,
        handle_unexpected_error,
    )
except ImportError:
    # This is a fallback for when the script is run in an environment
    # where the ragmaker package is not installed.
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "The 'ragmaker' package is not installed or not in the Python path.",
        "remediation_suggestion": "Please install the package, e.g., via 'pip install .'"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Structured Error Handling (Tool-specific) ---
def handle_file_sync_error(exception: Exception):
    """Handles file synchronization errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "FILE_SYNC_ERROR",
        "message": "Failed to synchronize files.",
        "details": {
            "error_type": type(exception).__name__,
            "error": str(exception)
        }
    })


# --- Core Logic ---
def sync_files(source_dir: Path, dest_dir: Path):
    """
    Synchronizes files from a source to a destination directory using shutil.copytree.
    """
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    try:
        # Ensure destination exists and is empty for a clean sync
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        # dirs_exist_ok=True handles the case where the destination is created
        # by another process between the rmtree and copytree calls.
        shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)

        logger.info(f"File synchronization successful from {source_dir} to {dest_dir}")

    except (shutil.Error, OSError) as e:
        handle_file_sync_error(e)
        raise  # Re-raise to be caught by the main exception handler

# --- Main Execution ---
def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Synchronize files between two directories.")
    parser.add_argument("--source-dir", required=True, help="Source directory.")
    parser.add_argument("--dest-dir", required=True, help="Destination directory.")

    try:
        args = parser.parse_args()

        source_path = Path(args.source_dir)
        dest_path = Path(args.dest_dir)

        sync_files(source_path, dest_path)

        result = {
            "status": "success",
            "source_dir": str(source_path.resolve()),
            "dest_dir": str(dest_path.resolve())
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except Exception as e:
        # Catch other exceptions raised from sync_files
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
