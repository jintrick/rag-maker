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
def create_knowledge_base(kb_root: Path):
    """
    Sets up the basic directory structure and files for a new knowledge base.
    """
    try:
        # 1. Create the root directory
        kb_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Knowledge base root created at: {kb_root.resolve()}")

        # 2. Copy only the necessary command files (e.g., ask.toml) to make the KB self-contained.
        # Assumes this script is in <project_root>/tools/
        project_root = Path(__file__).resolve().parent.parent
        source_gemini_dir = project_root / ".gemini"
        dest_commands_dir = kb_root / ".gemini" / "commands"

        # Create the destination directory structure
        dest_commands_dir.mkdir(parents=True, exist_ok=True)

        # Selectively copy only the 'ask' command definition.
        source_ask_toml = source_gemini_dir / "commands" / "ask.toml"
        if source_ask_toml.is_file():
            shutil.copy2(source_ask_toml, dest_commands_dir / "ask.toml")
            logger.info(f"Copied ask.toml to {dest_commands_dir.resolve()}")


        # 3. Create the cache directory
        cache_dir = kb_root / "cache"
        cache_dir.mkdir(exist_ok=True)
        logger.info(f"Created cache directory at {cache_dir.resolve()}")

        # 4. Create a minimal discovery.json for the knowledge base.
        # This file will only contain the document catalog. Tool definitions
        # are centralized in the project's root discovery.json.
        dest_discovery_json_path = kb_root / "discovery.json"

        # Create a new discovery.json structure for the knowledge base.
        kb_discovery_data = {
            "documents": []
        }

        # Write the new discovery.json to the knowledge base directory.
        with open(dest_discovery_json_path, 'w', encoding='utf-8') as f:
            json.dump(kb_discovery_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Created minimal discovery.json for the knowledge base at {dest_discovery_json_path.resolve()}")

    except (IOError, OSError, FileNotFoundError) as e:
        eprint_error({
            "status": "error",
            "error_code": "FILE_OPERATION_ERROR",
            "message": f"An error occurred during file operations: {e}",
            "details": {"error_type": type(e).__name__, "error": str(e)}
        })
    except Exception as e:
        eprint_error({
            "status": "error",
            "error_code": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred.",
            "details": {"error_type": type(e).__name__, "error": str(e)}
        })


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
        # Errors from create_knowledge_base are already handled and will exit.
        # This catches errors from argument parsing or other unexpected issues.
        if not isinstance(e, SystemExit):
            eprint_error({
                "status": "error",
                "message": "An unexpected error occurred in main.",
                "details": str(e)
            })

if __name__ == "__main__":
    main()
