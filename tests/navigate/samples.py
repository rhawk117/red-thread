"""Sources, budgets and the navigator that the verb tests share."""

from red_thread_navigate.cli import create_navigator
from red_thread_navigate.slice import WINDOW_LINES

BIG_BUDGET = 10_000
NAVIGATOR = create_navigator()
CORE = """\
def helper():
    return 1


class Widget:
    def render(self):
        return helper()
"""
CLIENT = """\
from core import helper


def run():
    helper()
    helper()
"""


def long_class() -> str:
    body = '\n'.join(f'        total += {number}' for number in range(WINDOW_LINES))
    return (
        'class Big:\n'
        '    """A long class."""\n\n'
        '    def first(self):\n'
        f'        total = 0\n{body}\n'
        '        return total\n\n'
        '    def second(self):\n'
        '        return 2\n'
    )
