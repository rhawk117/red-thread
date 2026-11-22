---
name: distill
description: >-
  Turns a red-thread case into one output for one reader: a brief of 60 lines or fewer for a
  planning session, a GitHub issue, a handoff for whoever resumes the work, or a report. The case
  file script assembles the output from the ledger, so every line is an entry's own words with its
  citation; you choose and rank what goes in.
when_to_use: >-
  Use after an investigation, or when the user says "write this up", "make a brief for the next
  session", "hand this off", "create an issue from what we found", "open a GitHub issue for this",
  "give me a report on the root cause", or "summarize the research so we can plan". Also use with
  no case open, to turn this conversation's findings into a case first. Not for finding out more
  (that is investigate).
argument-hint: '[brief|issue|handoff|report]'
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/casefile.sh *)
---

# Distill

You turn a case file into one output for one reader. You choose which entries go in and in what order. The script writes every line from the ledger. The only prose you write is a title and a goal, because a summary written from memory drifts from the record and the reader cannot tell where.

The owner's request: $ARGUMENTS

In this file, SCRIPT means:

```text
${CLAUDE_PLUGIN_ROOT}/scripts/casefile.sh
```

## Steps

1. Find the case: `ls .red-thread`. With one case, use it. With several, ask the owner which. With none, follow "With no case open" below first. CASE is the case directory.
2. Pick the lens. If the owner did not name one, ask with AskUserQuestion, giving the four lenses in the table below and who reads each.
3. Check before anything else: `SCRIPT check --case CASE`. If a citation is changed or missing, ask the owner whether to verify it again with investigate, export with the flag showing, or stop. The export flags such an entry and never hides it.
4. Read the record: `SCRIPT render --case CASE --full`.
5. Read the lens file from the table. It says who reads the output and how to choose.
6. Send a plan and export:

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
   - `include`: the refs to show, most important first. Without it, every live entry in ledger order. Decisions always appear.
   - `blocking`: the `open` refs the reader cannot proceed without. They sort first and each open entry is labelled blocking or not blocking.

   Add `--html` to also write the output as a page.
7. If the script says the output is over its budget, cut `include` and export again. The budget is the point: an output that grows to hold everything is a second ledger, and the reader already has the first.
8. Read the written file once and go through the lens file's checklist. To change the output, change the plan and export again. Do not edit the file: an edited output no longer matches the ledger. If the ledger itself is missing something, add the entry with `SCRIPT add`, then export again.
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
2. Record round 0 in one batch with `SCRIPT add --case CASE --round 0`, a JSON array on standard input:
   - A fact with a `path:line` or URL that was opened in this conversation: `known`, with that `cite`. The script opens each `path:line` and rejects one that does not resolve.
   - Something the owner decided: `decision`, with `source` `user`.
   - A dead end the owner named: `ruled_out`, with `source` `user`.
   - Every other claim: `open`, with `rests_on` saying it was stated in conversation and not verified.
3. Do not upgrade a claim to fit the output. An `open` entry in a brief tells the next session what to check first, which is worth more than a confident line that turns out wrong.

## Rules

- Peer review runs only when the owner asks for it here or chose "sufficient, verify first" at the gate in investigate. Do not start it on your own.
- Anything that leaves the machine needs the owner's go-ahead in this conversation: creating an issue, publishing a page, posting anywhere. Ask with AskUserQuestion and name the destination.
- The script redacts text that matches a secret pattern. It cannot know what is private to the owner, so read an output that will be shared for internal names, hosts and customer data before you ask to send it.
