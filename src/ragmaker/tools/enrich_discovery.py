# -*- coding: utf-8 -*-
"""
enrich_discovery.py - A tool to batch update discovery.json with enriched data.
"""

import argparse
import json
import sys
import os
from ragmaker.io_utils import print_json_stdout, eprint_error

def main():
    """
    Main function to batch update a discovery.json file.
    """
    parser = argparse.ArgumentParser(description="Batch updates a discovery.json file with titles and summaries.")
    parser.add_argument("--discovery-path", required=True, help="Full path to the discovery.json file to be updated.")
    parser.add_argument("--updates", required=True, help="A JSON string of an array of update objects, each with 'path', 'title', and 'summary'.")
    args = parser.parse_args()

    discovery_path = args.discovery_path

    try:
        # 1. Load and parse the discovery.json file
        if not os.path.exists(discovery_path):
            raise FileNotFoundError(f"The discovery file was not found at the specified path: {discovery_path}")

        with open(discovery_path, 'r', encoding='utf-8') as f:
            discovery_data = json.load(f)

        # 2. Parse the updates JSON string
        try:
            updates = json.loads(args.updates)
            if not isinstance(updates, list):
                raise ValueError("--updates must be a JSON array of objects.")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for --updates argument.")

        # 3. Create a dictionary for efficient lookup
        documents_dict = {doc['path']: doc for doc in discovery_data.get('documents', [])}

        # 4. Loop through updates and apply them
        updated_paths = []
        not_found_paths = []
        for update in updates:
            path = update.get('path')
            if not path:
                continue # or handle error if path is mandatory in an update

            if path in documents_dict:
                doc_to_update = documents_dict[path]
                doc_to_update['title'] = update.get('title', doc_to_update.get('title'))
                doc_to_update['summary'] = update.get('summary', doc_to_update.get('summary'))
                updated_paths.append(path)
            else:
                not_found_paths.append(path)

        if not_found_paths:
            raise FileNotFoundError(f"The following document paths from the updates were not found in {discovery_path}: {', '.join(not_found_paths)}")

        # 5. Write the updated data back to the file
        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(discovery_data, f, ensure_ascii=False, indent=2)

        output_data = {
            "status": "success",
            "message": f"Successfully updated {len(updated_paths)} documents in {discovery_path}.",
            "updated_paths": updated_paths
        }
        print_json_stdout(output_data)

    except (FileNotFoundError, ValueError) as e:
        error_data = {
            "status": "error",
            "path": discovery_path,
            "message": str(e)
        }
        eprint_error(error_data)
        sys.exit(1)
    except Exception as e:
        error_data = {
            "status": "error",
            "path": discovery_path,
            "message": f"An unexpected error occurred: {e}"
        }
        eprint_error(error_data)
        sys.exit(1)

if __name__ == "__main__":
    main()
