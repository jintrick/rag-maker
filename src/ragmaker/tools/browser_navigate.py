#!/usr/bin/env python3
"""
Tool to navigate to a URL using a persistent browser context.
Extracts links and title, handling bot detection appropriately.
"""

import sys
import argparse
import asyncio
import logging
from pathlib import Path

# Suppress logging for clean JSON output
logging.disable(logging.CRITICAL)

try:
    from ragmaker.io_utils import (
        ArgumentParsingError,
        GracefulArgumentParser,
        eprint_error,
        handle_argument_parsing_error,
        handle_unexpected_error,
        print_json_stdout,
    )
    from ragmaker.browser_manager import BrowserManager, FatalBrowserError
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

logger = logging.getLogger(__name__)

async def main_async():
    # Re-enable logging for execution to stderr
    logging.disable(logging.NOTSET)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Navigate to a URL and extract links using persistent browser context.")
    parser.add_argument("--url", required=True, help="URL to navigate to.")
    parser.add_argument("--no-headless", action="store_true", help="Run browser visibly to allow manual interaction if needed.")

    try:
        args = parser.parse_args()
        profile_path = Path(".tmp/cache/browser_profile")

        async with BrowserManager(user_data_dir=profile_path, headless=not args.no_headless) as browser:
            page, is_bot_detected = await browser.navigate(args.url)

            # Extract info even if bot detected (might be partial or incorrect, but let agent decide)
            info = await browser.extract_links_and_title(page)

            output = {
                "status": "success",
                "url": page.url,
                "title": info['title'],
                "links": info['links'],
                "is_bot_detected": is_bot_detected
            }
            print_json_stdout(output)

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except FatalBrowserError as e:
        logger.error(f"Fatal browser error: {e}")
        eprint_error({
            "status": "error",
            "error_code": "FATAL_BROWSER_ERROR",
            "message": str(e)
        })
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
