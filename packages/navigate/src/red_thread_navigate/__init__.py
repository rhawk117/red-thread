"""Code navigation for the red-thread plugin."""

import sys
from importlib.metadata import version

__all__ = ['main']


def main(argv: list[str] | None = None) -> int:
    """Runs the navigate command line and returns its exit code."""
    args = sys.argv[1:] if argv is None else argv
    if args == ['--version']:
        print(f'red-thread-navigate {version("red-thread-navigate")}')
        return 0
    print('usage: red-thread-navigate --version', file=sys.stderr)
    return 2
