SAMPLE = '''\
import functools


def decorate(function):
    return function


class Outer(Base):
    """Outer docs."""

    @property
    def size(self):
        """Size docs."""
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

    @decorate
    @functools.wraps(decorate)
    def method(self, item: int) -> int:
        def inner():
            return item

        return inner()

    class Nested:
        def deep(self):
            pass


async def outer(count):
    """Outer function."""

    def inner():
        return count

    return inner()


def use():
    value = Outer()
    return value.method(1) + helper
'''

BROKEN = """\
def fine():
    return 1


def broken(:
    return 2
"""
