# The plan

A plan is one Markdown file, `PLAN`, at `.red-thread/tickets/<plan-id>/plan.md`: the plan of one ticket. `PLANNER init` writes its frontmatter and its headings, and you write everything else by hand. The frontmatter holds what a script reads; the sections hold what a person reads. `PLANNER check --plan PLAN` reads the file and names every fault with its fix, and changes nothing. The consistency check below finds what the script cannot.

## Frontmatter

| Key | What it holds | Who writes it |
| --- | --- | --- |
| `id` | the plan's id, the name of its directory | init; never change it |
| `title` | what the ticket delivers, in one line | init, from `--title` |
| `status` | `draft` until the owner accepts the plan at the gate, then `accepted`; `done` once the work has landed | you, at the gate |
| `revision` | 1 at first; one more for each change after the owner accepted it | you, with a line under Changes |
| `created` | the day init ran | init; never change it |
| `head` | the commit init ran at | init; never change it |
| `cases` | each case the plan rests on, by alias: `C1: <case-id>` | init, from each `--case` in order. To rest on another case later, add it with the next alias |
| `lights` | `"on"` or `"off"` with the quotes, asked at the gate; `null` until then | you, at the gate |
| `epic` | the epic this ticket belongs to, `null` until the epic skill is built | nobody yet |
| `issue` | the ticket's issue, `null` until publishing is built | nobody yet |

Write `lights: "on"` with the quotes: YAML reads a bare `on` or `off` as true or false, and check refuses it. Leave a key you do not change as init wrote it, and add none: check refuses an unknown key.

## Sections

The headings come from init, in this order, and check refuses a plan that drops one. Intent, Approach, Acceptance and Tasks must have text before check passes; Invariants, Non-goals, Risks and Changes may stay empty.

| Section | What it holds |
| --- | --- |
| Intent | what the ticket changes, in one paragraph |
| Approach | the strategy, and why it beats the alternative the owner considered |
| Invariants | what must stay true after every task, one `- ` line each, with what shows it |
| Non-goals | what the ticket leaves out, one `- ` line each, with its reason |
| Acceptance | the criteria, one `- ` line each, ending with the refs of the entries that require it |
| Tasks | the work, numbered in the order it is done |
| Risks | what could go wrong, empty until the review and the risk dialog |
| Changes | one line per revision after the first, saying what changed and the decision behind it |

A ref names a case entry through its case's alias: `C1.e4`, or `C2.T1.e2` for entry e2 of thread T1. Check reads every ref in the body: it must be an entry of its case, not retired by a later one. A criterion's refs must also be a `decision` or a `known`.

## Example

```markdown
---
id: 20261126-cap-retries
title: Cap the attempts of each job
status: accepted
revision: 2
created: 2026-11-26
head: 1a2b3c4
cases:
  C1: 20261126-retry-pool
  C2: 20261126-retry-limit
lights: "on"
epic: null
issue: null
---

# Cap the attempts of each job

## Intent

Retries stop starving the job pool: a job gives up after a fixed number of attempts, so new jobs keep their share of the workers.

## Approach

Cap the attempts of each job where the retry decision is made, and keep retries in the shared pool (C1.e2). A separate retry pool was considered and set aside by the owner.

## Invariants

- The test suite passes after each task, shown by the repository's own test command.

## Non-goals

- A separate pool for retries: the owner chose to keep one pool (C1.e2).
- Documenting the limit for operators: a ticket of its own, for a later plan.

## Acceptance

- A job that fails five times is not run a sixth time. (C1.e1, C2.e1)
- A job dropped after its last attempt is logged with its id. (C1.e3)

## Tasks

1. Count each attempt on the job record, where the retry decision is made.
2. Drop a job from the queue once its fifth attempt fails.
3. Log each dropped job with its id.

## Risks

- R1: A job dropped after its last attempt leaves the queue without a trace.
  - signal: a job leaves the queue with no error in the log
  - tasks: 2, 3
  - handling: mitigate, by the second criterion

## Changes

- r2: the cap moved from three attempts to five, as the owner decided after the review (C2.e1).
```

## Writing each section

From mightymodels `game-plan`, unless marked otherwise.

- **Altitude is not vagueness.** The plan says what and where, and what outcome shows it done. A task says what changes and where, never the code; detail waits until the task starts, against the code as it is then.
- **A criterion is an observable outcome sentence**: what a person or a test can see happen, with no ids and no commands, then its refs in parentheses. "Asking for a job that does not exist returns a not-found message instead of a stack trace" is one. "Error handling works correctly", "handles errors appropriately" and "is consistent with the rest of the code" are not: rewrite them or drop them. One to four criteria; a ticket that needs more is two tickets (break-it-down).
- **A task** is one change a reviewer could check alone, in the order it is done, and leaves the repository passing. Cut them by the `red-thread:break-it-down` skill.
- **An invariant** says what shows it holds: a test, a CI job or a read, in words. An invariant without that is a wish.
- **A non-goal** carries its reason, so a later session does not reopen it.
- **A risk** is one `- R<n>:` line with its subject named in full, then three nested lines: `signal`, the `tasks` it touches by number, and the `handling` the owner chose (`accept`, `mitigate, by` the criterion or task that does it, or `you intervene`). The `red-thread:risk-register` skill says how each is found and chosen.
- **No `path:line` in plan text.** A line number goes stale with the first task that lands and is trusted anyway. The citations live in the entries, and the plan reaches them through refs.

## From the interview

From mightymodels `game-plan`. Lift what the cross-examine interview settled into the plan before you write anything of your own:

- A decision becomes the approach, an invariant, a non-goal or a criterion. A decision that fits none of these is a task, or a sign that the work is more than one ticket.
- A verified fact becomes ground a criterion rests on, through its ref.
- An open question or an assumption goes on a list for the risk dialog, which adds it after the reviewer's risks, as risk-register describes. It stays out of the plan until then.

## Consistency check

From mightymodels `game-plan`. Run it before the owner sees the plan, together with `PLANNER check --plan PLAN`. Each item is a yes or no question.

- The plan has one to four criteria, and each is an observable outcome sentence.
- Each criterion follows from the entries it names: read each one on the board. An entry that says less than the criterion promises means a narrower criterion or a question for the owner.
- Every decision on the boards that bears on the intent shows in the plan as the approach, an invariant, a non-goal or a criterion, and nothing in the plan contradicts one.
- Every task can be done in the order written, and each criterion is met once the last task lands.
- Once risk-register has run, every open question and assumption from the cross-examine interview is a risk.
- No task does what a non-goal excludes.
- Every invariant says what shows it, and every non-goal its reason.
- Before the review, Risks is empty and `lights` is `null`. After risk-register, every risk has a signal someone can see while the work runs, the tasks it touches, and the handling the owner chose.
- No plan text carries a `path:line`.

## Showing the plan

At the gate, give the owner the path of PLAN and show the plan in your message, section by section as the file holds it, with each ref followed by its entry's kind: `(C1.e1 known, C2.e1 decision)`. When the plan revises an accepted one, open with what changed since that revision.

## Revising

A plan is edited in place. Until the owner accepts it, edit it freely. After that, each change the owner accepts adds one to `revision` and one line under Changes: `- r<n>: what changed, and the decision behind it (C1.e9)`. Git does not track `.red-thread/`, so the Changes lines are the plan's only history: write each so a reader who never saw the earlier text knows what it said.
