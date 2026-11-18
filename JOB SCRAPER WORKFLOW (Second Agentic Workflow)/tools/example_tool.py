#!/usr/bin/env python3
"""
Example Tool Template

This tool demonstrates the structure for any deterministic tool in the WAT framework.
Each tool should do ONE thing reliably and return structured output.

Usage:
    python tools/example_tool.py --input data.csv --output result.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Example tool that does one thing well"
    )
    parser.add_argument("--input", required=True, help="Input file path or data")
    parser.add_argument("--output", required=False, help="Output file path (optional)")
    parser.add_argument(
        "--api-key",
        required=False,
        default=os.getenv("API_KEY"),
        help="API key (defaults to .env API_KEY)",
    )

    args = parser.parse_args()

    try:
        # Validate inputs
        if not args.input:
            raise ValueError("Input is required")

        # Do the actual work here
        result = process_data(args.input, args.api_key)

        # Output results (always JSON for consistency)
        output = {"status": "success", "data": result, "output_path": args.output}

        # Write to file if specified, else print to stdout
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)
            print(json.dumps(output))
        else:
            print(json.dumps(output))

        return 0

    except Exception as e:
        error_output = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
        }
        print(json.dumps(error_output), file=sys.stderr)
        return 1


def process_data(input_data: str, api_key: str = None) -> dict:
    """
    Do the actual work here.

    Args:
        input_data: The input (file path, text, URL, etc.)
        api_key: Optional API key for external services

    Returns:
        dict: Processed data
    """
    # Replace this with actual logic
    return {
        "processed": True,
        "input_length": len(input_data) if input_data else 0,
        "items_processed": 0,
    }


if __name__ == "__main__":
    sys.exit(main())
