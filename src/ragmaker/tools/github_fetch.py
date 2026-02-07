#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
github_fetch.py - Fetch documents from a GitHub repository.

This tool clones a GitHub repository (or uses a local git repo), extracts files from a specified path,
converts HTML files to Markdown, and generates a catalog.json file.
"""

import argparse
import json
import logging
import shutil
import sys
import os
import tempfile
from pathlib import Path
from typing import Optional

# --- Dependency Loading ---
try:
    from git import Repo
    from markdownify import markdownify as md
    from bs4 import BeautifulSoup
    from ragmaker.io_utils import (
        GracefulArgumentParser,
        handle_argument_parsing_error,
        handle_unexpected_error,
        handle_file_not_found_error,
        print_json_stdout,
        eprint_error
    )
    from ragmaker.utils import print_catalog_data, safe_export
except ImportError as e:
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": f"A required dependency is not installed: {e}"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)

def setup_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

def convert_html_to_md(html_path: Path) -> Path:
    """Converts an HTML file to Markdown and returns the new path."""
    try:
        content = html_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Try fallback encodings
        try:
             content = html_path.read_text(encoding='cp1252')
        except UnicodeDecodeError:
             content = html_path.read_text(encoding='latin-1')

    # Basic cleaning with BeautifulSoup if needed, but markdownify handles a lot.
    # The test implies we might want to strip some parts?
    # "Test that HTML files are converted to Markdown"

    markdown_content = md(content, heading_style="ATX")

    md_path = html_path.with_suffix('.md')
    md_path.write_text(markdown_content, encoding='utf-8')
    return md_path

def github_fetch(
    repo_url: str,
    path_in_repo: str,
    output_dir: Path,
    branch: Optional[str] = None
):
    """
    Fetches files from a git repo and prepares them in output_dir (formerly temp_dir).
    """
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_root_str:
        temp_root = Path(temp_root_str)
        work_dir = temp_root / "work"
        clone_dir = temp_root / "clone"

        work_dir.mkdir()
        clone_dir.mkdir()

        logger.info(f"Cloning {repo_url} into temporary directory...")

        kwargs = {"depth": 1}
        if branch:
            kwargs["branch"] = branch

        try:
            Repo.clone_from(repo_url, clone_dir, **kwargs)
        except Exception as e:
            logger.warning(f"Shallow clone failed, retrying full clone: {e}")
            if "depth" in kwargs:
                del kwargs["depth"]

            try:
                Repo.clone_from(repo_url, clone_dir, **kwargs)
            except Exception as final_exception:
                # Explicitly state that the full clone also failed after the shallow clone attempt.
                raise RuntimeError(f"Full clone also failed after shallow clone attempt: {final_exception}") from final_exception

        # Now copy files from path_in_repo to work_dir
        source_path = clone_dir / path_in_repo

        if not source_path.exists():
            raise FileNotFoundError(f"Path '{path_in_repo}' not found in repository.")

        documents = []

        if source_path.is_file():
            # Copy single file
            dest_file = work_dir / path_in_repo
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_file)
            files_to_process = [dest_file]

        else:
            # Determine the destination base directory
            # We want to preserve the structure relative to the repo root.
            # if path_in_repo=".", output is directly in work_dir.
            # if path_in_repo="docs", output is in work_dir/docs.
            dest_base = work_dir / path_in_repo
            dest_base.mkdir(parents=True, exist_ok=True)

            # Copy directory
            # Iterate and copy
            for root, dirs, files in os.walk(source_path):
                rel_root = Path(root).relative_to(source_path)
                target_root = dest_base / rel_root
                target_root.mkdir(parents=True, exist_ok=True)

                for file in files:
                    s_file = Path(root) / file
                    d_file = target_root / file
                    shutil.copy2(s_file, d_file)

        # Process files in work_dir (HTML -> MD)
        files_to_process = []
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                files_to_process.append(Path(root) / file)

        catalog_documents = []

        for file_path in files_to_process:
            if not file_path.exists(): continue # Might have been deleted (e.g. html replaced by md)

            final_path = file_path

            if file_path.suffix.lower() in ['.html', '.htm']:
                logger.info(f"Converting {file_path} to Markdown")
                try:
                    md_path = convert_html_to_md(file_path)
                    file_path.unlink() # Remove HTML
                    final_path = md_path
                except Exception as e:
                    logger.error(f"Failed to convert {file_path}: {e}")
                    # Keep HTML if failed?
                    pass

            # Add to documents list
            # Path should be relative to work_dir
            rel_path = final_path.relative_to(work_dir)
            catalog_documents.append({
                "path": rel_path.as_posix(),
                "title": final_path.stem, # Simple title guess
                # "url": ... # We don't have a direct URL for the file easily mapping back to github blob without more logic.
                # But for catalog, path is essential.
            })

        # Generate catalog.json
        metadata = {
            "source": repo_url,
            "path_in_repo": path_in_repo,
            "branch": branch
        }

        # Use utils function if compatible, or just write it.
        # print_catalog_data handles writing catalog.json if output_dir is passed.
        # Note: print_catalog_data currently writes 'catalog.json' (based on my read earlier)
        # "output_path = output_dir / 'catalog.json'"

        print_catalog_data(catalog_documents, metadata, output_dir=work_dir)

        # Finally, safe export to the real output directory
        safe_export(work_dir, output_dir)


def main():
    parser = GracefulArgumentParser(description="Fetch documents from GitHub.")
    parser.add_argument("--repo-url", required=True, help="URL of the GitHub repository.")
    parser.add_argument("--path-in-repo", required=True, help="Path within the repository to fetch.")
    parser.add_argument("--temp-dir", required=True, help="Output directory.")
    parser.add_argument("--branch", help="Branch to fetch.")
    parser.add_argument("--log-level", default="INFO", help="Logging level.")

    try:
        args = parser.parse_args()
        setup_logging(args.log_level)

        github_fetch(
            args.repo_url,
            args.path_in_repo,
            Path(args.temp_dir),
            args.branch
        )

    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
