# red-thread-casefile

The case file behind the red-thread plugin. A case file is Markdown with YAML frontmatter that records what an investigation found. The skills and the leads write its findings by hand; this package creates the file, checks every finding and citation, renders the board at every gate, and assembles the final outputs from the findings. It writes no finding itself.

It depends on msgspec, which decodes the frontmatter and each finding's YAML block into strict Structs, and on `red-thread-core` (`packages/core`), which holds the document tree, the page and its assets, redaction and the source tree, clock and page store. This package adds what only a case file knows: the case file format, its rules, the board and the lenses, and the finding list block the core page renders. `docs/design.md` section 4 holds the format, the rules and the decisions behind them.

## Who uses it

The `investigate` and `distill` skills call it through `bin/redthread-casefile`, and so do the agents: `research-lead` appends its rounds to its own thread file and runs `check` until it passes, and `peer-review` runs `render` and `check` to test a conclusion against the record. The `debug`, `game-plan`, `cross-examine` and `course-correction` skills append to `case.md` the same way. The launcher runs:

```sh
uv run --no-config --no-project --python 3.14 --with-editable <plugin>/packages/casefile -- python -m red_thread_casefile "$@"
```

uv takes the dependencies from this package's `pyproject.toml`, installs `packages/core` editable beside it as a workspace source, and keeps the environment in its cache. Nothing is installed into the repository under investigation, and `--no-config` stops a uv setting in that repository from changing what gets installed. The first run on a machine downloads msgspec and, if needed, Python 3.14.

## What it is for

- **Starting a case.** `init` turns a question into a case directory with its target, kind and bar, and records the commit and the languages of the tree.
- **Recording findings.** A scout's, a lead's or the owner's findings are appended by hand as a round of findings. `check` then names every fault with its line and fix, so a claim without a citation can't pass as a fact.
- **Steering at a gate.** `render` prints a board that fits on about one screen, so the owner can decide whether to run another round, review the conclusion or stop.
- **Resuming later.** A new session, a model switch or a compaction loses the conversation but not the case. `check` tells the next session which recorded claims still hold against the current tree.
- **Writing it up.** `export` builds a brief, an issue, a handoff or a report from the findings, so every line in it keeps its citation.
- **Sharing the board.** The link of a board published to claude.ai goes in the `page_url` frontmatter key, written by hand, so later gates republish to the same URL and the board shows it.

## The case directory

A case lives in the repository under investigation:

```text
.red-thread/<case-id>/
  case.md            frontmatter (target, kind, bar, publish choice, page URL, capabilities), then the primary's rounds
  threads/T1.md      the rounds of one lead; one file per thread, so writers never share a file
  board.html         rendered at every gate
  out/               brief.md, issue.md, handoff.md, report.md and their HTML
```

A case id is the UTC date and a slug of the target, such as `20261121-retry-queue-slowdown`. `init` adds `.red-thread/` to the repository's local git exclude file, so a case is never committed.

## Commands

| Command | What it does |
| --- | --- |
| `init --target T --kind K --bar B [--slug S] [--publish] [--root R]` | creates the case, records HEAD and detects the repository's languages once; `--kind` is `root-cause`, `claim`, `research` or `survey` |
| `render --case DIR [--full] [--html]` | opens every citation again and prints the board with a changed, moved or missing citation flagged beside its finding; `--full` shows every live finding, `--html` also writes `board.html` |
| `check --case DIR` | reads every file of the case and reports each fault as `file:line finding id: problem` with its fix, then resolves every live citation against the current tree; it changes no file and exits 1 on a fault |
| `export --case DIR --lens L [--selection F] [--html]` | writes one output to `out/` from the findings; `--lens` is `brief`, `issue`, `handoff` or `report` |

`--case` takes the directory `init` printed. `init` writes the frontmatter, the `# target` title and the `## Round 0` heading. Round 0 is framing, and the rounds count up from there. `render` and `export` refuse a case whose files cannot be read and point at `check`.

Each output has a line budget, and `export` fails when the output runs over it: 60 lines for a brief, 80 for an issue, 40 for a handoff and 200 for a report. The selection it reads is a JSON object with an optional `title`, `goal`, `include` and `blocking`, the last two as lists of finding ids such as `["e3", "T1.e2"]`.

