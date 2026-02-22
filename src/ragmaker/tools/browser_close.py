#!/usr/bin/env python3
"""
Tool to explicitly close the browser session (cleanup).
Currently, browser context is closed after each tool execution, so this tool serves as a semantic end of session.
"""

import sys
import logging
import argparse

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
        # No actual cleanup needed as each tool invocation handles its own context closure.
        # Could potentially clear temporary files here if desired, but user_data_dir is persistent.

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
