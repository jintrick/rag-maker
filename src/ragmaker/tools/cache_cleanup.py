#!/usr/bin/env python3
"""
cache_cleanup.py - Clean up cache directories.

This tool removes all files and directories from a specified target directory,
except for 'catalog.json' and any Markdown ('.md') files. This is used
to clean up source files (like HTML or cloned git repos) after they have
been converted to Markdown, saving storage space.
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

try:
    from ragmaker.io_utils import handle_file_not_found_error, handle_unexpected_error
except ImportError:
    # Fallback for local execution without installation
    def handle_file_not_found_error(exception: FileNotFoundError):
        print(json.dumps({"status": "error", "message": f"File not found: {exception}"}))
        sys.exit(1)
    def handle_unexpected_error(exception: Exception):
        print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"}))
        sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Core Logic ---
def cleanup_directory(target_dir: Path) -> tuple[list[str], list[str]]:
    """
    Deletes files and directories in the target directory, with exceptions.
    """
    if not target_dir.is_dir():
        logger.error(f"Target directory not found: {target_dir}")
        raise FileNotFoundError(f"Target directory not found: {target_dir}")

    deleted_items = []
    kept_items = []

    items_to_delete = []
    for item_path in target_dir.glob('*'):
        if item_path.name == 'catalog.json' or item_path.suffix == '.md':
            kept_items.append(str(item_path))
            continue
        items_to_delete.append(item_path)

    for item_path in items_to_delete:
        try:
            if item_path.is_dir():
                shutil.rmtree(item_path)
                logger.info(f"Deleted directory: {item_path}")
            else:
                item_path.unlink()
                logger.info(f"Deleted file: {item_path}")
            deleted_items.append(str(item_path))
        except OSError as e:
            logger.error(f"Error deleting {item_path}: {e}")

    return deleted_items, kept_items

# --- Main Execution ---
def main():
    """Main entry point."""
    # Suppress logging to ensure pure JSON output on stderr
    logging.disable(sys.maxsize)

    parser = argparse.ArgumentParser(description="Clean up a cache directory, keeping only essential files.")
    parser.add_argument("--target-dir", required=True, help="The directory to clean up.")

    try:
        args = parser.parse_args()
        target_path = Path(args.target_dir)

        deleted, kept = cleanup_directory(target_path)

        result = {
            "status": "success",
            "target_directory": str(target_path.resolve()),
            "deleted_items": sorted(deleted),
            "kept_items": sorted(kept),
            "summary": f"Deleted {len(deleted)} items, kept {len(kept)} items."
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError as e:
        handle_file_not_found_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
