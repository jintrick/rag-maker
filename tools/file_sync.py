#!/usr/bin/env python3
"""
A tool for synchronizing files between two directories.

This tool uses OS-native commands for high-speed file copying.
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
import platform
import subprocess
import sys
from pathlib import Path

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)

# --- Custom Exception and ArgumentParser ---
class ArgumentParsingError(Exception):
    """Custom exception for argument parsing errors."""

class GracefulArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises a custom exception on error."""
    def error(self, message: str):
        raise ArgumentParsingError(message)

# --- Structured Error Handling ---
def eprint_error(error_obj: dict):
    """Prints a structured error object as JSON to stderr."""
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

def handle_argument_parsing_error(exception: Exception):
    """Handles argument parsing errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "Failed to parse command-line arguments.",
        "details": {"original_error": str(exception)}
    })

def handle_file_sync_error(cmd: list, exception: subprocess.CalledProcessError):
    """Handles file synchronization errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "FILE_SYNC_ERROR",
        "message": "Failed to synchronize files.",
        "details": {
            "command": " ".join(cmd),
            "return_code": exception.returncode,
            "stdout": exception.stdout,
            "stderr": exception.stderr
        }
    })

def handle_unexpected_error(exception: Exception):
    """Handles unexpected errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred during processing.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })

# --- Core Logic ---
def sync_files(source_dir: Path, dest_dir: Path):
    """
    Synchronizes files from a source to a destination directory.

    Uses 'rsync' on Linux/macOS and 'robocopy' on Windows.
    """
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    system = platform.system()
    if system == "Windows":
        # Robocopy: /E (copy subdirectories, including empty ones), /MIR (mirror a directory tree)
        cmd = ["robocopy", str(source_dir), str(dest_dir), "/E", "/MIR"]
    else:
        # rsync: -a (archive mode), -v (verbose), --delete (delete extraneous files from dest dirs)
        cmd = ["rsync", "-av", "--delete", f"{source_dir}/", str(dest_dir)]

    try:
        # We don't use check=True because robocopy has non-zero exit codes for success
        process = subprocess.run(
            cmd,
            check=False,  # Important for robocopy
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        # Robocopy returns non-zero codes even on success.
        # A value of < 8 indicates success (files copied, extra files, etc.)
        if system == "Windows" and process.returncode >= 8:
             raise subprocess.CalledProcessError(
                process.returncode, cmd, output=process.stdout, stderr=process.stderr
            )
        # For rsync, 0 is the only success code.
        elif system != "Windows" and process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, cmd, output=process.stdout, stderr=process.stderr
            )

        logger.info("File synchronization successful from %s to %s", source_dir, dest_dir)
        logger.debug("Sync command output:\n%s", process.stdout)

    except subprocess.CalledProcessError as e:
        handle_file_sync_error(cmd, e)
        raise  # Re-raise to be caught by the main exception handler
    except FileNotFoundError as e:
        # This can happen if rsync/robocopy is not installed
        handle_unexpected_error(e)
        raise

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
