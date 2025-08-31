#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to register a new document entry into the root discovery.json.

This tool adds or updates a document entry in the `documents` list of the
RAGMaker's root `discovery.json` file. It ensures that the catalog of
available knowledge bases is kept up-to-date.

Usage:
    python entry_discovery.py --path <path> --title <title> --summary <summary> --src-type <type>

Args:
    --path (str): The path to the cache directory of the document.
    --title (str): The title of the document set.
    --summary (str): A brief summary of the document set.
    --src-type (str): The source type (e.g., 'local', 'web', 'github').

Returns:
    (stdout): On success, a JSON object summarizing the result.
              Example: {
                          "status": "success",
                          "message": "Entry added/updated successfully.",
                          "entry": { ... new entry ... }
                       }
    (stderr): On error, a JSON object with an error code and details.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)

# --- Custom Exception and ArgumentParser ---
class ArgumentParsingError(Exception):
    """Custom exception for argument parsing errors."""

class GracefulArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises a custom exception on error."""
    def error(self, message: str):
        raise ArgumentParsingError(message)

# --- Structured Error Handling ---
def eprint_error(error_obj: dict):
    """Prints a structured error object as JSON to stderr."""
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

def handle_argument_parsing_error(exception: Exception):
    """Handles argument parsing errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "Failed to parse command-line arguments.",
        "details": {"original_error": str(exception)}
    })

def handle_file_io_error(exception: IOError, filepath: Path):
    """Handles file I/O errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "FILE_IO_ERROR",
        "message": f"Failed to read from or write to '{filepath}'.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })

def handle_unexpected_error(exception: Exception):
    """Handles unexpected errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred during processing.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })

# --- Core Logic ---
def update_discovery_file(discovery_path: Path, new_entry: dict):
    """
    Adds or updates an entry in the discovery.json file.
    """
    try:
        if discovery_path.exists():
            with open(discovery_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"documents": [], "tools": [], "handles": {}}

        documents = data.get("documents", [])
        entry_path = new_entry["path"]

        # Check if an entry with the same path already exists
        found_index = -1
        for i, doc in enumerate(documents):
            if doc.get("path") == entry_path:
                found_index = i
                break

        if found_index != -1:
            # Update existing entry
            documents[found_index] = new_entry
            message = "Entry updated successfully."
        else:
            # Add new entry
            documents.append(new_entry)
            message = "Entry added successfully."

        data["documents"] = documents

        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(message)
        return message

    except (IOError, json.JSONDecodeError) as e:
        handle_file_io_error(e, discovery_path)
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Register a document entry in discovery.json.")
    parser.add_argument("--path", required=True, help="The path to the document's cache directory.")
    parser.add_argument("--title", required=True, help="The title of the document set.")
    parser.add_argument("--summary", required=True, help="A summary of the document set.")
    parser.add_argument("--src-type", required=True, help="The source type (e.g., local, web, github).")

    try:
        args = parser.parse_args()

        discovery_file_path = Path("discovery.json")

        new_document_entry = {
            "path": args.path,
            "title": args.title,
            "summary": args.summary,
            "src_type": args.src_type
        }

        message = update_discovery_file(discovery_file_path, new_document_entry)

        result = {
            "status": "success",
            "message": message,
            "entry": new_document_entry
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
