#!/usr/bin/env python3
"""
cache_cleanup.py - Clean up cache directories.

This tool removes all files and directories from a specified target directory,
except for 'discovery.json' and any Markdown ('.md') files. This is used
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

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# --- Structured Error Handling ---
def eprint_error(error_obj: dict):
    """Prints a structured error object as JSON to stderr."""
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- Core Logic ---
def cleanup_directory(target_dir: Path):
    """
    Deletes files and directories in the target directory, with exceptions.
    """
    if not target_dir.is_dir():
        logger.error(f"Target directory not found: {target_dir}")
        raise FileNotFoundError(f"Target directory not found: {target_dir}")

    deleted_items = []
    kept_items = []

    # Use a two-pass approach. First, identify what to delete.
    items_to_delete = []
    for item_path in target_dir.glob('*'):
        # Keep discovery.json and .md files
        if item_path.name == 'discovery.json' or item_path.suffix == '.md':
            kept_items.append(str(item_path))
            continue

        items_to_delete.append(item_path)

    # Second pass: delete the identified items.
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
            # For now, we'll log and continue. We could re-raise if needed.

    return deleted_items, kept_items

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean up a cache directory, keeping only essential files.")
    parser.add_argument("--target-dir", required=True, help="The directory to clean up.")

    try:
        args = parser.parse_args()
        target_path = Path(args.target_dir)

        deleted, kept = cleanup_directory(target_path)

        result = {
            "status": "success",
            "target_directory": str(target_path.resolve()),
            "deleted_items": sorted(deleted), # Sort for deterministic output
            "kept_items": sorted(kept),       # Sort for deterministic output
            "summary": f"Deleted {len(deleted)} items, kept {len(kept)} items."
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except FileNotFoundError as e:
        eprint_error({
            "status": "error",
            "error_code": "DIRECTORY_NOT_FOUND",
            "message": str(e)
        })
    except Exception as e:
        eprint_error({
            "status": "error",
            "error_code": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred during cleanup.",
            "details": str(e)
        })

if __name__ == "__main__":
    main()
