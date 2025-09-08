# -*- coding: utf-8 -*-
"""
io_utils.py - I/O and Error Handling Utilities for RAGMaker.

This module provides centralized functions for handling command-line arguments,
structured error reporting, and standard stream I/O to ensure consistency
and robustness across all tools in the application.
"""

import sys
import json
import argparse
from typing import Any

# --- Custom Exception and ArgumentParser ---

class ArgumentParsingError(Exception):
    """Custom exception for argument parsing errors."""

class GracefulArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises a custom exception on error."""
    def error(self, message: str):
        """
        Handles parsing errors by raising a custom exception instead of exiting.

        Args:
            message (str): The error message from argparse.

        Raises:
            ArgumentParsingError: Always raised with the provided message.
        """
        raise ArgumentParsingError(message)


# --- Structured I/O Functions ---

def print_json_stdout(data: dict[str, Any]):
    """
    Prints a dictionary as a JSON string to standard output, handling encoding.

    This function ensures that the output is correctly encoded as UTF-8
    before being written to the standard output buffer. This avoids
    UnicodeEncodeError on Windows environments where the default encoding
    might be 'cp932'.

    Args:
        data (dict[str, Any]): The dictionary to be printed as JSON.
    """
    try:
        json_string = json.dumps(data, ensure_ascii=False, indent=2)
        sys.stdout.buffer.write(json_string.encode('utf-8'))
    except Exception as e:
        # Fallback for environments where buffer writing might fail
        fallback_data = {"status": "error", "message": "Failed to write to stdout buffer", "details": str(e)}
        print(json.dumps(fallback_data, ensure_ascii=False))

def eprint_error(data: dict[str, Any]):
    """
    Prints a dictionary as a JSON string to standard error, handling encoding.

    This function ensures UTF-8 encoding for error messages, preventing
    potential encoding errors on Windows. It serves as the primary function
    for reporting structured errors. It checks for a `buffer` attribute
    on stderr to support streams that don't have one (like test mocks).

    Args:
        data (dict[str, Any]): The error dictionary to be printed as JSON.
    """
    json_string = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        # Prefer writing to the buffer to handle encoding correctly
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr.buffer.write(json_string.encode('utf-8'))
        else:
            # Fallback for streams without a buffer (e.g., io.StringIO in tests)
            sys.stderr.write(json_string)
    except Exception as e:
        # A final, desperate fallback in case all writing methods fail.
        print(f"FATAL: Could not write to stderr. Original error: {data}. New error: {e}")


# --- Common Error Handlers ---

def handle_argument_parsing_error(exception: Exception):
    """
    Handles argument parsing errors by printing a structured JSON error.

    Args:
        exception (Exception): The exception caught during argument parsing.
    """
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "Failed to parse command-line arguments.",
        "remediation_suggestion": (
            "Review the command-line parameters and ensure all required "
            "arguments are provided correctly."
        ),
        "details": {"original_error": str(exception)}
    })

def handle_unexpected_error(exception: Exception):
    """
    Handles unexpected errors by printing a structured JSON error.

    Args:
        exception (Exception): The unexpected exception that was caught.
    """
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred during processing.",
        "remediation_suggestion": "Check the input and environment, then try again.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })
