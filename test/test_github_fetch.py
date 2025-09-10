import unittest
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
import sys
import os
from typing import Any, Type, Optional

# Add src to path to allow importing ragmaker and its dependencies
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Define Repo as Any initially to satisfy mypy if GitPython is not installed
Repo: Any = None

try:
    from git import Repo as GitRepoType
    Repo = GitRepoType
except ImportError:
    pass

@unittest.skipIf(Repo is None, "GitPython is not installed, skipping TestGitHubFetch")
class TestGitHubFetch(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory and a local git repository."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.test_dir.name) / "test_repo"
        self.repo_dir.mkdir()

        # Initialize a new git repository
        self.repo = Repo.init(self.repo_dir)

        # Create a docs directory and a file within it
        docs_dir = self.repo_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "test_file.md").write_text("hello world")
        (self.repo_dir / "README.md").write_text("# Test Repo")


        # Add and commit the file
        self.repo.index.add(["docs/test_file.md", "README.md"])
        self.repo.index.commit("Initial commit")
        self.main_branch = self.repo.active_branch.name


    def tearDown(self):
        """Clean up the temporary directory."""
        self.repo.close()
        self.test_dir.cleanup()

    def test_html_conversion_and_copying(self):
        """
        Test that HTML files are converted to Markdown, and other files are copied.
        """
        output_dir = Path(self.test_dir.name) / "output_html"
        repo_url = self.repo_dir.as_uri()
        path_in_repo = "html_docs"

        # Create files for HTML conversion test
        html_docs_dir = self.repo_dir / path_in_repo
        html_docs_dir.mkdir(exist_ok=True)
        (html_docs_dir / "test.html").write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>My Test Page</title></head>
        <body>
            <header><h1>Header</h1></header>
            <div class="ad">An ad</div>
            <article>
                <p>This is the main content.</p>
            </article>
            <footer>Footer</footer>
        </body>
        </html>
        """)
        (html_docs_dir / "plain.txt").write_text("This is a plain text file.")

        # Add and commit these new files
        self.repo.index.add([f"{path_in_repo}/test.html", f"{path_in_repo}/plain.txt"])
        self.repo.index.commit("Add files for html conversion test")


        process = subprocess.run(
            [
                "python", "-m", "src.ragmaker.tools.github_fetch",
                "--repo-url", repo_url,
                "--path-in-repo", path_in_repo,
                "--temp-dir", str(output_dir),
                "--branch", self.main_branch,
                "--log-level", "DEBUG" # for easier debugging
            ],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        self.assertEqual(process.returncode, 0, f"Script failed: {process.stderr}")

        # Check that output directory and files exist
        self.assertTrue(output_dir.exists())
        converted_md = output_dir / path_in_repo / "test.md"
        copied_txt = output_dir / path_in_repo / "plain.txt"
        original_html = output_dir / path_in_repo / "test.html"

        self.assertTrue(converted_md.exists(), f"Markdown file was not created. Stderr: {process.stderr}")
        self.assertTrue(copied_txt.exists(), "Text file was not copied.")
        self.assertFalse(original_html.exists(), "Original HTML file should not be present in the preserved structure.")

        # Check content of converted markdown
        md_content = converted_md.read_text()
        self.assertIn("# My Test Page", md_content)
        self.assertIn("This is the main content.", md_content)
        self.assertNotIn("An ad", md_content) # Check that cleaning happened
        self.assertNotIn("Header", md_content)
        self.assertNotIn("Footer", md_content)

        # Check content of copied text file
        self.assertEqual(copied_txt.read_text(), "This is a plain text file.")

        # Check JSON output
        try:
            stdout_json = json.loads(process.stdout)
        except json.JSONDecodeError:
            self.fail(f"Stdout was not valid JSON.\nStdout: {process.stdout}\nStderr: {process.stderr}")

        self.assertEqual(len(stdout_json["documents"]), 2)

        paths = {doc["path"] for doc in stdout_json["documents"]}
        self.assertIn("html_docs/test.md", paths)
        self.assertIn("html_docs/plain.txt", paths)

    def test_fetch_and_stdout_json(self):
        """
        Test that github_fetch can fetch from a local repo
        and prints the discovery JSON to stdout.
        """
        output_dir = Path(self.test_dir.name) / "output"
        self.assertFalse(output_dir.exists())

        # Use the local repository with the file:// protocol
        # Using as_uri() is more robust for path handling across OSes
        repo_url = self.repo_dir.as_uri()
        path_in_repo = "docs"

        process = subprocess.run(
            [
                "python", "-m", "src.ragmaker.tools.github_fetch",
                "--repo-url", repo_url,
                "--path-in-repo", path_in_repo,
                "--temp-dir", str(output_dir),
                "--branch", self.main_branch
            ],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        # Check for successful execution
        self.assertEqual(process.returncode, 0, f"github_fetch.py script failed with stderr: {process.stderr}")

        # The tool should still create the output directory and fetch the files.
        self.assertTrue(output_dir.exists())
        self.assertTrue((output_dir / "docs" / "test_file.md").exists())
        # It should NOT fetch files outside the sparse checkout path
        self.assertFalse((output_dir / "README.md").exists())

        # Verify the stdout is a valid JSON with the correct structure
        try:
            stdout_json = json.loads(process.stdout)
        except json.JSONDecodeError:
            self.fail(f"Stdout was not valid JSON.\nStdout: {process.stdout}")

        # Check for discovery data structure
        self.assertIn("documents", stdout_json)
        self.assertIn("metadata", stdout_json)
        self.assertIsInstance(stdout_json["documents"], list)
        self.assertEqual(len(stdout_json["documents"]), 1)

        # Check the content of the discovery data
        document_info = stdout_json["documents"][0]
        self.assertEqual(document_info["path"], "docs/test_file.md")
        # The URL should be constructed correctly, even for a local file URI
        self.assertIn("test_repo/blob", document_info["url"])
        self.assertIn(self.main_branch, document_info["url"])
        self.assertIn("docs/test_file.md", document_info["url"])

        # Check metadata
        self.assertEqual(stdout_json["metadata"]["source"], "github_fetch")
        self.assertEqual(stdout_json["metadata"]["repo_url"], repo_url)


if __name__ == '__main__':
    unittest.main()
