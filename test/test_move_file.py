import unittest
import subprocess
import tempfile
import os
import json
from pathlib import Path

class TestMoveFileTool(unittest.TestCase):

    def test_move_file_success(self):
        """Test that move_file successfully moves a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            source_path = temp_dir_path / "source.txt"
            dest_path = temp_dir_path / "destination.txt"
            test_content = "move me"

            # Create the source file
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(test_content)

            # Pre-conditions
            self.assertTrue(source_path.exists())
            self.assertFalse(dest_path.exists())

            # Run the move_file tool
            process = subprocess.run(
                [
                    "python", "-m", "src.ragmaker.tools.move_file",
                    "--source", str(source_path),
                    "--destination", str(dest_path)
                ],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            # Check for success
            self.assertEqual(process.returncode, 0, f"Tool exited with error: {process.stderr}")
            try:
                stdout_json = json.loads(process.stdout)
                self.assertEqual(stdout_json["status"], "success")
            except (json.JSONDecodeError, KeyError):
                self.fail(f"Failed to parse stdout JSON: {process.stdout}")

            # Verify the move
            self.assertFalse(source_path.exists())
            self.assertTrue(dest_path.exists())
            with open(dest_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertEqual(content, test_content)

    def test_move_file_creates_dest_dir(self):
        """Test that move_file creates the destination directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            source_path = temp_dir_path / "source.txt"
            nested_dir = temp_dir_path / "new" / "nested"
            dest_path = nested_dir / "destination.txt"
            test_content = "move me to a new place"

            # Create the source file
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(test_content)

            # Pre-conditions
            self.assertTrue(source_path.exists())
            self.assertFalse(nested_dir.exists())

            # Run the move_file tool
            process = subprocess.run(
                [
                    "python", "-m", "src.ragmaker.tools.move_file",
                    "--source", str(source_path),
                    "--destination", str(dest_path)
                ],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            # Check for success
            self.assertEqual(process.returncode, 0, f"Tool exited with error: {process.stderr}")

            # Verify the move and directory creation
            self.assertFalse(source_path.exists())
            self.assertTrue(nested_dir.exists())
            self.assertTrue(dest_path.exists())
            with open(dest_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertEqual(content, test_content)

    def test_move_file_source_not_found(self):
        """Test that move_file fails gracefully if the source file does not exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            source_path = temp_dir_path / "non_existent_source.txt"
            dest_path = temp_dir_path / "destination.txt"

            # Run the move_file tool
            process = subprocess.run(
                [
                    "python", "-m", "src.ragmaker.tools.move_file",
                    "--source", str(source_path),
                    "--destination", str(dest_path)
                ],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            # Check for failure
            self.assertNotEqual(process.returncode, 0)
            try:
                stderr_json = json.loads(process.stderr)
                self.assertEqual(stderr_json["status"], "error")
                self.assertIn("Source file not found", stderr_json["message"])
            except (json.JSONDecodeError, KeyError):
                self.fail(f"Failed to parse stderr JSON: {process.stderr}")


if __name__ == '__main__':
    unittest.main()
