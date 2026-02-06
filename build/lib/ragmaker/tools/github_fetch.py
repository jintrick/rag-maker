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
        self.branch: str | None = args.branch
        self.fetched_files_map: list[dict] = []

    def run(self):
        """リポジトリの取得とファイルの処理を実行する。"""
        logger.info(f"Starting fetch for repo: {self.repo_url}")
        try:
            repo = Repo.init(self.temp_dir)
            if not repo.remotes:
                origin = repo.create_remote('origin', self.repo_url)
            else:
                origin = repo.remotes.origin
                origin.set_url(self.repo_url)

            origin.fetch()

            repo.git.execute(['git', 'config', 'core.sparseCheckout', 'true'])
            sparse_checkout_path = self.temp_dir / '.git' / 'info' / 'sparse-checkout'
            sparse_checkout_path.parent.mkdir(exist_ok=True)

            with open(sparse_checkout_path, 'w', encoding='utf-8') as f:
                f.write(f"{self.path_in_repo.strip('/')}/*\n")
                f.write(f"{self.path_in_repo.strip('/')}\n")

            branch_to_checkout = self.branch
            if not branch_to_checkout:
                symref = repo.git.execute(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'])
                branch_to_checkout = symref.split('/')[-1].strip()
                logger.info(f"No branch specified, using default branch: {branch_to_checkout}")

            self.branch = branch_to_checkout # Update branch if it was auto-detected

            repo.git.execute(['git', 'checkout', branch_to_checkout])
            logger.info(f"Successfully checked out branch '{branch_to_checkout}' with sparse checkout for path '{self.path_in_repo}'")

        except GitCommandError as e:
            handle_git_error(e)
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
        logger.info(f"Discovering files in {self.temp_dir}")
        target_path = self.temp_dir / self.path_in_repo
        allowed_extensions = {".md", ".mdx", ".txt", ".py", ".html", ".htm"}

        if not target_path.exists():
            logger.warning(f"Target path {target_path} does not exist after checkout. It might be empty or incorrect.")
            return

        for root, _, files in os.walk(target_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in allowed_extensions:
                    relative_path = file_path.relative_to(self.temp_dir).as_posix()
                    base_repo_url = self.repo_url.replace(".git", "")
                    file_url = f"{base_repo_url}/blob/{self.branch}/{relative_path}"

                    self.fetched_files_map.append({
                        "url": file_url,
                        "path": relative_path
                    })
        logger.info(f"Discovered {len(self.fetched_files_map)} relevant files.")


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

        temp_dir_path = Path(args.temp_dir)
        temp_dir_path.mkdir(parents=True, exist_ok=True)

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
