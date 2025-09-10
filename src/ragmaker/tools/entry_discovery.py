#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to create an initial discovery.json file for the workflow.
This file starts with an 'unknowns' entry containing the initial source URI.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

try:
    # This will work when the package is installed.
    from ragmaker.io_utils import handle_unexpected_error, handle_io_error
except ImportError:
    # Fallback for local execution and testing.
    def handle_unexpected_error(exception: Exception):
        """Prints a JSON error message for unexpected exceptions."""
        print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"}))
        sys.exit(1)

    def handle_io_error(exception: IOError):
        """Prints a JSON error message for IO errors."""
        print(json.dumps({"status": "error", "message": f"I/O error: {exception}"}))
        sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# --- Core Logic ---
def create_initial_discovery(discovery_path: Path, uri: str) -> str:
    """
    Creates a new discovery.json file with an 'unknowns' entry.
    """
    try:
        # Ensure the parent directory exists.
        discovery_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "unknowns": [
                {"uri": uri}
            ]
        }

        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        message = f"Successfully created initial discovery file at {discovery_path.resolve()}"
        logger.info(message)
        return message

    except IOError as e:
        handle_io_error(e)
        raise  # Re-raise after handling, so the main block knows it failed.
    except Exception as e:
        handle_unexpected_error(e)
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create an initial discovery.json with a source URI.")
    parser.add_argument("--discovery-path", required=True, help="The full path where the discovery.json file will be created.")
    parser.add_argument("--uri", required=True, help="The initial source URI to be processed.")

    try:
        args = parser.parse_args()
        discovery_file_path = Path(args.discovery_path)

        message = create_initial_discovery(discovery_file_path, args.uri)

        result = {
            "status": "success",
            "message": message,
            "discovery_file": str(discovery_file_path.resolve())
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        # Error handling is done in the core logic function,
        # which will print a JSON error and exit.
        # This is a fallback.
        if not isinstance(e, SystemExit):
            handle_unexpected_error(e)
            sys.exit(1)

if __name__ == "__main__":
    main()
