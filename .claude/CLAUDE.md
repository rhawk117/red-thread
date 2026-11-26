# red-thread: agent instructions

red-thread is a Claude Code plugin for investigation with a human gate. The `investigate` skill runs research rounds through scouts and records what they find in a case file. The `distill` skill turns a case file into a brief, an issue, a handoff or a report. The `debug` skill takes a failure to a confirmed cause, a fix the owner approves and a decision on preventing it, and keeps its record in a case file. `docs/design.md` holds the design, the owner's decisions and the build status: read it before changing a skill, an agent or the case file format.

## Commands

Every command goes through `make`. Each target delegates to uv, prek or a script under `scripts/`.

- `make setup` installs the prek git hooks and syncs every workspace package and dependency group. A fresh clone has no git hook, so run it before the first commit.
- `make sync` syncs the workspace packages and dependency groups.
- `make format` runs the prek hooks in the `format` group on all files: the hygiene fixers, uv-lock, ruff fix and format, shfmt and mdformat.
- `make lint` runs the prek hooks in the `lint` group on all files: the hygiene checks, ruff check, ty and shellcheck.
- `make typecheck` runs ty alone.
- `make test` runs `pytest -q -m "unit or agents or smoke"`, with coverage.
- `make test.end-to-end` runs `pytest -q -m e2e`: the tests under `tests/casefile/launcher/e2e` and `tests/navigate/launcher/e2e`, which run `bin/redthread-casefile` and `bin/redthread-navigate` as child processes from a copy of the plugin.
- `make pre-commit` runs every prek hook in `.pre-commit-config.yaml` on all files.
- `make check` runs lint, then test.
- `make quality` runs every prek hook on all files, then `pytest -q -m "not integration"`, which matches CI's quality job.

## Stack

Python 3.14 (`requires-python` in `pyproject.toml`), uv, ruff, ty, pytest with Hypothesis, mdformat and prek. `packages/casefile` depends on msgspec. `packages/navigate` depends on tree-sitter and the grammar wheels for JavaScript, TypeScript, Go, Rust and Terraform (`tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-go`, `tree-sitter-rust` and `tree-sitter-hcl`), all pinned with `==`. `.github/workflows/ci.yml` sets up CI: `astral-sh/setup-uv` takes its uv version from the `UV_VERSION` repository variable, and `actions/setup-node` takes its Node version from the `NODE_VERSION` repository variable.

## Layout

