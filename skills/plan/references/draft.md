# The draft

The draft is one JSON object in `PLAN/draft.json`. `PLANNER revise` reads it at the end, checks it whole and stores it as the next revision. Until then it is your working copy, and the consistency check below is how you find its faults before the owner does.

## Fields

| Field | What it holds |
| --- | --- |
| `intent` | what the plan changes, in one paragraph |
| `approach` | the strategy, and why it beats the alternative the owner considered |
| `cases` | each case the plan rests on, by alias: `{"C1": "<case-id>"}`. The case id is the directory name under `.red-thread/` |
| `invariants` | what must stay true after every ticket lands, each with what shows it |
| `non_goals` | what the plan leaves out, each with its reason |
| `tickets` | the work, below |
| `risks` | what could go wrong, below |

A ticket has an `id` and a `worktree` (lowercase slugs such as `retry-cap`), a `title`, a `why`, its `acceptance` criteria, the paths or globs it `owns` and the tickets it `depends_on`. A criterion is `{"criterion": "...", "required_by": [...]}`, where each ref names a live `decision` or `known` entry through its case's alias: `C1.e4`, or `C2.T1.e2` for an entry in thread T1. Leave `interface` out: the agent that writes it is not built yet.

A risk has an `id` (`R1`, `R2`), the `risk`, a `signal`, the `tickets` it touches and a `handling`: `{"kind": "accept"}`, `{"kind": "mitigate", "ticket": "retry-cap", "criterion": "..."}` or `{"kind": "you-intervene", "recut": ["retry-cap"]}`. A mitigation's `criterion` is one of that ticket's criteria word for word; leave it out when the ticket itself is the mitigation. A `recut` holds some of the risk's own tickets.

## Example

```json
{
  "intent": "Retries stop starving the job pool: a job gives up after a fixed number of attempts, so new jobs keep their share of the workers.",
  "approach": "Cap the attempts of each job where retry() decides, and keep retries in the shared pool. A separate retry pool was considered and set aside by the owner.",
  "cases": {"C1": "20261126-retry-pool", "C2": "20261126-retry-limit"},
  "invariants": ["The test suite passes after each ticket lands, shown by the repository's own test command."],
  "non_goals": ["A separate pool for retries: the owner chose to keep one pool."],
  "tickets": [
    {
      "id": "retry-cap",
      "title": "Cap the attempts of each job",
      "why": "A job that keeps failing is retried without end and holds a worker that new jobs need.",
      "worktree": "retry",
      "acceptance": [
        {"criterion": "A job that fails five times is not run a sixth time.", "required_by": ["C1.e1", "C1.e2"]},
        {"criterion": "A job dropped after its last attempt is logged with its id.", "required_by": ["C1.e3"]}
      ],
      "owns": ["src/pool.py", "tests/test_pool.py"],
      "depends_on": []
    },
    {
      "id": "retry-docs",
      "title": "Document the retry limit",
      "why": "Operators need to know when a failing job stops being retried.",
      "worktree": "docs",
      "acceptance": [
        {"criterion": "The docs state that a job gets five attempts and is then dropped and logged.", "required_by": ["C2.e1", "C1.e2"]}
      ],
      "owns": ["docs/"],
      "depends_on": []
    }
  ],
  "risks": [
    {
      "id": "R1",
      "risk": "A job dropped after its last attempt disappears without a trace.",
      "signal": "A job leaves the queue with no error in the log.",
      "tickets": ["retry-cap"],
      "handling": {"kind": "mitigate", "ticket": "retry-cap", "criterion": "A job dropped after its last attempt is logged with its id."}
    }
  ]
}
```

## Writing each field

From mightymodels `game-plan`, unless marked otherwise.

