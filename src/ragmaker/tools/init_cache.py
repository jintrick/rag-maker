#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to initialize the temporary cache directory for a workflow run.
"""
import os
import shutil
import sys
import json
import logging
from pathlib import Path

try:
    from ragmaker.utils import cleanup_dir_contents
except ImportError:
    # Fallback implementation
    def cleanup_dir_contents(path: Path):
        """ディレクトリ自体は残し、その中身のみを再帰的に削除する。"""
        if not path.exists(): return
        for item in path.iterdir():
            if item.is_dir(): shutil.rmtree(item)
            else: item.unlink()

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# --- Core Logic ---
def init_cache():
    """
    Initializes the .tmp/cache directory.

    This ensures the .tmp/cache directory exists and is empty.
    """
    tmp_dir = '.tmp'
    cache_dir = os.path.join(tmp_dir, 'cache')

    try:
        # Step 1: Create the new .tmp/cache directory.
        # We removed the destructive operation (shutil.rmtree) to prevent accidental data loss.
        os.makedirs(cache_dir, exist_ok=True)

        # Step 2: Clean up the contents of the cache directory.
        cleanup_dir_contents(Path(cache_dir))

        logger.info(f"Successfully initialized cache directory: {cache_dir}")

        return f"Cache initialized at {cache_dir}"

    except OSError as e:
        error_message = f"Failed to initialize cache directory: {e}"
        logger.error(error_message)
        print(json.dumps({"status": "error", "message": error_message}))
        sys.exit(1)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.error(error_message)
        print(json.dumps({"status": "error", "message": error_message}))
        sys.exit(1)

# --- Main Execution ---
def main():
    """Main entry point."""
    # This tool has no arguments.
    if len(sys.argv) > 1:
        logger.warning(f"This script '{os.path.basename(__file__)}' does not accept any arguments. Ignoring provided arguments: {sys.argv[1:]}")

    try:
        message = init_cache()
        result = {
            "status": "success",
            "message": message,
            "cache_directory": os.path.abspath('.tmp/cache')
        }
        print(json.dumps(result, indent=2))
    except SystemExit:
        # Prevent catching sys.exit() calls
        raise
    except Exception:
        # The specific error handling is done in init_cache,
        # but this is a fallback.
        # The error message would have already been printed to stderr.
        sys.exit(1)

if __name__ == "__main__":
    main()
