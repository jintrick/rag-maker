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

    @patch('ragmaker.tools.browser_fetch.async_playwright')
    async def test_fetch_content(self, mock_playwright):
        # Mock Playwright structure
        mock_p = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        # Correctly setup AsyncMocks for async methods
        mock_playwright.return_value.start = AsyncMock(return_value=mock_p)
        # Use launch_persistent_context instead of launch/new_context
        mock_p.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_p.stop = AsyncMock()
        mock_context.close = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.add_init_script = AsyncMock()

        # Mocks for bot detection check
        mock_page.title = AsyncMock(return_value="Safe Title")
        mock_page.content = AsyncMock(return_value="Safe content")
        mock_page.query_selector = AsyncMock(return_value=None)

        # Mock page.evaluate return value
        mock_page.evaluate = AsyncMock(return_value={
            "html": "<html><body><h1>Test Title</h1><p>Test content.</p></body></html>",
            "links": ["http://example.com/page2"],
            "title": "Test Page"
        })

        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        # Verify results
        self.assertEqual(len(fetcher.documents), 1)
        self.assertEqual(fetcher.documents[0]['url'], "http://example.com")

        # Verify launch_persistent_context was called
        mock_p.chromium.launch_persistent_context.assert_called_once()

        # Verify stealth script was added
        mock_page.add_init_script.assert_called()

        # Check file content
        file_path = self.output_dir / fetcher.documents[0]['path']
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("# Test Title", content)
        self.assertIn("Test content", content)

    @patch('ragmaker.tools.browser_fetch.async_playwright')
    async def test_recursion(self, mock_playwright):
        # Mock Playwright
        mock_p = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        # Correctly setup AsyncMocks
        mock_playwright.return_value.start = AsyncMock(return_value=mock_p)
        mock_p.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_p.stop = AsyncMock()
        mock_context.close = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.add_init_script = AsyncMock()

        # Mocks for bot detection check
        mock_page.title = AsyncMock(return_value="Safe Title")
        mock_page.content = AsyncMock(return_value="Safe content")
        mock_page.query_selector = AsyncMock(return_value=None)

        # Define behavior for recursion
        # First call returns link to sub
        # Second call returns content

        mock_page.evaluate = AsyncMock(side_effect=[
            {
                "html": "<p>Root</p>",
                "links": ["http://example.com/sub"],
                "title": "Root"
            },
            {
                "html": "<p>Sub</p>",
                "links": [],
                "title": "Sub"
            }
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
