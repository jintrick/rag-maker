#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHubリポジトリからドキュメントを取得し、ファイルとして保存するツール。

指定されたGitHubリポジトリから特定パスのドキュメントを効率的に取得するため、
Gitのスパースチェックアウト機能を利用する。
AIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
構造化されたJSONによるレポート出力を提供する。

Usage:
    python github_fetch.py --repo-url <repo_url> --path-in-repo <path> --temp-dir <path/to/dir> [--branch <branch_name>]

Args:
    --repo-url (str): 取得対象のGitHubリポジトリのURL。
    --path-in-repo (str): リポジトリ内で収集対象とするディレクトリまたはファイルのパス。
    --temp-dir (str): 取得したファイルを保存する一時ディレクトリのパス。
    --branch (str, optional): 取得対象のブランチ名。指定されない場合、リポジトリのデフォルトブランチが使われる。

Returns:
    (stdout): 成功した場合、処理結果をまとめたJSONオブジェクト。
              例: {
                    "status": "success",
                    "output_dir": "/path/to/temp_output_directory",
                    "fetched_count": 15
                  }
    (stderr): エラーが発生した場合、エラーコードと詳細を含むJSONオブジェクト。
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path
from typing import Optional, List
from ragmaker.utils import create_discovery_file

# --- Dependency Check ---
try:
    from git import Repo, GitCommandError
except ImportError:
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required library 'GitPython' not found.",
        "remediation_suggestion": "Please install the required library by running: pip install GitPython"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

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
        "remediation_suggestion": (
            "Review the command-line parameters and ensure all required "
            "arguments are provided correctly."
        ),
        "details": {"original_error": str(exception)}
    })

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

def handle_unexpected_error(exception: Exception):
    """Handles unexpected errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred during processing.",
        "remediation_suggestion": "Check the input and environment, then try again.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })


# --- Core Logic ---

class GitHubFetcher:
    """GitHubリポジトリの取得と処理のロジックをカプセル化するクラス。"""
    def __init__(self, args: argparse.Namespace):
        """
        GitHubFetcherのインスタンスを初期化する。

        Args:
            args (argparse.Namespace): コマンドライン引数を格納したオブジェクト。
        """
        self.repo_url = args.repo_url
        self.path_in_repo = args.path_in_repo
        self.temp_dir = Path(args.temp_dir)
        self.branch = args.branch
        self.fetched_files_map = []

    def run(self):
        """リポジトリの取得とファイルの処理を実行する。"""
        logger.info("Starting fetch for repo: %s", self.repo_url)
        try:
            # 1. リポジトリを一時ディレクトリにクローン（ただし、オブジェクトのみ）
            repo = Repo.init(self.temp_dir)
            if not repo.remotes:
                origin = repo.create_remote('origin', self.repo_url)
            else:
                origin = repo.remotes.origin
                origin.set_url(self.repo_url)

            origin.fetch()

            # 2. スパースチェックアウトの設定
            repo.git.execute(['git', 'config', 'core.sparseCheckout', 'true'])
            sparse_checkout_path = self.temp_dir / '.git' / 'info' / 'sparse-checkout'

            # Ensure the .git/info directory exists
            sparse_checkout_path.parent.mkdir(exist_ok=True)

            with open(sparse_checkout_path, 'w', encoding='utf-8') as f:
                f.write(f"{self.path_in_repo.strip('/')}/*\n")
                f.write(f"{self.path_in_repo.strip('/')}\n")


            # 3. 指定されたブランチ（またはデフォルト）をチェックアウト
            branch_to_checkout = self.branch
            if not branch_to_checkout:
                # デフォルトブランチを取得 (e.g., 'origin/main' or 'origin/master')
                symref = repo.git.execute(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'])
                branch_to_checkout = symref.split('/')[-1].strip()
                logger.info("No branch specified, using default branch: %s", branch_to_checkout)

            repo.git.execute(['git', 'checkout', branch_to_checkout])
            logger.info("Successfully checked out branch '%s' with sparse checkout for path '%s'", branch_to_checkout, self.path_in_repo)

        except GitCommandError as e:
            handle_git_error(e)
            # Re-raise or exit to stop execution
            raise
        except Exception as e:
            handle_unexpected_error(e)
            raise

        self._discover_files()

    def _discover_files(self):
        """
        チェックアウトされたディレクトリをスキャンし、対象ファイルを特定して
        `fetched_files_map` に格納する。
        """
        logger.info("Discovering files in %s", self.temp_dir)
        target_path = self.temp_dir / self.path_in_repo
        allowed_extensions = {".md", ".mdx", ".txt", ".py", ".html", ".htm"}

        if not target_path.exists():
            logger.warning("Target path %s does not exist after checkout. It might be empty or incorrect.", target_path)
            return

        for root, _, files in os.walk(target_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in allowed_extensions:
                    # Create a repo-relative path for the discovery file
                    relative_path = file_path.relative_to(self.temp_dir).as_posix()

                    # Construct the GitHub URL
                    # Assumes a standard github.com URL structure
                    base_repo_url = self.repo_url.replace(".git", "")
                    file_url = f"{base_repo_url}/blob/{self.branch}/{relative_path}"

                    self.fetched_files_map.append({
                        "url": file_url,
                        "path": relative_path
                    })
        logger.info("Discovered %d relevant files.", len(self.fetched_files_map))


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
    setup_logging(verbose=False, log_level='INFO')

    parser = GracefulArgumentParser(description="Fetch documents from a GitHub repository.")
    parser.add_argument("--repo-url", required=True, help="The URL of the GitHub repository to fetch.")
    parser.add_argument("--path-in-repo", required=True, help="The path within the repository to fetch documents from.")
    parser.add_argument("--temp-dir", required=True, help="Directory to save the fetched documents.")
    parser.add_argument("--branch", type=str, default=None, help="The branch to fetch from. Defaults to the repository's default branch.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        # Core logic will be added here in the next steps.
        # For now, just print a success message if parsing is successful.

        # Create the temporary directory if it doesn't exist
        temp_dir_path = Path(args.temp_dir)
        temp_dir_path.mkdir(parents=True, exist_ok=True)

        # Create and run the fetcher
        fetcher = GitHubFetcher(args)
        fetcher.run()

        # Write the discovery.json file
        try:
            create_discovery_file(fetcher.fetched_files_map, temp_dir_path)
        except IOError as e:
            logger.error("Could not write discovery.json: %s", e)
            # This is a critical error, so we'll let it be caught by the main exception handler
            raise

        # Print final JSON report to stdout
        result = {
            "status": "success",
            "output_dir": str(temp_dir_path.resolve()),
            "fetched_count": len(fetcher.fetched_files_map)
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except GitCommandError as e:
        # Already handled in the fetcher, but exit here.
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
