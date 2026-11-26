# red-thread-plans

The plan of a red-thread case: revisions checked whole against the case file's ledger, stored one file per revision, and drawn as a page. It depends on `red-thread-core` for the page and on `red-thread-casefile` for the ledger a plan cites.

The skills run it through `bin/redthread-plan`, which starts it with `uv run --no-project` so that nothing is installed into the repository under investigation.

| Command | What it does |
|---|---|
| `revise --case DIR [--file F]` | checks a plan whole, redacts secrets, stores it as the next revision and writes the plan page; the plan is one JSON object, read from standard input or `--file` |

A revision is stored in the case directory as `plans/r1.json`, `plans/r2.json` and so on, one file per revision, never edited. `plan.html` shows the latest revision and is drawn again each time one is stored.

A plan has an `intent`, an `approach`, `invariants`, `non_goals`, `tickets` and `risks`. A ticket has an `id` and a `lane` (both lowercase slugs), a `title`, `acceptance` sentences that each name in `rests_on` the live `decision` or `known` entries they follow from, the paths or globs it `owns`, the tickets it `depends_on` and an optional `interface` (`language`, `source`). `revise` refuses the whole plan, naming every fault, when a sentence rests on nothing or on a ref that is unknown, retired or of another kind, when the dependencies form a cycle or cross lanes, or when two lanes own a path in common. A stored revision is never rewritten.

`revise` writes `plan.html` each time it stores a revision. The page opens with the revision, the date, the commit, the ticket count and what changed since the revision before, then the approach, the invariants and the non-goals. Each lane is a panel of its tickets, bottom of the stack first: a ticket shows its status mark (`new`, `changed` or `unchanged` against the revision before), its title, its place in the lane, what it depends on, the paths it owns, each acceptance sentence with the entries it rests on, and its interface as a code listing. The risks follow, each with its handling and its signal. A mermaid chart draws each lane as a stack with an arrow from each dependency to its dependent, and a folded list names the tickets the revision before had and this one drops.
