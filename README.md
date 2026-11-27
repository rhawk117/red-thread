# red-thread

red-thread is a Claude Code plugin for investigating before you build. You ask a question, read-only scouts collect cited facts, and the session stops at a gate after every round so that you decide whether the evidence is enough. Every claim is kept in a case file, so a case survives a compaction, a new session or a change of model.

## How it works

1. **Frame.** `investigate` agrees the target, the kind of case (`root-cause`, `claim`, `research` or `survey`) and the bar the answer must meet. It then creates a case under `.red-thread/<case-id>/` in the repository you are investigating.
2. **Research.** Each round sends scouts for facts. A scout reports each claim with a verdict and a citation: a `path:line` with the quoted line, a URL or a command. The findings are written into the case file as Markdown, and the case file script checks every finding and citation, naming each fault with its line and fix.
3. **Gate.** After each round the board is printed and you steer: another round, a review of the conclusion, or stop. The board flags a citation whose line has changed, moved or gone missing since it was recorded.
4. **Distill.** `distill` turns the case into one output for one reader: a brief, a GitHub issue, a handoff or a report. The script assembles it from the case file, so every line keeps its citation.

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

When something is broken and you want it working, start from the failure instead:

```text
/red-thread:debug tests/test_pool.py::test_starvation fails since the retry change
```

`debug` reproduces the failure, tests rival hypotheses by experiment, and applies a fix only after you approve it. It then reports why the defect was introduced and why nothing caught it, prices the guards that would have, and offers an investigation of any technical debt behind it. You decide which of those are worth building.

## What the plugin holds

| Path | What it is |
| --- | --- |
| `skills/investigate` | the investigation loop and its gate |
| `skills/distill` | the four outputs, one reference file per output |
| `skills/debug` | a failure taken to a confirmed cause, a fix you approve and a decision on preventing it; one reference file for failure shapes and one for the escape analysis |
| `skills/agents/navigate` | how the scouts use the navigate script; preloaded into them, not a command you run |
| `skills/agents/meet-the-team` | who the agents are and how to brief each one; preloaded into `research-lead` and loaded by name from `investigate` and `debug`, not a command you run |
| `skills/agents/artifact-authoring` | how an agent words what it writes for a reader who was not there: findings, reports, gate summaries, distill titles and handoffs; preloaded into `research-lead` and loaded by name from `investigate`, `debug` and `distill`, not a command you run |
| `agents/` | `research-lead`, which runs one thread of a case, the scouts in `agents/swarm/` (`code-sense`, `code-lens`, `web-head` and `lab-rat`), and the skeptic `peer-review` |
| `hooks/roster.py` | a hook that denies a red-thread agent's dispatch outside its roster |
| `packages/casefile` | the only writer and renderer of a case file: `init`, `render`, `check` and `export` |
| `bin/redthread-casefile` | how the skills and agents run that package, without installing anything into your project |
| `packages/navigate` | code navigation for the `code-lens` scout: `map`, `find` and `slice` over six languages |
| `bin/redthread-navigate` | how the agents run that package, without installing anything into your project |

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
