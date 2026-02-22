#!/usr/bin/env python3
"""
Tool to explicitly close the browser session (cleanup).
"""

import sys
import logging
import argparse
import json
import os
import signal
from pathlib import Path

# Suppress logging
logging.disable(logging.CRITICAL)

try:
    from ragmaker.io_utils import (
        print_json_stdout,
        GracefulArgumentParser,
        ArgumentParsingError,
        handle_argument_parsing_error,
        handle_unexpected_error
    )
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

logger = logging.getLogger(__name__)

def main():
    logging.disable(logging.NOTSET)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    parser = GracefulArgumentParser(description="Close the browser session.")

    try:
        args = parser.parse_args()

        cdp_file = Path(".tmp/browser_cdp.json")
        if not cdp_file.exists():
            print_json_stdout({
                "status": "success",
                "message": "No active browser session found."
            })
            return

        try:
            with open(cdp_file, 'r') as f:
                data = json.load(f)
                pid = data.get("pid")
        except Exception as e:
            logger.warning(f"Failed to read CDP file: {e}")
            pid = None

        if pid:
            try:
                # Terminate process
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                # Already gone
                pass
            except OSError as e:
                logger.warning(f"Failed to kill browser process {pid}: {e}")

        try:
            cdp_file.unlink()
        except OSError:
            pass

        print_json_stdout({
            "status": "success",
            "message": "Browser session closed."
        })

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
