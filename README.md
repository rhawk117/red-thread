# red-thread

red-thread is a Claude Code plugin for investigating before you build. You ask a question, read-only scouts collect cited facts, and the session stops at a gate after every round so that you decide whether the evidence is enough. Every claim is kept in a case file, so a case survives a compaction, a new session or a change of model.

## How it works

1. **Frame.** `investigate` agrees the target, the kind of case (`root-cause`, `claim`, `research` or `survey`) and the bar the answer must meet. It then creates a case under `.red-thread/<case-id>/` in the repository you are investigating.
2. **Research.** Each round sends scouts for facts. A scout reports each claim with a verdict and a citation: a `path:line` with the quoted line, a URL or a command. The case file script validates a batch whole before it records any of it.
3. **Gate.** After each round the board is printed and you steer: another round, a review of the conclusion, or stop. The board flags a citation whose line has changed, moved or gone missing since it was recorded.
4. **Distill.** `distill` turns the case into one output for one reader: a brief, a GitHub issue, a handoff or a report. The script assembles it from the ledger, so every line keeps its citation.

The case directory is added to the repository's local git exclude file, so it is never committed.

## Requirements

- Claude Code
- [uv](https://docs.astral.sh/uv/), which runs the case file script and fetches Python 3.14 for it
- git

## Try it

No marketplace lists the plugin yet, so load it from a clone:

```sh
git clone https://github.com/rhawk117/red-thread
claude --plugin-dir ./red-thread
```

Then, in a session opened in the repository you want to investigate:

```text
/red-thread:investigate why does the retry queue stall under load
/red-thread:distill
```

`/red-thread:investigate` also resumes a case that already exists for the target.

## What the plugin holds

| Path | What it is |
| --- | --- |
| `skills/investigate` | the investigation loop and its gate |
| `skills/distill` | the four outputs, one reference file per output |
| `agents/` | `research-lead`, which runs one thread of a case, the scouts `code-sense`, `code-lens`, `web-head` and `research-cell`, and the skeptic `peer-review` |
| `hooks/roster.py` | a hook that denies a red-thread agent's dispatch outside its roster |
| `packages/casefile` | the only writer and renderer of a case file: `init`, `add`, `render`, `check`, `export` and `page` |
| `scripts/casefile.sh` | how the skills and agents run that package, without installing anything into your project |
| `packages/navigate` | code navigation for the `code-lens` scout: `map`, `find` and `slice` over six languages |
| `scripts/navigate.sh` | how the agents run that package, without installing anything into your project |

## Development

```sh
make setup     # install the git hooks and sync the dependencies
make check     # lint, then the fast tests
make quality   # every hook, then the tests of CI's quality job
```

- `uv run pytest -q -m integration` runs what CI's integration job runs. The tests of the page's script need Node and skip without it.
- Tests live in `tests/<tree>/<concept>/<tier>/`, and the directory sets the tier: `unit`, `integration`, `smoke` or `e2e`.
- `.claude/CLAUDE.md` lists every command, the layout, the conventions and what to verify before calling work done. `.claude/rules/` holds the Python and testing rules.
- `docs/design.md` holds the design, each decision with its date, and the build status. Read it before changing a skill, an agent or the case file format.

## Security and license

`SECURITY.md` says what the plugin runs and stores, and how to report a problem. The license is MIT.
