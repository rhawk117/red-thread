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

A plan has an `intent`, an `approach`, `cases`, `invariants`, `non_goals`, `tickets`, `risks` and `lights`.

`lights` is `"on"` when the owner is in the loop while the tickets are built and decides each fork in the road, and `"off"` when they are away, so a fork that would change what a ticket promises waits for them. Leave it out when the owner was not asked.

`cases` gives each investigation the plan rests on an alias: `{"C1": "20261121-retry-queue-slowdown", "C2": "20261124-page-layout"}`. A ref names an entry through its alias: `C1.e4` is entry `e4` of case C1, and `C2.T1.e2` is entry `e2` of thread T1 in case C2. One plan can rest on many cases, and one case can be cited by many plans.

A ticket has an `id` and a `worktree` (both lowercase slugs), a `title`, a `why` that says what the ticket is for, `acceptance` criteria, the paths or globs it `owns`, the tickets it `depends_on` and an optional `interface` (`language`, `source`). A worktree is one git worktree and one stack of pull requests: the tickets in it land in order, each on the one before, and two worktrees never own the same file, so they can be built side by side.

An acceptance criterion is `{"criterion": "...", "required_by": ["C1.e4"]}`: an outcome someone can observe, and the live `decision` or `known` entries that require it.

`revise` refuses the whole plan, naming every fault, when it names no case or a case that is not in `.red-thread/`, when a criterion is required by nothing or by a ref that is unknown, retired or of another kind, when a ticket has no why, when the dependencies form a cycle or cross worktrees, or when two worktrees own a path in common. A stored revision is never rewritten.

## The page

`plan.html` is laid out like every red-thread page: at 1280px and up, a rail on the left holds the title, the facts, the filters, the list of sections and a fold that explains each word the page uses, and the worktrees sit side by side as columns; on a phone the rail sits on top and the columns stack.

The facts are the revision, the date, the commit, the ticket count, the lights, what changed since the revision before and the epic, which reads "not published yet" until a publish step records it. From the second revision on, a "What changed" section comes first: the tickets added, changed and dropped, then each plan field that changed, as it was and as it is. The approach follows, then the cases the plan rests on, each alias linked to its board with the case's question, then the invariants and the non-goals.

Each worktree is a column of its tickets, bottom of the stack first. A ticket shows its status mark (`new`, `changed` or `unchanged` against the revision before), its title, its why, its place in the worktree, what it depends on, the paths it owns and its issue link, or "not published yet". Under "Done when", each criterion lists every entry that requires it: the entry's kind, its ref linked to that entry on its case's board (`../../<case-id>/board.html#e4`) and its text, so the reason for the criterion is on the page. A ref whose entry is gone says so. A changed ticket has a fold with each changed field as it was and as it is, and an interface shows as a code listing.

The risks follow, each with its handling and its signal. A mermaid chart draws each worktree as a stack with an arrow from each dependency to its dependent, and a folded list names the tickets the revision before had and this one drops.

## Links back from the boards

The plan never writes into a case directory. A case's `board.html` lists the plans that cite it under "Plans", linking `../plans/<plan-id>/plan.html`: the casefile package reads each `plan.json` in `.red-thread/plans/` when it draws the board, and skips one it cannot read. Run `render --html` on a case after a new plan cites it to add the link.
