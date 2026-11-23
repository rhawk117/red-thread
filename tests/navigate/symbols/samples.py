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

JAVASCRIPT_SAMPLE = """\
class Widget {
  constructor(name) {
    this.name = name;
  }

  render() {
    return helper(this.name);
  }
}

function build() {
  return new Widget('a');
}

const arrow = (value) => value + 1;

const bound = function (value) {
  return arrow(value);
};

export class Exported {
  open() {
    return build().render();
  }
}

export function exportedFunction() {
  return 1;
}

export const exportedArrow = () => bound(2);
"""

MATCH_SAMPLE = """\
def route(command):
    match command:
        case 'go':
            def go():
                return 1

            return go
        case _:
            class Fallback:
                pass

            return Fallback
"""

LINE_BREAK_SAMPLE = (
    "x = '\x0c'\ny = '\x0b'\nz = '\u2028'\n\n\ndef later(value):\n    return value\n"
)

WRITE_SAMPLE = """\
class Box:
    def put(self, value):
        self._size = value
        del self.gone
        return self.kept
"""
