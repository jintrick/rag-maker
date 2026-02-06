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
    from ragmaker.io_utils import handle_unexpected_error, handle_io_error, handle_value_error
except ImportError:
    # Fallback for local execution
    def handle_unexpected_error(exception: Exception): print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"})); sys.exit(1)
    def handle_io_error(exception: IOError): print(json.dumps({"status": "error", "message": f"I/O error: {exception}"})); sys.exit(1)
    def handle_value_error(exception: ValueError): print(json.dumps({"status": "error", "message": f"Value error: {exception}"})); sys.exit(1)


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
            data = {"documents": []}

        data["header"] = header_data

        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        message = f"Successfully updated discovery header at {discovery_path.resolve()}"
        logger.info(message)
        return message

    except IOError as e:
        handle_io_error(e)
        raise
    except json.JSONDecodeError as e:
        handle_value_error(e)
        raise
    except Exception as e:
        handle_unexpected_error(e)
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

        header_data: dict[str, Any] = {
            "title": args.title,
            "summary": args.summary,
            "src_type": args.src_type,
            "source_url": args.source_url,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

        message = update_discovery_header(discovery_file_path, header_data)

        result = {
            "status": "success",
            "message": message,
            "header": header_data,
            "discovery_file": str(discovery_file_path.resolve())
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        if not isinstance(e, SystemExit):
            handle_unexpected_error(e)
            sys.exit(1)

if __name__ == "__main__":
    main()