- The plugin sits at the repository root, and `.claude-plugin/plugin.json` contains its manifest. The root `pyproject.toml` is both the plugin project and the uv workspace root, with members under `packages/`.
- `agents/` holds the six agent files: `research-lead` and `peer-review`, and the scouts `code-sense`, `code-lens`, `web-head` and `lab-rat` under `agents/swarm/`, which are dispatched as `red-thread:swarm:<name>`. Each is written for the model its frontmatter names. Check a change with `vibe-code subagent validate <file>`.
- `hooks/hooks.json` runs `hooks/roster.py`, a PEP 723 script, before every Agent call. It denies a red-thread agent's dispatch outside its roster. A new agent file needs an entry in that roster, and a test fails without one. Check a change with `vibe-code hook validate --strict hooks/hooks.json`.
- `skills/investigate/`, `skills/distill/` and `skills/debug/` hold the three user-facing skills. Each keeps its supporting files under `references/` (one per case kind, one per lens, and for `debug` the failure shapes and the escape analysis) and links every one of them from `SKILL.md`. `skills/agents/` holds three more skills that are not invocable and have no `references/`: `navigate`, preloaded into the agents that read code, and `meet-the-team`, which introduces the agents to whoever dispatches them, is preloaded into `research-lead` and is loaded by name from `investigate` and `debug`, and `artifact-authoring`, which says how to word an entry, a report, a gate summary, a distill title and a handoff, is preloaded into `research-lead` and is loaded by name from `investigate`, `debug` and `distill`. `plugin.json` lists `skills/agents/` under `skills` so that they load. Check a change with `vibe-code skill validate <skill directory>`.
- `packages/casefile` holds `red_thread_casefile`, the only writer and renderer of a case file. Its commands are `init`, `add`, `render`, `check`, `export` and `page`. The page's skeleton, styles, script and map header are in `packages/casefile/assets/`, beside `src/`, and the page loads Tailwind and mermaid from cdnjs at pinned versions.
- `bin/redthread-casefile` is how the skills and agents run that package. It sources `bin/redthread-lib`, whose `redthread::run_package` starts it with `uv run --no-project`, so it installs nothing into the project under investigation. `bin/` holds what ships with the plugin; `scripts/` holds repository tooling.
- `packages/navigate` holds `red_thread_navigate`, the code navigation tool behind `code-lens`. Its verbs are `map`, `find` and `slice`, and its tree-sitter queries are vendored in the package.
- `bin/redthread-navigate` is how the agents run that package, started the same way as `bin/redthread-casefile`.
- `tests/<tree>/<concept>/{unit,integration,smoke,e2e}/` holds the tests, in the trees `casefile`, `navigate` and `plugin`. The root `conftest.py` marks each test from its tier directory. The tests under `tests/casefile/pages/integration` run the page's script under `node` and skip when it is missing.
- A case lives in `.red-thread/<case-id>/` in the repository under investigation: `case.json`, `ledger.jsonl`, `threads/`, `board.html` and `out/`.
- `.claude/hooks/pyhooks.py` is the project's own hook script, a PEP 723 script that `.claude/settings.json` wires to Write, Edit and Read. ty does not check it, because `ty.toml` includes only `packages` and `tests`.
- Read `.claude/rules/python.md` before writing Python and `.claude/rules/testing.md` before writing tests. Both load on their own when you touch a matching file.

## Conventions

- Commit subjects follow Conventional Commits as the history does: `type(scope): subject`, with the subject in lowercase imperative and no closing period.
- The plugin version lives in both `pyproject.toml` and `.claude-plugin/plugin.json`. Keep the two equal: `tests/plugin/manifest` fails when they differ.
- An agent file or a skill is a prompt for one model. Write it for the model that will read it, and state what changed and why in `docs/design.md` when the change alters a decision recorded there.

## Boundaries

- Always: run the Verification commands before calling work done.
- Ask first: edits to `pyproject.toml`, `ruff.toml`, `pytest.toml`, `ty.toml` and `CLAUDE.md`, which `.claude/settings.json` lists under `permissions.ask`; edits to `uv.lock`; version bumps, which the release workflow (`.github/workflows/cd.yml`) owns; changes to `.claude/settings.json` or `.claude/hooks/pyhooks.py`, because every session runs the hooks they define.
- Never: weaken the ruff or ty configuration; hand-edit `uv.lock`, which the uv-lock hook regenerates; commit `.red-thread/`, which `init` adds to the repository's local git exclude file.

## Verification

`.github/workflows/ci.yml` defines CI's quality job, which runs every prek hook on all files and then the tests. Match it with `make pre-commit`, then `uv run pytest -q -m "not integration"`, because `make test` skips the unmarked tests that CI runs. CI's integration job runs `pytest -q -m integration`. `make check` is the faster local loop, but it skips the `format` group (the hygiene fixers, uv-lock, shfmt and mdformat), so it can pass where CI fails.

## Claude Code

- `make lint`, `make check` and `make pre-commit` pass inside the Bash sandbox: three fixer hooks skip `uv.lock`, `.claude/settings.json` and `.claude/hooks/pyhooks.py`, which are read-only there. `claude plugin validate --strict .` still fails there on `.mcp.json`, a sandbox mount point that shows up as a character device. A failure that names such a path comes from the sandbox, not the repository: report it instead of changing code to get past it.
- `uv add`, `uv lock` and `make sync` fail inside the Bash sandbox, and so does a nested `claude` run. Each needs a command run outside it.
- The project hooks run on every tool call: before a Write or Edit, a check asks for approval when the change adds a lint or type suppression; after it, the formatter runs; after a Read, ruff and ty report diagnostics on the file.
