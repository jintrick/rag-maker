import unittest
from unittest.mock import patch
import sys
import os
from pathlib import Path

# Add src to path to allow importing ragmaker and its dependencies
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools.github_fetch import github_fetch
from git import GitCommandError

class TestGitHubFetchError(unittest.TestCase):

    @patch('ragmaker.tools.github_fetch.Repo')
    def test_clone_fallback_failure(self, mock_repo):
        """
        Test that a RuntimeError is raised when both shallow and full clones fail.
        """
        # Arrange
        repo_url = "https://github.com/example/repo.git"
        path_in_repo = "docs"
        temp_dir = Path("/tmp/test_dir")

        # Configure the mock to raise GitCommandError
        shallow_error = GitCommandError(["clone", "--depth", "1"], 128, stderr="shallow clone failed")
        full_error = GitCommandError(["clone"], 128, stderr="full clone failed")

        mock_repo.clone_from.side_effect = [shallow_error, full_error]

        # Act & Assert
        with self.assertRaises(RuntimeError) as cm:
            github_fetch(repo_url, path_in_repo, temp_dir)

        # Check the error message
        # The expected message should contain the details of the final exception
        self.assertIn("Full clone also failed after shallow clone attempt:", str(cm.exception))
        self.assertIn("full clone failed", str(cm.exception))

        # Check that the cause is preserved
        self.assertIs(cm.exception.__cause__, full_error)

if __name__ == '__main__':
    unittest.main()
