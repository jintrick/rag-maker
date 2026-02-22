
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
import tempfile
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import browser_open, browser_navigate, browser_extract
from ragmaker.browser_manager import BrowserManager

class TestBrowserPiloting(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.catalog_path = Path(".tmp/cache/catalog.json")
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        # Clean catalog if exists
        if self.catalog_path.exists():
            self.catalog_path.unlink()

    def tearDown(self):
        self.temp_dir.cleanup()
        if self.catalog_path.exists():
            self.catalog_path.unlink()

    @patch('ragmaker.tools.browser_open.BrowserManager')
    @patch('ragmaker.tools.browser_open.sys.stderr')
    @patch('ragmaker.tools.browser_open.print_json_stdout')
    async def test_browser_open_headless(self, mock_print, mock_stderr, MockBrowserManager):
        # Mock args
        with patch('ragmaker.tools.browser_open.GracefulArgumentParser.parse_args',
                   return_value=argparse.Namespace(no_headless=False)):
            await browser_open.main_async()

            # Check output
            mock_print.assert_called_with({
                "status": "success",
                "profile_path": ".tmp/cache/browser_profile"
            })
            # Check BrowserManager was NOT called (headless mode only inits dir)
            MockBrowserManager.assert_not_called()

    @patch('ragmaker.tools.browser_open.BrowserManager')
    @patch('ragmaker.tools.browser_open.sys.stderr')
    @patch('ragmaker.tools.browser_open.print_json_stdout')
    @patch('ragmaker.tools.browser_open.asyncio.get_event_loop') # To mock readline
    async def test_browser_open_no_headless(self, mock_loop, mock_print, mock_stderr, MockBrowserManager):
        # Mock BrowserManager context manager
        mock_instance = MagicMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_instance.context.new_page = AsyncMock()
        MockBrowserManager.return_value = mock_instance

        # Mock readline
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=b"\n")

        with patch('ragmaker.tools.browser_open.GracefulArgumentParser.parse_args',
                   return_value=argparse.Namespace(no_headless=True)):
            await browser_open.main_async()

            MockBrowserManager.assert_called_with(user_data_dir=Path(".tmp/cache/browser_profile"), headless=False)
            mock_instance.context.new_page.assert_called_once()

    @patch('ragmaker.tools.browser_navigate.BrowserManager')
    @patch('ragmaker.tools.browser_navigate.print_json_stdout')
    async def test_browser_navigate(self, mock_print, MockBrowserManager):
        mock_instance = MagicMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        # Mock navigate return
        mock_page = MagicMock()
        mock_page.url = "http://example.com"
        mock_instance.navigate = AsyncMock(return_value=(mock_page, False)) # page, is_bot_detected

        # Mock extract
        mock_instance.extract_links_and_title = AsyncMock(return_value={
            "links": [{"text": "Link", "href": "http://link.com"}],
            "title": "Title"
        })

        MockBrowserManager.return_value = mock_instance

        with patch('ragmaker.tools.browser_navigate.GracefulArgumentParser.parse_args',
                   return_value=argparse.Namespace(url="http://example.com", no_headless=False)):
            await browser_navigate.main_async()

            mock_instance.navigate.assert_called_with("http://example.com")
            mock_instance.extract_links_and_title.assert_called_with(mock_page)

            mock_print.assert_called_with({
                "status": "success",
                "url": "http://example.com",
                "title": "Title",
                "links": [{"text": "Link", "href": "http://link.com"}],
                "is_bot_detected": False
            })

    @patch('ragmaker.tools.browser_extract.BrowserManager')
    @patch('ragmaker.tools.browser_extract.print_json_stdout')
    async def test_browser_extract(self, mock_print, MockBrowserManager):
        mock_instance = MagicMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        mock_page = MagicMock()
        mock_instance.navigate = AsyncMock(return_value=(mock_page, False))

        mock_instance.extract_content = AsyncMock(return_value=("# Title\nContent", "Title"))

        MockBrowserManager.return_value = mock_instance

        with patch('ragmaker.tools.browser_extract.GracefulArgumentParser.parse_args',
                   return_value=argparse.Namespace(
                       url="http://example.com",
                       output_dir=str(self.output_dir),
                       no_headless=False)):
            await browser_extract.main_async()

            mock_instance.navigate.assert_called_with("http://example.com")

            # Check file creation
            files = list(self.output_dir.glob("*.md"))
            self.assertEqual(len(files), 1)
            with open(files[0], 'r') as f:
                self.assertEqual(f.read(), "# Title\nContent")

            # Check catalog update
            with open(self.catalog_path, 'r') as f:
                data = json.load(f)
                self.assertEqual(len(data['documents']), 1)
                self.assertEqual(data['documents'][0]['url'], "http://example.com")
                self.assertEqual(data['documents'][0]['title'], "Title")

if __name__ == '__main__':
    unittest.main()