- **Altitude is not vagueness.** A ticket says what and where, never how, and says what outcome shows it done. Task detail waits until the ticket starts, against the code as it is then.
- **A criterion is an observable outcome sentence**: what a person or a test can see happen, with no ids and no commands. "Asking for a job that does not exist returns a not-found message instead of a stack trace" is one. "Error handling works correctly", "handles errors appropriately" and "is consistent with the rest of the code" are not: rewrite them or drop them.
- **The why** says what the ticket is for, to a reader who has not seen the cases. It is the reason someone would build it, not a list of its criteria.
- **An invariant** says what shows it holds: a test, a CI job or a read, in words. An invariant without that is a wish.
- **A non-goal** carries its reason, so a later session does not reopen it.
- **No `path:line` in plan text.** A line number goes stale with the first ticket that lands and is trusted anyway. The citations live in the entries, and a criterion reaches them through `required_by`. Paths belong in `owns`.

## Cutting tickets

From mightymodels `break-it-down`, with the worktree rules of `docs/design.md` section 13.

- A ticket is one pull request a reviewer can hold in their head: one to four criteria. A ticket that needs more is two tickets.
- Cut where the work already has a seam, in this order: by behaviour (criteria that can be proven apart go to different tickets), by module (files that change for different reasons), by order (what must land first, such as a schema before its callers, is a ticket of its own, and the tickets that need it name it in `depends_on`).
- The repository passes after each ticket, not only after the last.
- Tickets that depend on each other share a worktree and land as a stack, bottom first. A dependency on a ticket in another worktree is refused.
- Two worktrees never own the same path. A ticket that cannot keep its files apart from another worktree joins that worktree. `dir/` owns everything under `dir`; an entry may use `*`, `?` and `**`, and may not be absolute, climb with `..` or use `[ ]`.
- Some work does not cut: one rename across thirty files is one change. Keep it whole and say why.

## Consistency check

From mightymodels `game-plan`. Run it on every draft before the owner sees it. Each item is a yes or no question.

- Every ticket has a why and one to four criteria, and each criterion is an observable outcome sentence.
- Each criterion follows from the entries in its `required_by`: read each one on the board. An entry that says less than the criterion promises means a narrower criterion or a question for the owner.
- Every decision on the boards that bears on the intent shows in the plan as the approach, an invariant, a non-goal or a criterion, and nothing in the plan contradicts one.
- Every open question and assumption from the design dialog is a risk.
- No two tickets do the same thing, and no ticket does what a non-goal excludes.
- Every `depends_on` names a ticket in the same worktree, and no two worktrees own a path in common.
- Every invariant says what shows it, and every non-goal its reason.
- Every risk has a signal someone can see while the work runs, the tickets it touches, and after the risk dialog the handling the owner chose.
- No ticket has an `interface`, and no plan text carries a `path:line`.

## Showing the plan

At the gate, show the plan in your message in this shape, worktree by worktree with each stack bottom first, before you ask:

```text
Cap retries in the job pool (rests on C1 20261126-retry-pool, C2 20261126-retry-limit)
Intent: Retries stop starving the job pool: ...
Approach: Cap the attempts of each job where retry() decides, ...

Worktree retry
  1. Cap the attempts of each job (retry-cap)
     why: A job that keeps failing is retried without end ...
     owns: src/pool.py, tests/test_pool.py
     done when:
       - A job that fails five times is not run a sixth time. (C1.e1 known, C1.e2 decision)
       - A job dropped after its last attempt is logged with its id. (C1.e3 decision)

Worktree docs
  1. Document the retry limit (retry-docs)
     ...

Invariants: ...
Non-goals: ...
Risks:
  R1 A job dropped after its last attempt disappears without a trace.
     signal: a job leaves the queue with no error in the log
     handling: mitigate, by the second criterion of retry-cap
```

When the draft revises a stored plan, open with what changed since that revision: the tickets added, changed and dropped.

## From a revision to a draft

A stored revision, `r<n>.json`, carries fields the script stamps: `schema`, `revision`, `at` and `head`, and a `position` in every ticket. The draft refuses unknown fields, so write `PLAN/draft.json` as the revision without those five, and change it from there.
