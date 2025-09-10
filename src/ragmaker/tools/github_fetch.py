#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHubリポジトリからドキュメントを取得し、ファイルとして保存するツール。

指定されたGitHubリポジトリから特定パスのドキュメントを効率的に取得するため、
Gitのスパースチェックアウト機能を利用する。
取得したファイルがHTMLの場合はMarkdownに変換し、それ以外のサポート対象ファイルは
そのままコピーする。
AIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
構造化されたJSONによるレポート出力を提供する。

Usage:
    python github_fetch.py --repo-url <repo_url> --path-in-repo <path> --temp-dir <path/to/dir> [--branch <branch_name>]

Args:
    --repo-url (str): 取得対象のGitHubリポジトリのURL。
    --path-in-repo (str): リポジトリ内で収集対象とするディレクトリまたはファイルのパス。
    --temp-dir (str): 取得したファイルを保存する（出力）ディレクトリのパス。
    --branch (str, optional): 取得対象のブランチ名。指定されない場合、リポジトリのデフォルトブランチが使われる。

Returns:
    (stdout): 成功した場合、処理結果をまとめたJSONオブジェクト。
    (stderr): エラーが発生した場合、エラーコードと詳細を含むJSONオブジェクト。
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
    from ragmaker.utils import print_discovery_data
except ImportError:
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "The 'ragmaker' package is not installed or not in the Python path.",
        "remediation_suggestion": "Please install the package, e.g., via 'pip install .'"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

try:
    from git import Repo, GitCommandError
except ImportError:
    eprint_error({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required library 'GitPython' not found.",
        "remediation_suggestion": "Please install the required library by running: pip install GitPython"
    })
    sys.exit(1)

try:
    from bs4 import BeautifulSoup, Tag
    from markdownify import markdownify as md
    from readabilipy import simple_json_from_html_string
except ImportError:
    eprint_error({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required libraries 'beautifulsoup4', 'markdownify', or 'readabilipy' not found.",
        "remediation_suggestion": "Please ensure required libraries are installed."
    })
    sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Structured Error Handling (Tool-specific) ---
