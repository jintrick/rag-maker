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

        # 2. Copy the .gemini directory
        # Assumes this script is in <project_root>/tools/
        project_root = Path(__file__).resolve().parent.parent
        source_gemini_dir = project_root / ".gemini"
        dest_gemini_dir = kb_root / ".gemini"

        if not source_gemini_dir.is_dir():
            raise FileNotFoundError(f"Source .gemini directory not found at {source_gemini_dir}")

        shutil.copytree(source_gemini_dir, dest_gemini_dir, dirs_exist_ok=True)
        logger.info(f"Copied .gemini directory to {dest_gemini_dir.resolve()}")

        # 3. Create the cache directory
        cache_dir = kb_root / "cache"
        cache_dir.mkdir(exist_ok=True)
        logger.info(f"Created cache directory at {cache_dir.resolve()}")

        # 4. Create the initial discovery.json
        discovery_path = kb_root / "discovery.json"
        initial_discovery_content = {
            "documents": [],
            "tools": [],
            "handles": {}
        }
        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(initial_discovery_content, f, ensure_ascii=False, indent=2)
        logger.info(f"Created initial discovery.json at {discovery_path.resolve()}")

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
