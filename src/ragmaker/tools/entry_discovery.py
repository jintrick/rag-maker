#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A tool to create an initial discovery.json file for the workflow.
This file starts with metadata and an 'unknowns' entry containing the initial source URI.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

try:
    # This will work when the package is installed.
    from ragmaker.io_utils import handle_unexpected_error, handle_io_error
except ImportError:
    # Fallback for local execution and testing.
    def handle_unexpected_error(exception: Exception):
        """Prints a JSON error message for unexpected exceptions."""
        print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"}))
        sys.exit(1)

    def handle_io_error(exception: IOError):
        """Prints a JSON error message for IO errors."""
        print(json.dumps({"status": "error", "message": f"I/O error: {exception}"}))
        sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# --- Core Logic ---
def create_initial_discovery(discovery_path: Path, uri: str, title: str = None, summary: str = None, src_type: str = None) -> str:
    """
    Creates a new discovery.json file with metadata and an 'unknowns' entry.
    If the file exists, it updates the metadata.
    """
    try:
        # Ensure the parent directory exists.
        discovery_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if discovery_path.exists():
             with open(discovery_path, 'r', encoding='utf-8') as f:
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

        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        message = f"Successfully updated discovery file at {discovery_path.resolve()}"
        logger.info(message)
        return message

    except IOError as e:
        handle_io_error(e)
        raise  # Re-raise after handling, so the main block knows it failed.
    except Exception as e:
        handle_unexpected_error(e)
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create or update discovery.json with metadata and source URI.")
    parser.add_argument("--discovery-path", required=True, help="The full path where the discovery.json file will be created.")
    parser.add_argument("--uri", required=False, help="The initial source URI/URL.") # Made optional for updates, but logic handles it.
    parser.add_argument("--source-url", required=False, help="Alias for --uri.")
    
    # New metadata arguments
    parser.add_argument("--title", required=False, help="The title of the knowledge base.")
    parser.add_argument("--summary", required=False, help="A summary of the knowledge base.")
    parser.add_argument("--src-type", required=False, help="The type of the source (e.g., github, web, local).")

    try:
        args = parser.parse_args()
        discovery_file_path = Path(args.discovery_path)
        
        # Handle uri vs source-url alias
        uri = args.uri or args.source_url
        if not uri and not discovery_file_path.exists():
             # If creating new, we need a URI
             print(json.dumps({"status": "error", "message": "Either --uri or --source-url is required when creating a new discovery file."}))
             sys.exit(1)
        
        # If updating and no URI provided, try to read it from file, or just update metadata
        # For simplicity in this tool's scope, we pass the provided URI or None.
        # But create_initial_discovery logic expects a URI for the 'unknowns' if new. 
        # If existing, it updates source_url.
        
        message = create_initial_discovery(
            discovery_file_path, 
            uri, 
            title=args.title, 
            summary=args.summary, 
            src_type=args.src_type
        )

        result = {
            "status": "success",
            "message": message,
            "discovery_file": str(discovery_file_path.resolve())
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        if not isinstance(e, SystemExit):
            handle_unexpected_error(e)
            sys.exit(1)

if __name__ == "__main__":
    main()