---
name: distill
argument-hint: '[brief|issue|handoff|report]'
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/redthread-casefile *)
description: >-
  Turns a red-thread case into one output for one reader: a brief of 60 lines or fewer for a
  planning session, a GitHub issue, a handoff for whoever resumes the work, or a report. The case
  file script assembles the output from the ledger, so every line is a finding's own words with its
  citation; you choose and rank what goes in.
when_to_use: >-
  Use after an investigation, or when the user says "write this up", "make a brief for the next
  session", "hand this off", "create an issue from what we found", "open a GitHub issue for this",
  "give me a report on the root cause", or "summarize the research so we can plan". Also use with
  no case open, to turn this conversation's findings into a case first. Not for finding out more
  (that is investigate).
---

# Distill

You turn a case file into one output for one reader. You choose which findings go in and in what order. The script writes every line from the ledger. The only prose you write is a title and a goal, because a summary written from memory drifts from the record and the reader cannot tell where.

Before you write a title, a goal or a finding, load the `red-thread:artifact-authoring` skill with the Skill tool. It covers how to word each one for a reader who was not in this conversation.

The owner's request: $ARGUMENTS

In this file, SCRIPT means:

```text
${CLAUDE_PLUGIN_ROOT}/bin/redthread-casefile
```

## Steps

1. Find the case: `ls .red-thread`. With one case, use it. With several, ask the owner which. With none, follow "With no case open" below first. CASE is the case directory.
2. Pick the lens. If the owner did not name one, ask with AskUserQuestion, giving the four lenses in the table below and who reads each.
3. Check before anything else: `SCRIPT check --case CASE`. If it reports a fault in a file of the case, fix each one as it says and run it again: render and export refuse a case they cannot read. If a citation is changed or missing, ask the owner whether to verify it again with investigate, export with the flag showing, or stop. The export flags such a finding and never hides it.
4. Read the record: `SCRIPT render --case CASE --full`.
5. Read the lens file from the table. It says who reads the output and how to choose.
6. Send a selection and export:

   ```sh
   SCRIPT export --case CASE --lens brief <<'EOF'
   {
     "title": "Cap retries in the job pool",
     "goal": "Plan the change that stops retries starving the pool. The owner accepted the cause in e9.",
     "include": ["e3", "T1.e2", "e7", "e5"],
     "blocking": ["e5"]
   }
   EOF
   ```

   Every key is optional:

   - `title`: the heading. Without it, the case target.
   - `goal`: one or two sentences for the first section. Without it, the target and the bar.
   - `include`: the finding ids to show, most important first. Without it, every live finding in ledger order. Decisions always appear.
   - `blocking`: the `open` finding ids the reader cannot proceed without. They sort first and each open finding is labelled blocking or not blocking.

   Add `--html` to also write the output as a page.
7. If the script says the output is over its budget, cut `include` and export again. The budget is the point: an output that grows to hold everything is a second ledger, and the reader already has the first.
8. Read the written file once and go through the lens file's checklist. To change the output, change the selection and export again. Do not edit the file: an edited output no longer matches the ledger. If the ledger itself is missing something, append the finding to `case.md` under a new round heading, the way step 2 of With no case open shows, run `check`, then export again.
9. Deliver as the lens file says, and tell the owner the path and the line count.

## Lenses

| Lens | Reader | Budget | File |
| --- | --- | --- | --- |
| `brief` | a planning session, human or agent, that has not seen this work | 60 lines | [references/brief.md](references/brief.md) |
| `issue` | maintainers on GitHub, who do not have the case file | 80 lines | [references/issue.md](references/issue.md) |
| `handoff` | the person or agent who resumes this case | 40 lines | [references/handoff.md](references/handoff.md) |
| `report` | the owner or a team who want the whole picture | 200 lines | [references/report.md](references/report.md) |

The budget counts lines that carry text.

## With no case open

Build the ledger from this conversation, then carry on from step 3.

1. Confirm the target, the kind and the bar with the owner in one AskUserQuestion dialog, then run `SCRIPT init --target "..." --kind KIND --bar "..."` from the repository root. KIND is `root-cause`, `claim`, `research` or `survey`. It prints CASE.
2. Write round 0 by hand: append the findings to `CASE/case.md`, below the `## Round 0` heading that `init` wrote, with a quoted heredoc so the shell leaves `$`, backticks and quotes as written. Each finding is a `### e<n>` heading, numbered from e1 with no gap, over a fenced yaml block:

   ````sh
   cat >> CASE/case.md <<'EOF'

   ### e1

   ```yaml
   kind: known
   text: The pool is sized from WORKERS, default 4
   source: primary
   verdict: VERIFIED
   cite: src/pool.py:41
   quote: WORKERS = int(os.environ.get("WORKERS", 4))
   ```
   EOF
   ````

   The fields are the ones the board shows: `kind`, `text`, `source`, `verdict`, `cite`, `quote` (the cited line, copied exactly), `rests_on`, `refute`, `supersedes` and `diagram`. A value that holds `: ` or ` #`, or starts with a quote mark or a bracket, goes in a block: the key, then `|-`, then the value indented on the next line. Then run `SCRIPT check --case CASE` and fix each fault it prints until it exits 0. What to write:

   - A fact with a `path:line` or URL that was opened in this conversation: `known`, with that `cite`, and for a `path:line` the line's text as `quote`. Check opens each `path:line` and faults one that does not resolve or whose quote is not on the line.
   - Something the owner decided: `decision`, with `source` `user`.
   - A dead end the owner named: `ruled_out`, with `source` `user`.
   - Every other claim: `open`, with `rests_on` saying it was stated in conversation and not verified.
3. Do not upgrade a claim to fit the output. An `open` finding in a brief tells the next session what to check first, which is worth more than a confident line that turns out wrong.

## Rules

- Peer review runs only when the owner asks for it here or chose "sufficient, verify first" at the gate in investigate. Do not start it on your own.
- Anything that leaves the machine needs the owner's go-ahead in this conversation: creating an issue, publishing a page, posting anywhere. Ask with AskUserQuestion and name the destination.
- Check faults text that matches a secret pattern, and export redacts it. The script cannot know what is private to the owner, so read an output that will be shared for internal names, hosts and customer data before you ask to send it.
