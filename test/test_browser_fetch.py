import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
import tempfile
from pathlib import Path
import argparse
import asyncio

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import browser_fetch

class TestBrowserFetchTool(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.args = argparse.Namespace(
            url="http://example.com",
            base_url="http://example.com",
            output_dir=str(self.output_dir),
            recursive=False,
            depth=1,
            no_headless=False,
            verbose=False,
            log_level='INFO'
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('ragmaker.tools.browser_fetch.BrowserManager')
    async def test_fetch_content(self, MockBrowserManager):
        # Mock BrowserManager structure
        mock_instance = MagicMock()

        # Async context manager mocking
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        MockBrowserManager.return_value = mock_instance

        mock_page = MagicMock()
        mock_page.close = AsyncMock() # Ensure close is async

        mock_instance.navigate = AsyncMock(return_value=(mock_page, False))
        mock_instance.extract_content = AsyncMock(return_value=("# Test Title\nTest content.", "Test Page"))

        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        # Verify results
        self.assertEqual(len(fetcher.documents), 1)
        self.assertEqual(fetcher.documents[0]['url'], "http://example.com")
        self.assertEqual(fetcher.documents[0]['title'], "Test Page")

        # Verify calls
        mock_instance.navigate.assert_called_with("http://example.com")
        mock_instance.extract_content.assert_called_with(mock_page)

        # Check file content
        file_path = self.output_dir / fetcher.documents[0]['path']
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("# Test Title", content)
        self.assertIn("Test content", content)

    @patch('ragmaker.tools.browser_fetch.BrowserManager')
    async def test_recursion(self, MockBrowserManager):
        # Mock BrowserManager
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        MockBrowserManager.return_value = mock_instance

        mock_page = MagicMock()
        mock_page.close = AsyncMock()

        # Side effect for navigate
        mock_instance.navigate = AsyncMock(return_value=(mock_page, False))

        # Side effect for extract_content
        mock_instance.extract_content = AsyncMock(side_effect=[
            ("# Root\nRoot content", "Root"),
            ("# Sub\nSub content", "Sub")
        ])

        # Side effect for extract_links_and_title
        mock_instance.extract_links_and_title = AsyncMock(side_effect=[
            {"links": [{"href": "http://example.com/sub"}], "title": "Root"},
            {"links": [], "title": "Sub"}
        ])

        args = argparse.Namespace(
            url="http://example.com",
            base_url="http://example.com",
            output_dir=str(self.output_dir),
            recursive=True,
            depth=2,
            no_headless=False,
            verbose=False,
            log_level='INFO'
        )

        fetcher = browser_fetch.WebFetcher(args)
        await fetcher.run()

        # Verify that it visited http://example.com and http://example.com/sub
        visited = fetcher.visited_urls
        self.assertIn("http://example.com", visited)
        self.assertIn("http://example.com/sub", visited)
        self.assertEqual(len(fetcher.documents), 2)

if __name__ == '__main__':
    unittest.main()
