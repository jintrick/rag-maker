#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to create or update the header metadata in the discovery.json
file located in the knowledge base's cache directory.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

try:
    from ragmaker.io_utils import eprint_error
except ImportError:
    # Fallback if ragmaker is not in the path
    def eprint_error(data: dict[str, Any]):
        """Prints a structured error object as JSON to stderr."""
        print(json.dumps(data, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# --- Core Logic ---
def update_discovery_header(discovery_path: Path, header_data: dict[str, Any]) -> str:
    """
    Creates or updates the discovery.json file with new header metadata.
    """
    try:
        discovery_path.parent.mkdir(parents=True, exist_ok=True)

        if discovery_path.exists():
            with open(discovery_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"documents": []} # Initialize with documents key

        # Update the header
        data["header"] = header_data

        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        message = f"Successfully updated discovery header at {discovery_path.resolve()}"
        logger.info(message)
        return message

    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error processing discovery file {discovery_path}: {e}")
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create or update the header in cache/discovery.json.")
    parser.add_argument("--kb-root", required=True, help="The root path for the knowledge base.")
    parser.add_argument("--title", required=True, help="The title for the knowledge base.")
    parser.add_argument("--summary", required=True, help="The summary for the knowledge base.")
    parser.add_argument("--source-url", required=True, help="The original source URL or path for the knowledge base.")
    parser.add_argument("--src-type", required=True, help="The source type (e.g., local, web, github).")

    try:
        args = parser.parse_args()

        kb_root_path = Path(args.kb_root)
        discovery_file_path = kb_root_path / "cache" / "discovery.json"

        # 1. Prepare the header data
        header_data: dict[str, Any] = {
            "title": args.title,
            "summary": args.summary,
            "src_type": args.src_type,
            "source_url": args.source_url,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

        # 2. Update the discovery file's header
        message = update_discovery_header(discovery_file_path, header_data)

        # 3. Print success output
        result = {
            "status": "success",
            "message": message,
            "header": header_data,
            "discovery_file": str(discovery_file_path.resolve())
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        if not isinstance(e, SystemExit):
            eprint_error({
                "status": "error",
                "message": "An unexpected error occurred in main.",
                "details": str(e)
            })

if __name__ == "__main__":
    main()
