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

from git import Repo

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

    def run_tool(self, args):
        """Helper to run the tool and handle output encoding."""
        env = os.environ.copy()
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = src_path + os.pathsep + env["PYTHONPATH"]
        else:
            env["PYTHONPATH"] = src_path

        process = subprocess.run(
            [sys.executable, "-m", "ragmaker.tools.github_fetch"] + args,
            capture_output=True,
            text=False, # Get raw bytes to handle encoding manually
            env=env
        )
        # On Windows, stderr/stdout might be cp932. Try utf-8 first, fallback to cp932.
        def decode_output(b):
            if not b: return ""
            try:
                return b.decode('utf-8')
            except UnicodeDecodeError:
                return b.decode('cp932', errors='replace')

        stdout = decode_output(process.stdout)
        stderr = decode_output(process.stderr)
        return process.returncode, stdout, stderr

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


        returncode, stdout, stderr = self.run_tool([
            "--repo-url", repo_url,
            "--path-in-repo", path_in_repo,
            "--temp-dir", str(output_dir),
            "--branch", self.main_branch,
            "--log-level", "DEBUG"
        ])

        self.assertEqual(returncode, 0, f"Script failed with stderr: {stderr}")

        # Check that output directory and files exist
        self.assertTrue(output_dir.exists())
        converted_md = output_dir / path_in_repo / "test.md"
        copied_txt = output_dir / path_in_repo / "plain.txt"
        original_html = output_dir / path_in_repo / "test.html"

        self.assertTrue(converted_md.exists(), f"Markdown file was not created. Stderr: {stderr}")
        self.assertTrue(copied_txt.exists(), "Text file was not copied.")
        self.assertFalse(original_html.exists(), "Original HTML file should not be present.")

        # Check JSON output
        try:
            stdout_json = json.loads(stdout)
        except json.JSONDecodeError:
            self.fail(f"Stdout was not valid JSON.\nStdout: {stdout}\nStderr: {stderr}")

        self.assertEqual(len(stdout_json["documents"]),
 2)

    def test_fetch_and_stdout_json(self):
        """
        Test that github_fetch can fetch from a local repo
        and prints the discovery JSON to stdout.
        """
        output_dir = Path(self.test_dir.name) / "output"
        self.assertFalse(output_dir.exists())

        repo_url = self.repo_dir.as_uri()
        path_in_repo = "docs"

        returncode, stdout, stderr = self.run_tool([
            "--repo-url", repo_url,
            "--path-in-repo", path_in_repo,
            "--temp-dir", str(output_dir),
            "--branch", self.main_branch
        ])

        self.assertEqual(returncode, 0, f"github_fetch.py script failed with stderr: {stderr}")
        self.assertTrue(output_dir.exists())
        self.assertTrue((output_dir / "docs" / "test_file.md").exists())
        
        # Verify automatic saving of catalog.json
        discovery_file = output_dir / "catalog.json"
        self.assertTrue(discovery_file.exists(), "catalog.json was not automatically saved.")
        with open(discovery_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(len(saved_data["documents"]),
 1)

        try:
            stdout_json = json.loads(stdout)
        except json.JSONDecodeError:
            self.fail(f"Stdout was not valid JSON.\nStdout: {stdout}")

        self.assertIn("documents", stdout_json)
        self.assertEqual(len(stdout_json["documents"]),
 1)
        self.assertEqual(stdout_json["documents"][0]["path"], "docs/test_file.md")

    def test_fetch_root_directory(self):
        """
        Test that github_fetch can fetch from the root of a local repo.
        """
        output_dir = Path(self.test_dir.name) / "output_root"
        repo_url = self.repo_dir.as_uri()
        path_in_repo = "."

        returncode, stdout, stderr = self.run_tool([
            "--repo-url", repo_url,
            "--path-in-repo", path_in_repo,
            "--temp-dir", str(output_dir),
            "--branch", self.main_branch
        ])

        self.assertEqual(returncode, 0, f"Script failed with stderr: {stderr}")
        self.assertTrue((output_dir / "README.md").exists())
        self.assertTrue((output_dir / "docs" / "test_file.md").exists())

        stdout_json = json.loads(stdout)
        paths = {doc["path"] for doc in stdout_json["documents"]}
        self.assertIn("README.md", paths)
        self.assertIn("docs/test_file.md", paths)

    def test_fetch_single_file_path(self):
        """
        Test that github_fetch can fetch a single file path correctly
        without creating a directory conflict.
        """
        output_dir = Path(self.test_dir.name) / "output_single_file"
        repo_url = self.repo_dir.as_uri()
        path_in_repo = "README.md" # Root file

        returncode, stdout, stderr = self.run_tool([
            "--repo-url", repo_url,
            "--path-in-repo", path_in_repo,
            "--temp-dir", str(output_dir),
            "--branch", self.main_branch
        ])

        self.assertEqual(returncode, 0, f"Script failed with stderr: {stderr}")
        self.assertTrue((output_dir / "README.md").exists())
        self.assertTrue((output_dir / "README.md").is_file())
        self.assertFalse((output_dir / "README.md").is_dir())

        stdout_json = json.loads(stdout)
        self.assertEqual(len(stdout_json["documents"]), 1)
        self.assertEqual(stdout_json["documents"][0]["path"], "README.md")


if __name__ == '__main__':
    unittest.main()
