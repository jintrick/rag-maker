#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enrich_discovery.py - A tool to batch update catalog.json with enriched data.
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

try:
    from ragmaker.io_utils import (
        print_json_stdout,
        handle_file_not_found_error,
        handle_value_error,
        handle_unexpected_error
    )
    from ragmaker.utils import LockedJsonWriter
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

def main():
    """
    Main function to batch update a catalog.json file.
    """
    parser = argparse.ArgumentParser(description="Batch updates a catalog.json file with titles and summaries.")
    parser.add_argument("--catalog-path", required=True, help="Full path to the catalog.json file to be updated.")
    parser.add_argument("--updates", required=True, help="A JSON string or path to a JSON file containing an array of update objects.")
    args = parser.parse_args()

    catalog_path = args.catalog_path

    try:
        # Handle --updates as a file path or a JSON string
        updates_raw = args.updates
        if os.path.exists(updates_raw):
            try:
                with open(updates_raw, 'r', encoding='utf-8') as f:
                    updates = json.load(f)
            except Exception as e:
                raise ValueError(f"Failed to read updates from file {updates_raw}: {e}")
        else:
            try:
                updates = json.loads(updates_raw)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for --updates argument, and no such file found.")

        if not isinstance(updates, list):
            raise ValueError("--updates must be a JSON array of objects.")

        updated_paths = []
        added_paths = []

        with LockedJsonWriter(catalog_path) as catalog_data:
            if 'documents' not in catalog_data:
                catalog_data['documents'] = []

            documents = catalog_data['documents']
            documents_dict = {doc.get('path'): doc for doc in documents}

            for update in updates:
                path = update.get('path')
                if not path:
                    continue

                if path in documents_dict:
                    # Update existing
                    doc_to_update = documents_dict[path]
                    if 'title' in update: doc_to_update['title'] = update['title']
                    if 'summary' in update: doc_to_update['summary'] = update['summary']
                    if 'url' in update: doc_to_update['url'] = update['url']
                    updated_paths.append(path)
                else:
                    # Add new document
                    new_doc = {
                        "path": path,
                        "url": update.get('url', ''),
                        "title": update.get('title', ''),
                        "summary": update.get('summary', '')
                    }
                    documents.append(new_doc)
                    documents_dict[path] = new_doc # Keep dict synced just in case duplicates in updates
                    added_paths.append(path)

            if 'metadata' not in catalog_data:
                catalog_data['metadata'] = {}
            catalog_data['metadata']['updated_at'] = datetime.now(timezone.utc).isoformat()

        output_data = {
            "status": "success",
            "message": f"Successfully processed documents in {catalog_path}.",
            "updated_paths": updated_paths,
            "added_paths": added_paths
        }
        print_json_stdout(output_data)

    except FileNotFoundError as e:
        handle_file_not_found_error(e)
        sys.exit(1)
    except ValueError as e:
        handle_value_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
