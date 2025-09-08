import unittest
import subprocess
import tempfile
import shutil
import json
from pathlib import Path

class TestHttpFetchTool(unittest.TestCase):

    def test_fetch_single_page_and_stdout(self):
        """
        Test that http_fetch fetches a page and prints discovery JSON to stdout.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "fetch_output"
            # A real, simple, and reliable URL is needed.
            # Using a local file served via a simple server would be more robust,
            # but for this test, example.com is a reasonable choice.
            url = "http://example.com"

            # Run the http_fetch tool
            process = subprocess.run(
                [
                    "python", "-m", "src.ragmaker.tools.http_fetch",
                    "--url", url,
                    "--base-url", url,
                    "--output-dir", str(output_dir),
                    "--no-recursive" # Don't follow links for this simple test
                ],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            # Check for successful execution
            self.assertEqual(process.returncode, 0, f"Tool exited with error: {process.stderr}")

            # Verify the output directory and fetched file are still created
            self.assertTrue(output_dir.exists())
            html_files = list(output_dir.glob("*.html"))
            self.assertEqual(len(html_files), 1, "Expected one HTML file to be created")

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
            self.assertEqual(document_info["url"], url)
            self.assertEqual(document_info["path"], html_files[0].name)

            # Check metadata
            self.assertEqual(stdout_json["metadata"]["source"], "http_fetch")
            self.assertEqual(stdout_json["metadata"]["url"], url)


if __name__ == '__main__':
    unittest.main()
