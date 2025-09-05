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

        # 2. Copy only the necessary command files (ask.toml) to make the KB self-contained.
        # Assumes this script is in <project_root>/tools/
        project_root = Path(__file__).resolve().parent.parent
        
        source_ask_toml = project_root / ".gemini" / "commands" / "ask.toml"
        dest_commands_dir = kb_root / ".gemini" / "commands"

        if not source_ask_toml.is_file():
            raise FileNotFoundError(f"Source command file not found at {source_ask_toml}")

        # Create the destination directory structure
        dest_commands_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_ask_toml, dest_commands_dir / "ask.toml")
        logger.info(f"Copied ask.toml to {dest_commands_dir.resolve()}")

        # 3. Create the cache directory
        cache_dir = kb_root / "cache"
        cache_dir.mkdir(exist_ok=True)
        logger.info(f"Created cache directory at {cache_dir.resolve()}")

        # 4. Copy the root discovery.json to serve as a template for the new knowledge base.
        source_discovery_json = project_root / "discovery.json"
        dest_discovery_json = kb_root / "discovery.json"

        if not source_discovery_json.is_file():
            raise FileNotFoundError(f"Source discovery.json not found at {source_discovery_json}")

        shutil.copy2(source_discovery_json, dest_discovery_json)
        logger.info(f"Copied discovery.json template to {dest_discovery_json.resolve()}")

        # After copying, clear the 'documents' list to ensure the new KB is empty.
        with open(dest_discovery_json, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data['documents'] = []
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.truncate()
        logger.info(f"Cleared 'documents' list in new discovery.json")

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
