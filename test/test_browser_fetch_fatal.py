import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import tempfile
from pathlib import Path
import argparse
import asyncio

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import browser_fetch

class TestBrowserFetchFatal(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.args = argparse.Namespace(
            url="http://example.com",
            base_url="http://example.com",
            output_dir=str(self.output_dir),
            recursive=True,
            depth=5,
            no_headless=False,
            verbose=False,
            log_level='INFO'
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('ragmaker.tools.browser_fetch.async_playwright')
    async def test_fatal_error_stops_crawl(self, mock_playwright):
        # Mock Playwright
        mock_p = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.start = AsyncMock(return_value=mock_p)
        mock_p.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_p.stop = AsyncMock()
        mock_context.close = AsyncMock()
        mock_page.close = AsyncMock()

        # Simulate successful first page, then fatal error on second page
        async def side_effect_goto(url, **kwargs):
            if url == "http://example.com":
                return # success
            elif url == "http://example.com/fatal":
                raise Exception("Target closed")
            return

        mock_page.goto = AsyncMock(side_effect=side_effect_goto)
        mock_page.add_init_script = AsyncMock()
        mock_page.title = AsyncMock(return_value="Safe Title")
        mock_page.content = AsyncMock(return_value="Safe content")
        mock_page.query_selector = AsyncMock(return_value=None)

        # Evaluate returns links on first page
        mock_page.evaluate = AsyncMock(side_effect=[
            {
                "html": "<p>Root</p>",
                "links": ["http://example.com/fatal"],
                "title": "Root"
            },
            # Second call shouldn't happen or will fail before evaluate if goto fails
        ])

        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        # Should have processed the first page
        self.assertEqual(len(fetcher.documents), 1)
        self.assertEqual(fetcher.documents[0]['url'], "http://example.com")

        # Verify that the fatal error broke the loop and we didn't try to visit anything else
        # (though in this simple case, there was nothing else to visit)

        # To strictly verify it stopped, we can check logs or just rely on the fact that it didn't crash.

    @patch('ragmaker.tools.browser_fetch.async_playwright')
    async def test_timeout_setting(self, mock_playwright):
        # Mock Playwright
        mock_p = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.start = AsyncMock(return_value=mock_p)
        mock_p.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_p.stop = AsyncMock()
        mock_context.close = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        mock_page.title = AsyncMock(return_value="Safe Title")
        mock_page.content = AsyncMock(return_value="Safe content")
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.evaluate = AsyncMock(return_value={
            "html": "<p>Content</p>",
            "links": [],
            "title": "Title"
        })

        # Test headless (default) -> timeout 60000
        self.args.no_headless = False
        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        mock_page.goto.assert_called_with("http://example.com", timeout=60000, wait_until="networkidle")

        # Reset mocks
        mock_page.goto.reset_mock()

        # Test no-headless -> timeout 0
        self.args.no_headless = True
        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        mock_page.goto.assert_called_with("http://example.com", timeout=0, wait_until="networkidle")

if __name__ == '__main__':
    unittest.main()
