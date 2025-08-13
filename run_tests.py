#!/usr/bin/env python3
"""Test runner script for the Neurosetta GUI application."""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", coverage=False, verbose=False):
    """Run tests with specified options.
    
    Args:
        test_type: Type of tests to run ('unit', 'integration', 'all')
        coverage: Whether to generate coverage report
        verbose: Whether to run in verbose mode
    """
    # Add src directory to Python path
    src_path = Path(__file__).parent / "src"
    os.environ["PYTHONPATH"] = str(src_path) + ":" + os.environ.get("PYTHONPATH", "")
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test path based on type
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # Add coverage options
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    # Add verbose option
    if verbose:
        cmd.append("-v")
    
    # Add markers
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Neurosetta GUI tests")
    parser.add_argument(
        "--type", "-t",
        choices=["unit", "integration", "all"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print("Neurosetta GUI Test Runner")
    print("=" * 40)
    print(f"Test type: {args.type}")
    print(f"Coverage: {'Yes' if args.coverage else 'No'}")
    print(f"Verbose: {'Yes' if args.verbose else 'No'}")
    print("=" * 40)
    
    return run_tests(args.type, args.coverage, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
