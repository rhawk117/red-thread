#!/bin/sh
# Runs the red-thread code navigation command line with Python 3.14 from uv.
# uv installs the package from this plugin, editable, with the dependencies its pyproject.toml
# declares. The environment lives in uv's cache, so nothing is installed into the project under
# investigation and nothing is written into the plugin.
set -eu

here=$(cd -- "$(dirname -- "$0")" && pwd -P)
root=${CLAUDE_PLUGIN_ROOT:-${here%/*}}

export PYTHONDONTWRITEBYTECODE=1
exec uv run --no-config --no-project --python 3.14 --with-editable "${root}/packages/navigate" -- python -m red_thread_navigate "$@"
