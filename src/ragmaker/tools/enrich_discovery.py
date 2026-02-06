# -*- coding: utf-8 -*-
"""
enrich_discovery.py - A tool to batch update catalog.json with enriched data.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Any

try:
    from ragmaker.io_utils import (
        print_json_stdout,
        handle_file_not_found_error,
        handle_value_error,
        handle_unexpected_error
    )
except ImportError:
    # Fallback for local execution
    def print_json_stdout(data: dict[str, Any]): print(json.dumps(data))
    def handle_file_not_found_error(exception: FileNotFoundError): print(json.dumps({"status": "error", "message": f"File not found: {exception}"})); sys.exit(1)
    def handle_value_error(exception: ValueError): print(json.dumps({"status": "error", "message": f"Invalid value: {exception}"})); sys.exit(1)
    def handle_unexpected_error(exception: Exception): print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {exception}"})); sys.exit(1)

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
        if not os.path.exists(catalog_path):
            raise FileNotFoundError(f"The catalog file was not found at the specified path: {catalog_path}")

        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)

        # Handle --updates as a file path or a JSON string
        updates_raw = args.updates
        if os.path.exists(updates_raw):
            try:
                with open(updates_raw, 'r', encoding='utf-8') as f:
                    updates = json.load(f)
            except Exception as e:
                # If it's a valid path but failed to read as JSON, it's an error.
                raise ValueError(f"Failed to read updates from file {updates_raw}: {e}")
        else:
            try:
                updates = json.loads(updates_raw)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for --updates argument, and no such file found.")

        if not isinstance(updates, list):
            raise ValueError("--updates must be a JSON array of objects.")

        documents_dict = {doc['path']: doc for doc in catalog_data.get('documents', [])}

        updated_paths = []
        not_found_paths = []
        for update in updates:
            path = update.get('path')
            if not path:
                continue

            if path in documents_dict:
                doc_to_update = documents_dict[path]
                doc_to_update['title'] = update.get('title', doc_to_update.get('title'))
                doc_to_update['summary'] = update.get('summary', doc_to_update.get('summary'))
                updated_paths.append(path)
            else:
                not_found_paths.append(path)

        if not_found_paths:
            # We treat this as a warning or informational rather than a fatal error to allow partial updates?
            # Actually the original code raised FileNotFoundError. Let's keep it consistent but maybe more descriptive.
            print(json.dumps({
                "status": "warning",
                "message": f"Some document paths from the updates were not found in {catalog_path}.",
                "not_found_paths": not_found_paths
            }, ensure_ascii=False), file=sys.stderr)

        with open(catalog_path, 'w', encoding='utf-8') as f:
            json.dump(catalog_data, f, ensure_ascii=False, indent=2)

        output_data = {
            "status": "success",
            "message": f"Successfully updated {len(updated_paths)} documents in {catalog_path}.",
            "updated_paths": updated_paths
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