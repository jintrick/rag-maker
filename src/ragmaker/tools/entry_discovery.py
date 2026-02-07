#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to create an initial catalog.json file for the workflow.
This file starts with metadata and an 'unknowns' entry containing the initial source URI.
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import json
from pathlib import Path
from typing import Any

# --- Dependency Check ---
try:
    from ragmaker.io_utils import (
        handle_unexpected_error,
        handle_io_error,
        print_json_stdout,
        eprint_error
    )
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)


# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Core Logic ---
def create_initial_catalog(catalog_path: Path, uri: str, title: str = None, summary: str = None, src_type: str = None) -> str:
    """
    Creates a new catalog.json file with metadata and an 'unknowns' entry.
    If the file exists, it updates the metadata.
    """
    # Ensure the parent directory exists.
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if catalog_path.exists():
        with open(catalog_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                pass # Start fresh if corrupt

    # Update or set metadata
    if title:
        data['title'] = title
    if summary:
        data['summary'] = summary
    if src_type:
        data['src_type'] = src_type

    # Ensure source_url matches the initial URI if not already present or if we are initializing
    data['source_url'] = uri

    # Ensure 'unknowns' exists and verify URI
    if 'unknowns' not in data:
        data['unknowns'] = [{"uri": uri}]

    # Note: We don't force-add the URI to unknowns if it's already a document,
    # but for initialization, it's safe to ensure it's tracked if the file was empty.

    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    message = f"Successfully updated catalog file at {catalog_path.resolve()}"
    logger.info(message)
    return message

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create or update catalog.json with metadata and source URI.")
    # Renamed --discovery-path to --kb-root to align with master catalog (discovery.json) and new naming convention.
    parser.add_argument("--kb-root", required=True, help="The root path of the knowledge base where catalog.json will be created.")
    parser.add_argument("--uri", required=False, help="The initial source URI/URL.") # Made optional for updates, but logic handles it.
    parser.add_argument("--source-url", required=False, help="Alias for --uri.")
    
    # New metadata arguments
    parser.add_argument("--title", required=False, help="The title of the knowledge base.")
    parser.add_argument("--summary", required=False, help="A summary of the knowledge base.")
    parser.add_argument("--src-type", required=False, help="The type of the source (e.g., github, web, local).")

    try:
        args = parser.parse_args()
        catalog_path = Path(args.kb_root) / "catalog.json"
        
        # Handle uri vs source-url alias
        uri = args.uri or args.source_url
        if not uri and not catalog_path.exists():
             # If creating new, we need a URI
             eprint_error({"status": "error", "message": "Either --uri or --source-url is required when creating a new catalog file."})
             sys.exit(1)
        
        # If updating and no URI provided, try to read it from file, or just update metadata
        # For simplicity in this tool's scope, we pass the provided URI or None.
        # But create_initial_catalog logic expects a URI for the 'unknowns' if new.
        # If existing, it updates source_url.
        
        message = create_initial_catalog(
            catalog_path,
            uri, 
            title=args.title, 
            summary=args.summary, 
            src_type=args.src_type
        )

        result = {
            "status": "success",
            "message": message,
            "catalog_file": str(catalog_path.resolve())
        }
        print_json_stdout(result)

    except IOError as e:
        handle_io_error(e)
        sys.exit(1)
    except Exception as e:
        if not isinstance(e, SystemExit):
            handle_unexpected_error(e)
            sys.exit(1)

if __name__ == "__main__":
    main()