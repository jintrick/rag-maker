#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub fetch tool.

Features:
- Fetches files from a GitHub repository (supports sparse checkout).
- Converts HTML files to Markdown using readability metrics.
- Safely exports results to the destination directory.
- Generates a catalog.json file.
"""

import argparse
import json
import logging
import sys
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# --- Dependency Check ---
try:
    from ragmaker.io_utils import (
        ArgumentParsingError,
        GracefulArgumentParser,
        eprint_error,
        handle_argument_parsing_error,
        handle_unexpected_error,
    )
    from ragmaker.utils import print_catalog_data, safe_export
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

try:
    from git import Repo, GitCommandError
except ImportError:
    eprint_error({"status": "error", "message": "GitPython not found"})
    sys.exit(1)

try:
    from bs4 import BeautifulSoup, Tag
    from markdownify import markdownify as md
    from readabilipy import simple_json_from_html_string
except ImportError:
    eprint_error({
        "status": "error", 
        "message": "Required libraries not found.",
        "remediation_suggestion": "Please ensure 'beautifulsoup4', 'markdownify', and 'readabilipy' are installed."
    })
    sys.exit(1)

logger = logging.getLogger(__name__)

def handle_git_error(exception: Exception):
    eprint_error({"status": "error", "error_code": "GIT_ERROR", "message": str(exception)})

def _is_noise_element(tag: Tag) -> bool:
    noise_keywords = ['ad', 'advert', 'comment', 'share', 'social', 'extra', 'sidebar']
    for attr in ['class', 'id']:
        val = tag.get(attr)
        if not val: continue
        values = val if isinstance(val, list) else [val]
        if any(keyword in v for v in values for keyword in noise_keywords):
            if not tag.find_parent('article') and not tag.find_parent('main'):
                return True
    return False

class HTMLProcessor:
    @staticmethod
    def convert_html_file_to_markdown(file_path: Path) -> Optional[str]:
        try:
            html_content = file_path.read_text(encoding='utf-8')
            try:
                article = simple_json_from_html_string(html_content, use_readability=True)
            except IndexError:
                article = simple_json_from_html_string(html_content, use_readability=False)
            except Exception:
                return None
            
            if not article or not article.get('content'): return None
            title = article.get('title', '')
            html_snippet = article['content']
            soup = BeautifulSoup(html_snippet, 'html.parser')
            for element in soup.find_all(_is_noise_element):
                element.decompose()
            cleaned_html = str(soup)
            markdown_content = md(cleaned_html, heading_style="ATX")
            if title and not markdown_content.strip().startswith('#'):
                 markdown_content = f"# {title}\n\n{markdown_content}"
            return markdown_content
        except Exception as e:
            logger.error(f"Failed conversion: {e}")
            return None

class GitHubFetcher:
    def __init__(self, args: argparse.Namespace):
        self.repo_url = args.repo_url
        self.path_in_repo = args.path_in_repo.strip('/')
        # actual_output_dir: The final destination specified by the user
        self.actual_output_dir = Path(args.temp_dir)
        self.branch: Optional[str] = args.branch
        self.fetched_files_map: list[dict] = []
        # work_dir will be set in run()
        self.work_dir: Optional[Path] = None

    def run(self):
        # Use a temporary directory for all operations (cloning and processing)
        with tempfile.TemporaryDirectory() as temp_root_str:
            temp_root = Path(temp_root_str)
            clone_dir = temp_root / "clone"
            # processed_dir will hold the final files to be exported
            self.work_dir = temp_root / "processed"
            self.work_dir.mkdir()

            try:
                # Clone and Checkout
                repo = Repo.init(clone_dir)
                origin = repo.create_remote('origin', self.repo_url)
                origin.fetch()
                
                repo.git.execute(['git', 'config', 'core.sparseCheckout', 'true'])
                sparse_checkout_path = clone_dir / '.git' / 'info' / 'sparse-checkout'
                sparse_checkout_path.parent.mkdir(exist_ok=True)
                with open(sparse_checkout_path, 'w', encoding='utf-8') as f:
                    if self.path_in_repo == '.' or not self.path_in_repo:
                        f.write("/*\n!/.git\n")
                    else:
                        f.write(f"{self.path_in_repo}/*\n{self.path_in_repo}\n")
                
                branch_to_checkout = self.branch
                if not branch_to_checkout:
                    symref = repo.git.execute(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'])
                    branch_to_checkout = symref.split('/')[-1].strip()
                self.branch = branch_to_checkout
                repo.git.execute(['git', 'checkout', branch_to_checkout])
            except Exception as e:
                handle_git_error(e)
                raise
            
            # Process files from clone_dir to work_dir
            self._process_repository_files(clone_dir)
            
            # Safe Export to final destination
            # This ensures we don't leave partial files or overwrite unsafely
            safe_export(self.work_dir, self.actual_output_dir)

    def _process_repository_files(self, clone_dir: Path):
        source_path_to_scan = clone_dir / self.path_in_repo
        allowed_extensions = {'.md', '.mdx', '.txt', '.py', '.html', '.htm'}
        
        if not source_path_to_scan.exists():
            return
        
        files_to_process = []
        if source_path_to_scan.is_file():
            # If path_in_repo points to a single file
            files_to_process.append(source_path_to_scan)
        else:
            # If path_in_repo points to a directory
            for root, _, files in os.walk(source_path_to_scan):
                for file in files:
                    files_to_process.append(Path(root) / file)

        for source_file_path in files_to_process:
            if source_file_path.suffix.lower() not in allowed_extensions:
                continue

            # path_relative_to_repo_root includes path_in_repo
            path_relative_to_repo_root = source_file_path.relative_to(clone_dir)
            
            # Determine destination path in work_dir
            dest_file_path = self.work_dir / path_relative_to_repo_root
            dest_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            final_path_str = None
            
            if source_file_path.suffix.lower() in {'.html', '.htm'}:
                markdown_content = HTMLProcessor.convert_html_file_to_markdown(source_file_path)
                if markdown_content:
                    dest_file_path = dest_file_path.with_suffix('.md')
                    dest_file_path.write_text(markdown_content, encoding='utf-8')
                    final_path_str = dest_file_path.relative_to(self.work_dir).as_posix()
                else:
                    continue
            else:
                shutil.copy2(source_file_path, dest_file_path)
                final_path_str = dest_file_path.relative_to(self.work_dir).as_posix()
            
            if final_path_str:
                base_repo_url = self.repo_url.replace('.git', '')
                file_url = f"{base_repo_url}/blob/{self.branch}/{path_relative_to_repo_root.as_posix()}"
                self.fetched_files_map.append({"url": file_url, "path": final_path_str})

def setup_logging(verbose: bool, log_level: str) -> None:
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for h in root_logger.handlers[:]: root_logger.removeHandler(h)
    root_logger.addHandler(handler)

def main() -> None:
    parser = GracefulArgumentParser(description="Fetch from GitHub")
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--path-in-repo", required=True)
    parser.add_argument("--temp-dir", required=True, help="Output directory")
    parser.add_argument("--branch", default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    
    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)
        
        # We don't need to mkdir args.temp_dir here because safe_export will handle it,
        # or it will be created if it doesn't exist.
        
        fetcher = GitHubFetcher(args)
        fetcher.run()
        
        # Output catalog.json
        # Note: safe_export has already moved the files to args.temp_dir.
        # So we can write catalog.json directly to args.temp_dir.
        output_dir_path = Path(args.temp_dir)
        print_catalog_data(
            fetcher.fetched_files_map, 
            {"source": "github_fetch", "repo_url": args.repo_url}, 
            output_dir=output_dir_path
        )
        
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
