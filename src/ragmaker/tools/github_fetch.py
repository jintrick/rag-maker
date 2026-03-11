#!/usr/bin/env python3
import argparse
import json
import logging
import sys
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

try:
    from ragmaker.io_utils import (
        GracefulArgumentParser,
        eprint_error,
        handle_unexpected_error,
    )
    from ragmaker.utils import print_catalog_data, safe_export
except ImportError:
    sys.stderr.write("{\"status\": \"error\", \"message\": \"The 'ragmaker' package is not installed or not in the Python path.\"}\x0a")
    sys.exit(1)

try:
    from git import Repo, GitCommandError
except ImportError:
    sys.stderr.write("GitPython required\x0a")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
    from readabilipy import simple_json_from_html_string
except ImportError:
    sys.stderr.write("Required libraries missing\x0a")
    sys.exit(1)

def github_fetch(repo_url: str, path_in_repo: str, temp_dir: Path, branch: Optional[str] = None):
    with tempfile.TemporaryDirectory() as temp_root:
        clone_dir = Path(temp_root) / "clone"
        work_dir = Path(temp_root) / "processed"
        work_dir.mkdir(parents=True, exist_ok=True)
        repo = Repo.init(clone_dir)
        origin = repo.create_remote("origin", repo_url)
        origin.fetch()
        repo.git.execute(["git", "config", "core.sparseCheckout", "true"])
        sparse_path = clone_dir / ".git" / "info" / "sparse-checkout"
        sparse_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sparse_path, "w", encoding="utf-8") as f:
            if not path_in_repo or path_in_repo == ".": f.write("/*\x0a!/.git\x0a")
            else: f.write(path_in_repo + "/*\x0a" + path_in_repo + "\x0a")
        if not branch:
            try: branch = repo.git.execute(["git", "symbolic-ref", "refs/remotes/origin/HEAD"]).split("/")[-1].strip()
            except Exception: branch = "main"
        repo.git.execute(["git", "checkout", branch])
        allowed = {".md", ".mdx", ".txt", ".py", ".html", ".htm"}
        scan_path = clone_dir / path_in_repo.strip("/")
        files = []
        if scan_path.is_file(): files.append(scan_path)
        elif scan_path.is_dir():
            for r, _, fs in os.walk(scan_path):
                for f in fs: files.append(Path(r) / f)
        results = []
        for src in files:
            if src.suffix.lower() not in allowed: continue
            rel = src.relative_to(clone_dir)
            dst = work_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            url = repo_url.replace(".git","") + "/blob/" + branch + "/" + rel.as_posix()
            timestamp = datetime.now(timezone.utc).isoformat()
            if src.suffix.lower() in {".html", ".htm"}:
                try:
                    art = simple_json_from_html_string(src.read_text(encoding="utf-8"))
                    if art and art.get("content"):
                        dst = dst.with_suffix(".md")
                        title = art.get("title") or src.stem
                        markdown_content = md(art["content"], heading_style="ATX")
                        frontmatter = f"---\nsource_url: {url}\noriginal_title: {title}\nfetched_at: {timestamp}\n---\n\n"
                        dst.write_text(f"{frontmatter}{markdown_content}", encoding="utf-8")
                except Exception: continue
            else:
                try:
                    content = src.read_text(encoding="utf-8")
                    title = src.stem
                    frontmatter = f"---\nsource_url: {url}\noriginal_title: {title}\nfetched_at: {timestamp}\n---\n\n"
                    dst.write_text(f"{frontmatter}{content}", encoding="utf-8")
                except Exception:
                    shutil.copy2(src, dst)
            if dst.exists():
                results.append({"url": url, "path": dst.relative_to(work_dir).as_posix()})
        safe_export(work_dir, temp_dir)
        return results

def main():
    parser = GracefulArgumentParser(description="Fetch from GitHub")
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--path-in-repo", required=True)
    parser.add_argument("--temp-dir", required=True)
    parser.add_argument("--branch", default=None)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--verbose", "-v", action="store_true")
    try:
        args = parser.parse_args()
        res = github_fetch(args.repo_url, args.path_in_repo, Path(args.temp_dir), args.branch)
        print_catalog_data(res, {"source": "github_fetch", "repo_url": args.repo_url})
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
