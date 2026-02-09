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
    Prints a dictionary as a JSON string to standard output.

    This function serializes the dictionary to a JSON string and prints it
    to standard output. The `print` function handles the necessary encoding
    based on the environment's locale settings (e.g., `sys.stdout.encoding`),
    which is generally a robust approach.

    Args:
        data (dict[str, Any]): The dictionary to be printed as JSON.
    """
    try:
        # ensure_ascii=True is critical for cross-platform/encoding compatibility.
        # It escapes all non-ASCII characters, making the output safe for any
        # text stream, including those expecting cp932.
        json_string = json.dumps(data, ensure_ascii=True, indent=2)
        print(json_string)
        sys.stdout.flush()
    except Exception as e:
        # Fallback in case of serialization errors.
        fallback_data = {
            "status": "error",
            "error_code": "JSON_SERIALIZATION_ERROR",
            "message": "Failed to serialize data to JSON for stdout.",
            "details": str(e)
        }
        print(json.dumps(fallback_data, ensure_ascii=True))
        sys.stdout.flush()

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

def handle_file_not_found_error(exception: FileNotFoundError):
    """Handles file not found errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "FILE_NOT_FOUND",
        "message": str(exception),
        "details": {"error_type": type(exception).__name__}
    })

def handle_io_error(exception: IOError):
    """Handles general I/O errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "IO_ERROR",
        "message": "An I/O error occurred while reading or writing a file.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })

def handle_value_error(exception: ValueError):
    """Handles value errors, often from parsing, by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "VALUE_ERROR",
        "message": "An invalid value was encountered.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })

def handle_command_execution_error(exception: Exception):
    """Handles errors from subprocess command execution."""
    eprint_error({
        "status": "error",
        "error_code": "COMMAND_EXECUTION_ERROR",
        "message": "A command failed to execute.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })
