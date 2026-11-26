# red-thread-plans

The plan side of red-thread: a plan cuts work into tickets, and each ticket's acceptance criteria are required by decisions and known facts recorded in one or more investigations (cases). It depends on `red-thread-core` for the page and on `red-thread-casefile` to read the cases a plan cites. It never writes into a case directory.

The skills run it through `bin/redthread-plan`, which starts it with `uv run --no-project` so that nothing is installed into the repository under investigation.

## The plan directory

A plan lives beside the cases, in the repository under investigation:

```text
.red-thread/plans/<plan-id>/
  plan.json    the plan's id, title and start time, every case its revisions cited, and the epic and issue links once published
  r1.json      one checked revision per file, never edited
  r2.json
  plan.html    the latest revision as a page, drawn again by revise and render
```

A plan id is the UTC date and a slug of the title, such as `20261126-split-the-plans-package`.

## Commands

| Command | What it does |
| --- | --- |
| `init --title T [--slug S] [--root R]` | creates the plan directory and its `plan.json`, and prints the directory |
| `revise --plan DIR [--file F]` | checks a plan whole against the cases it names, redacts secrets, stores it as the next revision, adds its cases to `plan.json` and writes `plan.html`; the plan is one JSON object, read from standard input or `--file` |
| `render --plan DIR` | draws `plan.html` again from the latest revision |

## A revision

A plan has an `intent`, an `approach`, `cases`, `invariants`, `non_goals`, `tickets` and `risks`.

`cases` gives each investigation the plan rests on an alias: `{"C1": "20261121-retry-queue-slowdown", "C2": "20261124-page-layout"}`. A ref names an entry through its alias: `C1.e4` is entry `e4` of case C1, and `C2.T1.e2` is entry `e2` of thread T1 in case C2. One plan can rest on many cases, and one case can be cited by many plans.

A ticket has an `id` and a `worktree` (both lowercase slugs), a `title`, a `why` that says what the ticket is for, `acceptance` criteria, the paths or globs it `owns`, the tickets it `depends_on` and an optional `interface` (`language`, `source`). A worktree is one git worktree and one stack of pull requests: the tickets in it land in order, each on the one before, and two worktrees never own the same file, so they can be built side by side.

An acceptance criterion is `{"criterion": "...", "required_by": ["C1.e4"]}`: an outcome someone can observe, and the live `decision` or `known` entries that require it.

`revise` refuses the whole plan, naming every fault, when it names no case or a case that is not in `.red-thread/`, when a criterion is required by nothing or by a ref that is unknown, retired or of another kind, when a ticket has no why, when the dependencies form a cycle or cross worktrees, or when two worktrees own a path in common. A stored revision is never rewritten.

## The page

`plan.html` opens with the revision, the date, the commit, the ticket count and what changed since the revision before, then the approach, the cases the plan rests on, the invariants and the non-goals. Each worktree is a panel of its tickets, bottom of the stack first: a ticket shows its status mark (`new`, `changed` or `unchanged` against the revision before), its title, its why, its place in the worktree, what it depends on, the paths it owns, each criterion with the entries that require it, and its interface as a code listing. The risks follow, each with its handling and its signal. A mermaid chart draws each worktree as a stack with an arrow from each dependency to its dependent, and a folded list names the tickets the revision before had and this one drops.
