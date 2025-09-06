import unittest
import subprocess
import tempfile
import shutil
from pathlib import Path
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

        # Add and commit the file
        self.repo.index.add(["docs/test_file.md"])
        self.repo.index.commit("Initial commit")

    def tearDown(self):
        """Clean up the temporary directory."""
        self.repo.close()
        self.test_dir.cleanup()

    def test_local_repo_fetch_and_dir_creation(self):
        """
        Test that github_fetch.py can fetch from a local repo
        and creates the temp directory if it does not exist.
        """
        output_dir = Path(self.test_dir.name) / "output"
        self.assertFalse(output_dir.exists())

        # Use the local repository with the file:// protocol
        repo_url = f"file://{self.repo_dir}"
        path_in_repo = "docs"

        process = subprocess.run(
            [
                "ragmaker-github-fetch",
                "--repo-url", repo_url,
                "--path-in-repo", path_in_repo,
                "--temp-dir", str(output_dir)
            ],
            capture_output=True,
            text=True
        )

        if process.returncode != 0:
            print("GitHubFetch STDERR:", process.stderr)

        self.assertEqual(process.returncode, 0, "github_fetch.py script failed")

        # The tool should create the directory.
        self.assertTrue(output_dir.exists())
        # And it should contain the fetched file.
        self.assertTrue((output_dir / "docs" / "test_file.md").exists())

if __name__ == '__main__':
    unittest.main()
