#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to register a new document entry into the root discovery.json.
This tool takes a title and summary as arguments and adds or updates
an entry in the RAGMaker's root discovery.json file.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

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
def update_root_discovery_file(root_discovery_path: Path, new_entry: dict):
    """
    Adds or updates an entry in the root discovery.json file.
    """
    try:
        if root_discovery_path.exists():
            with open(root_discovery_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"documents": [], "tools": [], "handles": {}}

        documents = data.get("documents", [])
        entry_path = new_entry["path"]

        found_index = -1
        for i, doc in enumerate(documents):
            if doc.get("path") == entry_path:
                found_index = i
                break

        if found_index != -1:
            documents[found_index].update(new_entry)
            message = "Entry updated successfully."
        else:
            documents.append(new_entry)
            message = "Entry added successfully."

        data["documents"] = documents

        with open(root_discovery_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"{message} in {root_discovery_path.resolve()}")
        return message

    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error processing root discovery file {root_discovery_path}: {e}")
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Register a document entry into the root discovery.json.")
    parser.add_argument("--path", required=True, help="The path to the document's cache directory.")
    parser.add_argument("--src-type", required=True, help="The source type (e.g., local, web, github).")
    parser.add_argument("--title", required=True, help="The title for the document collection.")
    parser.add_argument("--summary", required=True, help="The summary for the document collection.")
    parser.add_argument("--source-url", required=True, help="The original source URL or path for the document.")
    parser.add_argument("--kb-root", help="The root directory of the knowledge base. Defaults to the current directory.")


    try:
        args = parser.parse_args()

        if args.kb_root:
            root_discovery_file = Path(args.kb_root) / "discovery.json"
        else:
            root_discovery_file = Path("discovery.json")


        source_info = {
            "url": args.source_url,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

        # 1. Prepare the new entry for the root discovery file
        new_document_entry = {
            "path": args.path,
            "title": args.title,
            "summary": args.summary,
            "src_type": args.src_type,
            "source_info": source_info
        }

        # 2. Update the root discovery file
        message = update_root_discovery_file(root_discovery_file, new_document_entry)

        # 3. Print success output
        result = {
            "status": "success",
            "message": message,
            "entry": new_document_entry,
            "discovery_file": str(root_discovery_file.resolve())
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        eprint_error({
            "status": "error",
            "message": "An unexpected error occurred.",
            "details": str(e)
        })

if __name__ == "__main__":
    main()
