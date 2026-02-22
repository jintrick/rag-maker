#!/usr/bin/env python3
"""
Tool to initialize the browser profile.
If --no-headless is specified, it opens the browser for manual interaction (e.g. login) and waits for user confirmation.
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
    from ragmaker.browser_manager import BrowserManager
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

logger = logging.getLogger(__name__)

async def main_async():
    # Re-enable logging for execution
    logging.disable(logging.NOTSET)
    # But keep it to stderr
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Initialize browser profile and optionally open browser for manual setup.")
    parser.add_argument("--no-headless", action="store_true", help="Open browser visibly and wait for user input.")

    try:
        args = parser.parse_args()

        profile_path = Path(".tmp/cache/browser_profile")
        profile_path.mkdir(parents=True, exist_ok=True)

        if args.no_headless:
            sys.stderr.write("[INFO] Opening browser for manual setup...\n")
            async with BrowserManager(user_data_dir=profile_path, headless=False) as browser:
                # Create a page so the browser window actually appears (context only might not show window until page created)
                await browser.context.new_page()

                sys.stderr.write("Browser is open. Please perform any necessary actions (e.g., login).\n")
                sys.stderr.write("Press ENTER in this terminal when finished to close the browser and save the session...\n")
                sys.stderr.flush()
                await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                sys.stderr.write("[INFO] Closing browser and saving session.\n")

        print_json_stdout({
            "status": "success",
            "profile_path": str(profile_path)
        })

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
