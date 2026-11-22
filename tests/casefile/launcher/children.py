"""Runs one child process to its end and reports what it printed."""

import asyncio
from asyncio.subprocess import PIPE
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

TIME_LIMIT = 120


@dataclass(slots=True, kw_only=True, frozen=True)
class Finished:
    code: int | None
    out: str
    err: str


@dataclass(slots=True, kw_only=True, frozen=True)
class ChildRunner:
    cwd: Path
    env: Mapping[str, str] | None = None

    async def wait(self, command: tuple[str, ...], stdin: str) -> Finished:
        child = await asyncio.create_subprocess_exec(
            *command, cwd=self.cwd, env=self.env, stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        async with asyncio.timeout(TIME_LIMIT):
            out, err = await child.communicate(stdin.encode())
        return Finished(code=child.returncode, out=out.decode(), err=err.decode())

    def run(self, *command: str, stdin: str = '') -> Finished:
        return asyncio.run(self.wait(command, stdin))
