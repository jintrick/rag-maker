#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to create a new, self-contained knowledge base.
"""

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
import importlib.resources

try:
    from ragmaker.io_utils import handle_io_error, handle_unexpected_error
except ImportError:
    # Fallback for local execution without installation
    def handle_io_error(exception: IOError):
        print(json.dumps({"status": "error", "message": f"I/O error: {exception}"}))
        sys.exit(1)
    def handle_unexpected_error(exception: Exception):
        print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"}))
        sys.exit(1)


# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# --- Core Logic ---
def create_knowledge_base(kb_root: Path):
    """
    Sets up the basic directory structure and files for a new knowledge base.
    """
    try:
        kb_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Knowledge base root created at: {kb_root.resolve()}")

        dest_commands_dir = kb_root / ".gemini" / "commands"
        dest_commands_dir.mkdir(parents=True, exist_ok=True)

        with importlib.resources.path("ragmaker.data", "ask.toml") as source_ask_toml:
            if source_ask_toml.is_file():
                shutil.copy2(source_ask_toml, dest_commands_dir / "ask.toml")
                logger.info(f"Copied ask.toml to {dest_commands_dir.resolve()}")

        cache_dir = kb_root / "cache"
        cache_dir.mkdir(exist_ok=True)
        logger.info(f"Created cache directory at {cache_dir.resolve()}")

    except (IOError, OSError, FileNotFoundError) as e:
        handle_io_error(e)
        raise
    except Exception as e:
        handle_unexpected_error(e)
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create a new knowledge base.")
    parser.add_argument("--kb-root", required=True, help="The root path for the new knowledge base.")

    try:
        args = parser.parse_args()
        kb_root_path = Path(args.kb_root)

        create_knowledge_base(kb_root_path)

        result = {
            "status": "success",
            "message": "Knowledge base created successfully.",
            "knowledge_base_root": str(kb_root_path.resolve())
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        if not isinstance(e, SystemExit):
            handle_unexpected_error(e)
            sys.exit(1)

if __name__ == "__main__":
    main()
