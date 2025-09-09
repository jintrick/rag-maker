import unittest
from unittest.mock import patch, mock_open
import sys
import io
import json
import os
import tempfile
from pathlib import Path
import http.server
import socketserver
import threading
import time

# Add the src directory to the Python path to allow for direct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import http_fetch

# --- Test Setup ---

PORT = 8000
TEST_DIR = Path(__file__).parent.resolve()
FIXTURES_DIR = TEST_DIR / "fixtures"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FIXTURES_DIR), **kwargs)

    def log_message(self, format, *args):
        pass # Suppress log messages

class TestHttpFetchTool(unittest.TestCase):

    _httpd = None
    _server_thread = None

    @classmethod
    def setUpClass(cls):
        socketserver.TCPServer.allow_reuse_address = True
        cls._httpd = socketserver.TCPServer(("", PORT), QuietHandler)
        cls._server_thread = threading.Thread(target=cls._httpd.serve_forever)
        cls._server_thread.daemon = True
        cls._server_thread.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        if cls._httpd:
            cls._httpd.shutdown()
            cls._httpd.server_close()
        if cls._server_thread:
            cls._server_thread.join(timeout=2)

    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def run_tool(self, args: list[str], mock_stdout, mock_stderr):
        """Helper method to run the tool with mocked argv, stdout, and stderr."""
        with patch.object(sys, 'argv', ['http_fetch.py'] + args):
            try:
                http_fetch.main()
            except SystemExit as e:
                # The tool calls sys.exit() on completion/error, catch it
                pass
        return mock_stdout.getvalue(), mock_stderr.getvalue()

    def test_fetch_local_page_and_verify_content(self):
        """
        Test fetching a local HTML file, converting it to Markdown,
        and verifying the content and output JSON.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "fetch_output"
            url = f"http://localhost:{PORT}/sample_page.html"

            args = [
                "--url", url,
                "--base-url", f"http://localhost:{PORT}/",
                "--output-dir", str(output_dir),
                "--no-recursive",
                "--log-level", "ERROR"
            ]

            # Run the tool
            stdout, stderr = self.run_tool(args)

            # Check for errors in stderr
            self.assertEqual(stderr.strip(), "", f"Tool printed to stderr unexpectedly: {stderr}")

            # Verify the stdout is a valid JSON
            try:
                stdout_json = json.loads(stdout)
            except json.JSONDecodeError:
                self.fail(f"Stdout was not valid JSON.\nStdout: {stdout}")

            # --- Assertions ---
            self.assertIn("documents", stdout_json)
            self.assertEqual(len(stdout_json["documents"]), 1)

            doc_info = stdout_json["documents"][0]
            md_file_path = output_dir / doc_info["path"]
            self.assertTrue(md_file_path.exists())

            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn("Main Content Title", content)
            self.assertNotIn("noisy ad banner", content)
            self.assertNotIn("Comments", content)
            self.assertNotIn("My News Site", content)

    @patch('shutil.which', return_value=None)
    def test_readability_cli_not_found(self, mock_which):
        """
        Test that the tool exits gracefully with an error if readable-cli is not found.
        """
        args = [
            "--url", "http://example.com",
            "--base-url", "http://example.com",
            "--output-dir", "dummy_dir"
        ]

        stdout, stderr = self.run_tool(args)

        self.assertEqual(stdout, "")
        self.assertNotEqual(stderr, "")

        stderr_json = json.loads(stderr)
        self.assertEqual(stderr_json["error_code"], "DEPENDENCY_ERROR")
        self.assertIn("'readable' command (from readability-cli) is not found", stderr_json["message"])


if __name__ == '__main__':
    unittest.main()