## Findings and their rules

A finding is a `### e<n>` heading over one fenced `yaml` block, under a `## Round N · YYYY-MM-DD · HEAD` heading that gives it its round, date and commit. Its `kind` is `known`, `open`, `decision`, `hypothesis`, `ruled_out`, `resource` or `next`. Most carry a citation in `cite` (a `path:line`, a `URL#heading` or a command) and the cited text in `quote`. Optional fields hold a symbol address, a mermaid diagram, the caveat an inference rests on, the observation that would refute a hypothesis, and the earlier findings this one retires. The design document lists every field and shows a whole case file.

`check` enforces these rules:

1. A `known` needs a citation. A claim with no citation is `open`.
2. A `decision` comes only from the owner.
3. A finding is corrected where it stands until a gate or a report has shown it. After that, a later finding retires it by naming it, and it is never edited.
4. Every file is read whole, and each fault is named with its `file:line`, its finding id and its fix, not just the first one.
5. Text matching a secret pattern is a fault, and `check` prints the text with the secret replaced, to put in its place.
6. A finding whose round commit differs from the current HEAD is a lead to re-verify, not evidence.
7. A `hypothesis` needs a `refute` line.
8. A `ruled_out` finding needs a citation or the owner as its source.

It also opens every `path:line` and compares `quote` with the cited line; a `path:line` cite without `quote` is a fault, and `check` prints the line to paste. An absolute path or one containing `..` is never read and stays unchecked. Text outside a round heading, a finding heading or a block is a fault, and so is a field that is present but blank. Round headings in one file go up, one heading for each round. A thread can retire only its own findings, a finding from `user` or a `decision` belongs in `case.md`, an `INFERRED` finding needs `rests_on`, a `known` can't carry a verdict weaker than `VERIFIED`, and `page_url`, when set, must be an https link.

## The citation check

`check`, and `render` before it prints, gives each live citation one of four states:

- `ok`: the file exists and the quoted text is still at that line.
- `moved`: the quoted text is elsewhere in the file, or the symbol address now resolves to another line.
- `changed`: the line or symbol exists but the text differs.
- `missing`: the file, line or symbol is gone.

A citation it does not open, such as a URL, a command or an absolute path, is reported as `unchecked`.

This answers the question a later session has to ask first: which of these claims can I still trust? It also catches a citation a scout invented before the owner sees it at a gate. `check` redacts the lines it reads before it compares them, so a redacted quote still matches.

## Pages

`render --html` and `export --html` write HTML pages from the case file. The board page opens with the case facts (bar, kind, round, commit, languages, finding counts, threads and the totals of the citation check), then one panel per section, then a mermaid map of the case: each thread is a line of its findings, and a retired finding has a dashed outline with an edge from the finding that retired it. A folded list of retired findings closes the page. Lens pages share the panels and finding details but leave out the facts and the retired list.

A page loads two scripts from cdnjs, each pinned to an exact version with an integrity hash: the Tailwind browser build for styling and mermaid for diagrams. Offline, a page still reads top to bottom with every finding in the HTML. The page's own script, `page.js` in `red-thread-core`, uses no library. It filters findings by kind and thread, folds sections, copies a finding id or a citation, and redraws diagrams when the theme changes. Finding text reaches the page only as escaped text.

The skeleton, styles and script are in `red-thread-core` under `src/red_thread_core/assets/`. This package keeps its own files under `src/red_thread_casefile/assets/`: the map header, `wording.yaml` and `lenses.yaml`. `wording.yaml` holds the words the board and the lens outputs use: the section headings with their notes, the prefixes of a finding's notes, the notes of the map and retired sections, and the glossary. `lenses.yaml` holds each lens's parts in order, its line budget and the lines of How to read. Edit either file to change the wording; a key the code does not know is refused when the file loads. Colors are tokens in `page.css` in core, one set per theme, and `tailwind.css` maps them to Tailwind utilities, so a palette change touches one file.

## Development

The tests are under `tests/casefile/` at the repository root. `make check` runs lint and the fast tests, and `uv run pytest -q -m integration` runs the page script's tests under Node, which skip when Node is missing.
