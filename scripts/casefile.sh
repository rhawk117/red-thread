#!/bin/sh
# Runs the red-thread case file command line with Python 3.14 from uv.
# uv supplies msgspec, the package's one dependency, from its cache, so nothing is installed
# into the project. The first run on a machine downloads it.
set -eu

here=$(cd -- "$(dirname -- "$0")" && pwd -P)
root=${CLAUDE_PLUGIN_ROOT:-${here%/*}}

export PYTHONPATH="${root}/packages/casefile/src"
export PYTHONDONTWRITEBYTECODE=1
exec uv run --no-project --python 3.14 --with 'msgspec>=0.22' -- python -m red_thread_casefile "$@"
