# red-thread-casefile

The case file behind the red-thread plugin. It keeps an append-only ledger of what an investigation found, renders that ledger as a board at every gate, checks that each citation still points at the code it quoted, and assembles the final outputs from the ledger. Nothing else in the plugin writes or renders a case file, and the model never edits one by hand.

Its one dependency is msgspec, which reads and writes every JSON record. `docs/design.md` section 4 holds the format, the rules and the decisions behind them.

## Who uses it

The `investigate` and `distill` skills call it through `bin/redthread-casefile`, and so do the agents: `research-lead` writes its thread's entries, and `peer-review` runs `render` and `check` to test a conclusion against the record. The launcher runs:

```sh
uv run --no-config --no-project --python 3.14 --with-editable <plugin>/packages/casefile -- python -m red_thread_casefile "$@"
```

uv takes the dependencies from this package's `pyproject.toml` and keeps the environment in its cache. Nothing is installed into the repository under investigation, and `--no-config` stops a uv setting in that repository from changing what gets installed. The first run on a machine downloads msgspec and, if needed, Python 3.14.

## What it is for

- **Starting a case.** `init` turns a question into a case directory with its target, kind and bar, and records the commit and the languages of the tree.
- **Recording findings.** `add` takes a batch of entries from a scout, a lead or the owner and refuses the whole batch if any entry breaks a rule. A claim without a citation can't be stored as a fact.
- **Steering at a gate.** `render` prints a board that fits on about one screen, so the owner can decide whether to run another round, review the conclusion or stop.
- **Resuming later.** A new session, a model switch or a compaction loses the conversation but not the case. `check` tells the next session which recorded claims still hold against the current tree.
- **Writing it up.** `export` builds a brief, an issue, a handoff or a report from the ledger, so every line in it keeps its citation.
- **Sharing the board.** `page` records the link of a board published to claude.ai, so later gates republish to the same URL.

## The case directory

A case lives in the repository under investigation:

```text
.red-thread/<case-id>/
  case.json          target, kind, bar, publish choice, page URL, detected capabilities
  ledger.jsonl       entries written by the primary
  threads/T1.jsonl   entries written by one lead; one file per thread, so writers never share a file
  board.html         rendered at every gate
  out/               brief.md, issue.md, handoff.md, report.md and their HTML
```

A case id is the UTC date and a slug of the target, such as `20261121-retry-queue-slowdown`. `init` adds `.red-thread/` to the repository's local git exclude file, so a case is never committed.

## Commands

| Command | What it does |
| --- | --- |
| `init --target T --kind K --bar B [--slug S] [--publish] [--root R]` | creates the case, records HEAD and detects the repository's languages once; `--kind` is `root-cause`, `claim`, `research` or `survey` |
| `add --case DIR --round N [--thread T1] [--file F]` | validates a batch of entries whole, stamps the time and HEAD, redacts secrets and appends it; the batch is one JSON object or a JSON array of them, read from standard input or `--file` |
| `render --case DIR [--full] [--html]` | opens every citation again and prints the board with a changed, moved or missing citation flagged beside its entry; `--full` shows every live entry, `--html` also writes `board.html` |
| `check --case DIR` | resolves every live citation against the current tree |
| `export --case DIR --lens L [--selection F] [--html]` | writes one output to `out/` from the ledger; `--lens` is `brief`, `issue`, `handoff` or `report` |
| `page --case DIR --url URL` | records the https link that publishing returned in `case.json` |

`--case` takes the directory `init` printed. Round 0 is framing, and the rounds count up from there.

Each output has a line budget, and `export` fails when the output runs over it: 60 lines for a brief, 80 for an issue, 40 for a handoff and 200 for a report. The selection it reads is a JSON object with an optional `title`, `goal`, `include` and `blocking`, the last two as lists of entry refs such as `["e3", "T1.e2"]`.

## Entries and their rules

An entry has a `kind`: `known`, `open`, `decision`, `hypothesis`, `ruled_out`, `resource` or `next`. Most carry a citation in `cite` (a `path:line`, a `URL#heading` or a command) and the cited text in `quote`. Optional fields hold a symbol address, a mermaid diagram, the caveat an inference rests on, the observation that would refute a hypothesis, and the earlier entries this one retires. The design document lists every field.

`add` enforces these rules:

1. A `known` needs a citation. A claim with no citation is `open`.
2. A `decision` comes only from the owner.
3. Files are append-only. A later entry retires an earlier one by naming it; nothing is edited.
4. A batch is validated whole before anything is stored.
5. Text matching a secret pattern is redacted before it is stored.
6. An entry whose `head` differs from the current HEAD is a lead to re-verify, not evidence.
7. A `hypothesis` needs a `refute` line.
8. A `ruled_out` entry needs a citation or the owner as its source.

It also opens every `path:line` it is given. When the entry supplies a `quote`, `add` compares it with the cited line; when it doesn't, `add` records the line itself. An absolute path or one containing `..` is never read and stays unchecked. A thread can retire only its own entries, an `INFERRED` entry needs `rests_on`, and a `known` can't carry a verdict weaker than `VERIFIED`. A rejected batch comes back with every fault and its fix, not just the first one.

## The citation check

`check`, and `render` before it prints, gives each live citation one of four states:

- `ok`: the file exists and the quoted text is still at that line.
- `moved`: the quoted text is elsewhere in the file, or the symbol address now resolves to another line.
- `changed`: the line or symbol exists but the text differs.
- `missing`: the file, line or symbol is gone.

A citation it does not open, such as a URL, a command or an absolute path, is reported as `unchecked`.

This answers the question a later session has to ask first: which of these claims can I still trust? It also catches a citation a scout invented before the owner sees it at a gate. `check` redacts the lines it reads before it compares them, so a redacted quote still matches.

## Pages

`render --html` and `export --html` write HTML pages from the ledger. The board page opens with the case facts (bar, kind, round, commit, languages, entry counts, threads and the totals of the citation check), then one panel per section, then a mermaid map of the case: each thread is a line of its entries, and a retired entry has a dashed outline with an edge from the entry that retired it. A folded list of retired entries closes the page. Lens pages share the panels and entry details but leave out the facts and the retired list.

A page loads two scripts from cdnjs, each pinned to an exact version with an integrity hash: the Tailwind browser build for styling and mermaid for diagrams. Offline, a page still reads top to bottom with every entry in the HTML. The page's own script, `assets/page.js`, uses no library. It filters entries by kind and thread, folds sections, copies a ref or a citation, and redraws diagrams when the theme changes. Entry text reaches the page only as escaped text.

The skeleton, styles, script and map header are in `assets/`, beside `src/`. The package reads them by path from the source tree, which is how the launcher and an editable install run it. A built wheel would not carry them. Colors are tokens in `assets/page.css`, one set per theme, and `assets/tailwind.css` maps them to Tailwind utilities, so a palette change touches one file.

## Development

The tests are under `tests/casefile/` at the repository root. `make check` runs lint and the fast tests, and `uv run pytest -q -m integration` runs the page script's tests under Node, which skip when Node is missing.
