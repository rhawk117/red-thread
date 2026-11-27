# red-thread-plans

The plan side of red-thread: the plan of one ticket, a Markdown file whose acceptance criteria are required by decisions and known facts recorded in one or more investigations (cases). It depends on `red-thread-casefile` to read the cases a plan cites, and never writes into a case directory.

The skills run it through `bin/redthread-plan`, which starts it with `uv run --no-project` so that nothing is installed into the repository under investigation.

## The plan file

A plan lives beside the cases, in the repository under investigation:

```text
.red-thread/tickets/<plan-id>/plan.md
```

A plan id is the UTC date and a slug of the title, such as `20261126-cap-retries`. The file opens with YAML frontmatter between `---` lines, which the scripts read, and the body holds the sections a person reads:

```markdown
---
id: 20261126-cap-retries
title: Cap the attempts of each job
status: draft
revision: 1
created: 2026-11-26
head: 1a2b3c4
cases:
  C1: 20261126-retry-pool
lights: null
epic: null
issue: null
---

# Cap the attempts of each job

## Intent
## Approach
## Invariants
## Non-goals
## Acceptance

- A job that fails five times is not run a sixth time. (C1.e1, C1.e2)

## Tasks
## Risks
## Changes
```

`status` is `draft`, `accepted` or `done`. `lights` is `"on"` when the owner is in the loop while the work runs and `"off"` when they are away, written with the quotes because YAML reads a bare `on` or `off` as a boolean. `cases` gives each case the plan rests on an alias, and a finding id names a finding through it: `C1.e4` is finding `e4` of case C1, and `C2.T1.e2` is finding `e2` of thread T1 in case C2. Each `- ` line under Acceptance is a criterion, and ends with the finding ids of the live `decision` or `known` findings that require it.

The plan is edited in place. Once it is accepted, each change adds one to `revision` and a line under Changes.

The section headings, in order, and the ones `check` refuses to find empty are in `src/red_thread_plans/assets/outline.yaml`.

## Commands

| Command | What it does |
| --- | --- |
| `init --title T --case ID [--case ID ...] [--slug S] [--root R]` | writes `plan.md` with its frontmatter and its section headings, and prints its path. It refuses no case, a case that is not under `.red-thread/`, and a plan that exists already |
| `check --plan PATH` | reads the plan, or the `plan.md` in a directory, against its cases and names every fault with its line and its fix. It writes nothing |

`check` refuses a frontmatter that does not decode, with an unknown key or a bare `lights` value among the reasons, at the first fault. A readable plan is checked whole: no case or a case missing from `.red-thread/`, an accepted or done plan with no `lights`, a missing section heading, Intent, Approach, Acceptance or Tasks left empty, no criterion, a criterion with no finding id, a finding id that is unknown or retired anywhere in the body, and a criterion finding id that is not a `decision` or `known`.
