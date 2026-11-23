"""Code navigation for the red-thread plugin."""

import sys

from red_thread_navigate.cli import run

__all__ = ['main']


def main(argv: list[str] | None = None) -> int:
    """Runs the navigate command line and returns its exit code."""
    return run(sys.argv[1:] if argv is None else argv)
