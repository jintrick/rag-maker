#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to register a new document entry into the root discovery.json.

This tool reads the metadata from a discovery.json file within a specified
cache directory, synthesizes a title and summary, and then adds or updates
an entry in the RAGMaker's root discovery.json file.
"""

import argparse
import json
import logging
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
def get_metadata_from_cache(cache_discovery_path: Path) -> dict | None:
    """
    Reads the discovery.json from the cache path to extract metadata.

    It uses the title and summary of the first document entry as the
    overall title and summary for the collection.
    """
    try:
        if not cache_discovery_path.is_file():
            logger.error(f"Cache discovery file not found at: {cache_discovery_path}")
            return None

        with open(cache_discovery_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = data.get("documents")
        if not documents:
            logger.error(f"No 'documents' array found in {cache_discovery_path}")
            return None

        first_doc = documents[0]
        title = first_doc.get("title")
        summary = first_doc.get("summary")

        if not title or not summary:
            logger.error(f"First document in {cache_discovery_path} is missing 'title' or 'summary'")
            return None

        return {"title": title, "summary": summary}

    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read or parse {cache_discovery_path}: {e}")
        return None


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
        entry_src_type = new_entry["src_type"]

        found_index = -1
        for i, doc in enumerate(documents):
            if doc.get("path") == entry_path and doc.get("src_type") == entry_src_type:
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

        logger.info(message)
        return message

    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error processing root discovery file {root_discovery_path}: {e}")
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Register a document entry by reading metadata from its cache.")
    parser.add_argument("--path", required=True, help="The path to the document's cache directory.")
    parser.add_argument("--src-type", required=True, help="The source type (e.g., local, web, github).")

    try:
        args = parser.parse_args()

        cache_path = Path(args.path)
        cache_discovery_file = cache_path / "discovery.json"
        root_discovery_file = Path("discovery.json")

        # 1. Get metadata from the cache's discovery file
        metadata = get_metadata_from_cache(cache_discovery_file)
        if not metadata:
            raise ValueError("Could not retrieve valid metadata from cache.")

        # 2. Prepare the new entry for the root discovery file
        new_document_entry = {
            "path": args.path,
            "title": metadata["title"],
            "summary": metadata["summary"],
            "src_type": args.src_type
        }

        # 3. Update the root discovery file
        message = update_root_discovery_file(root_discovery_file, new_document_entry)

        # 4. Print success output
        result = {
            "status": "success",
            "message": message,
            "entry": new_document_entry
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
