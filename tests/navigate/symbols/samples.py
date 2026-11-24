"""Source text for the backend tests, and a directory of source files for the verb tests."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, kw_only=True, frozen=True)
class SourceDir:
    root: Path

    def write(self, name: str, text: str) -> Path:
        target = self.root.joinpath(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target


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
        self.count += 1
        return self.kept
"""

TYPESCRIPT_SAMPLE = """\
interface Shape {
  area(): number;
}

type Id = string | number;

enum Color {
  Red,
  Green,
}

class Circle implements Shape {
  area(): number {
    return 1;
  }
}

function build(value: string): string;
function build(value: number): string;
function build(value: string | number): string {
  return String(value);
}

const arrow = (x: number): number => x + 1;

export class Store {
  put(key: string): void;
  put(key: number): void;
  put(key: string | number): void {}
}
"""

TSX_SAMPLE = """\
function Greeting(props: { name: string }) {
  return <h1>{props.name}</h1>;
}

const Badge = (props: { label: string }) => <span>{props.label}</span>;

export default function Page() {
  return <Greeting name="x" />;
}
"""

GO_SAMPLE = """\
package shapes

const Pi = 3

type Shape interface {
	Area() float64
}

type Circle struct {
	Radius float64
}

type ID string

func (c Circle) Area() float64 {
	return Pi
}

func Build() Circle {
	return Circle{}
}

func (c *Circle) Grow() {
	c.Radius++
}
"""

TERRAFORM_SAMPLE = """\
variable "region" {
  type = string
}

locals {
  name = "app-${var.region}"
  tags = { Name = local.name }
}

data "aws_ami" "x" {
  most_recent = true
}

resource "aws_vpc" "this" {
  cidr_block = "10.0.0.0/16"
  tags       = local.tags
}

module "vpc" {
  source = "./vpc"
  ami    = data.aws_ami.x.id
}

output "id" {
  value = aws_vpc.this.id
}
"""

TERRAFORM_BROKEN = """\
resource "aws_vpc" "this" {
  cidr_block =
}

variable "region" {
"""

RUST_SAMPLE = """\
use std::fmt;

const LIMIT: u32 = 3;

struct Wrapper<T> {
    inner: T,
}

enum Color {
    Red,
}

trait Shape {
    fn area(&self) -> f64;
}

impl<T> Wrapper<T> {
    fn new(inner: T) -> Self {
        Wrapper { inner }
    }
}

impl fmt::Display for Color {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        Ok(())
    }
}

impl fmt::Debug for Color {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        Ok(())
    }
}

impl Shape for &Color {
    fn area(&self) -> f64 {
        0.0
    }
}

fn build() -> u32 {
    LIMIT
}
"""