def handle_git_error(exception: Exception):
    """Handles Git-related errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "GIT_ERROR",
        "message": "A Git command failed to execute.",
        "remediation_suggestion": (
            "Ensure the repository URL is correct, the branch exists, "
            "and you have the necessary permissions. Also check if Git is installed."
        ),
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })

# --- HTML Processing ---

def _is_noise_element(tag: Tag) -> bool:
    """A helper function to identify and remove noise elements from HTML."""
    noise_keywords = ['ad', 'advert', 'comment', 'share', 'social', 'extra', 'sidebar']
    for attr in ['class', 'id']:
        values = tag.get(attr, [])
        if any(keyword in v for v in values for keyword in noise_keywords):
            if not tag.find_parent('article') and not tag.find_parent('main'):
                return True
    return False

class HTMLProcessor:
    """Encapsulates the logic for converting HTML files to Markdown."""

    @staticmethod
    def convert_html_file_to_markdown(file_path: Path) -> Optional[str]:
        """
        Extracts main content from an HTML file using readabilipy,
        cleans it, and converts it to Markdown.
        """
        logger.debug(f"Processing HTML file with readabilipy: {file_path}")
        try:
            html_content = file_path.read_text(encoding='utf-8')
            article = simple_json_from_html_string(html_content, use_readability=True)

            if not article or not article.get('content'):
                logger.warning(f"readabilipy could not extract content from {file_path}.")
                return None

            title = article.get('title', '')
            html_snippet = article['content']

            soup = BeautifulSoup(html_snippet, 'html.parser')
            for element in soup.find_all(_is_noise_element):
                element.decompose()
            # The rest of the function continues after this block...
            # The following lines are part of the original function and should be kept.
            cleaned_html = str(soup)
            markdown_content = md(cleaned_html, heading_style="ATX")

            if title and not markdown_content.strip().startswith('#'):
                 markdown_content = f"# {title}\n\n{markdown_content}"

            return markdown_content

        except Exception as e:
            logger.error(f"Failed during content extraction or conversion for {file_path}: {e}", exc_info=True)
            return None

# --- Core Logic ---

class GitHubFetcher:
    """
    Clones a GitHub repository, processes its files by converting HTML to
    Markdown, and copies other relevant files to an output directory.
    """
    def __init__(self, args: argparse.Namespace):
        """Initializes the GitHubFetcher instance."""
        self.repo_url = args.repo_url
        self.path_in_repo = args.path_in_repo.strip('/')
        self.output_dir = Path(args.temp_dir)
        self.branch: Optional[str] = args.branch
        self.fetched_files_map: list[dict] = []

    def run(self):
        """
        Executes the entire process of cloning, processing, and saving files.
        """
        logger.info(f"Starting fetch for repo: {self.repo_url}")
        with tempfile.TemporaryDirectory() as clone_dir_str:
            clone_dir = Path(clone_dir_str)
            try:
                # Initialize a git repo in the temporary directory
                repo = Repo.init(clone_dir)
                origin = repo.create_remote('origin', self.repo_url)

                # Fetch all remote branches
                origin.fetch()

                # Configure sparse checkout
                repo.git.execute(['git', 'config', 'core.sparseCheckout', 'true'])
                sparse_checkout_path = clone_dir / '.git' / 'info' / 'sparse-checkout'
                sparse_checkout_path.parent.mkdir(exist_ok=True)
                with open(sparse_checkout_path, 'w', encoding='utf-8') as f:
                    f.write(f"{self.path_in_repo}/*\n")
                    f.write(f"{self.path_in_repo}\n")

                # Determine the branch to checkout
                branch_to_checkout = self.branch
                if not branch_to_checkout:
                    # If no branch is specified, find the default branch
                    symref = repo.git.execute(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'])
                    branch_to_checkout = symref.split('/')[-1].strip()
                    logger.info(f"No branch specified, using default branch: {branch_to_checkout}")

                self.branch = branch_to_checkout # Update branch if it was auto-detected

                # Checkout the desired branch
                repo.git.execute(['git', 'checkout', branch_to_checkout])
                logger.info(f"Successfully checked out branch '{branch_to_checkout}' with sparse checkout for path '{self.path_in_repo}'")

            except GitCommandError as e:
                handle_git_error(e)
                raise
            except Exception as e:
                handle_unexpected_error(e)
                raise

            # Process the checked-out files
            self._process_repository_files(clone_dir)

    def _process_repository_files(self, clone_dir: Path):
        """
        Processes files from the cloned repository, converting HTML to Markdown
        and copying others, preserving the directory structure.
        """
        logger.info(f"Processing files from {clone_dir} into {self.output_dir}")
        source_path_to_scan = clone_dir / self.path_in_repo
        allowed_extensions = {".md", ".mdx", ".txt", ".py", ".html", ".htm"}

        if not source_path_to_scan.exists():
            logger.warning(f"Target path {source_path_to_scan} does not exist after checkout. It might be empty or incorrect.")
            return

        for root, _, files in os.walk(source_path_to_scan):
            for file in files:
                source_file_path = Path(root) / file
                if source_file_path.suffix.lower() not in allowed_extensions:
                    continue

                # Preserve directory structure relative to the repository root
                path_relative_to_repo_root = source_file_path.relative_to(clone_dir)
                dest_file_path = self.output_dir / path_relative_to_repo_root
                dest_file_path.parent.mkdir(parents=True, exist_ok=True)

                final_relative_path_str = ""

                if source_file_path.suffix.lower() in {".html", ".htm"}:
                    markdown_content = HTMLProcessor.convert_html_file_to_markdown(source_file_path)
                    if markdown_content:
                        dest_file_path = dest_file_path.with_suffix('.md')
                        dest_file_path.write_text(markdown_content, encoding='utf-8')
                        final_relative_path_str = dest_file_path.relative_to(self.output_dir).as_posix()
                        logger.debug(f"Converted '{source_file_path}' to '{dest_file_path}'")
                    else:
                        logger.warning(f"Skipping file {source_file_path} as conversion failed.")
                        continue
                else:
                    shutil.copy2(source_file_path, dest_file_path)
                    final_relative_path_str = dest_file_path.relative_to(self.output_dir).as_posix()
                    logger.debug(f"Copied '{source_file_path}' to '{dest_file_path}'")

                base_repo_url = self.repo_url.replace(".git", "")
                file_url = f"{base_repo_url}/blob/{self.branch}/{path_relative_to_repo_root.as_posix()}"

                self.fetched_files_map.append({
                    "url": file_url,
                    "path": final_relative_path_str
                })

        logger.info(f"Processed and saved {len(self.fetched_files_map)} files to {self.output_dir}")

def setup_logging(verbose: bool, log_level: str) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )

def main() -> None:
    """Main entry point."""
    parser = GracefulArgumentParser(description="Fetch documents from a GitHub repository, converting HTML to Markdown.")
    parser.add_argument("--repo-url", required=True, help="The URL of the GitHub repository to fetch.")
    parser.add_argument("--path-in-repo", required=True, help="The path within the repository to fetch documents from.")
    parser.add_argument("--temp-dir", required=True, help="Directory to save the processed documents.")
    parser.add_argument("--branch", type=str, default=None, help="The branch to fetch from. Defaults to the repository's default branch.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        output_dir_path = Path(args.temp_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        fetcher = GitHubFetcher(args)
        fetcher.run()

        metadata = {
            "source": "github_fetch",
            "repo_url": args.repo_url,
            "path_in_repo": args.path_in_repo,
            "branch": fetcher.branch
        }

        print_discovery_data(fetcher.fetched_files_map, metadata)

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except GitCommandError:
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred in main.")
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
