---
name: break-it-down
user-invocable: false
description: >-
  How to cut planned work into tickets a reviewer can hold in their head: one pull request each, cut where the work already has a seam, stacked in worktrees that never share a file, with the repository passing after each ticket. Also how to put a split of one ticket to the owner. Loaded by name from game-plan and course-correction; not a command you run.
---

# Break it down

One ticket is one pull request a reviewer can hold in their head. A ticket past that size fails in a known way: whoever builds it runs out of room, the check proves half of it, and the reviewer gets a diff nobody can hold. Size is guidance, not a gate, and the owner decides whether to split. The rules come from mightymodels `break-it-down`, with the worktree rules of `docs/design.md` section 13.

## Cutting

- A ticket has one to four acceptance criteria. A ticket that needs more is two tickets.
- Cut where the work already has a seam, trying these in order:
  - by behaviour: criteria that can be proven apart go to different tickets;
  - by module: files that change for different reasons go to different tickets;
  - by order: what must land first, such as a schema before its callers or a helper before its users, is a ticket of its own, and the tickets that need it name it in `depends_on`.
- The repository passes after each ticket, not only after the last. A ticket that cannot be checked alone is not a ticket yet.
- Some work does not cut: one rename across thirty files is one change. Keep it whole and say why.

## Worktrees and stacks

A worktree is one git worktree and one stack of pull requests: its tickets land in order, each on the one before. Worktrees that own disjoint files run side by side.

- Tickets that depend on each other share a worktree. A dependency on a ticket in another worktree is refused.
- Two worktrees never own the same path. A ticket that cannot keep its files apart from another worktree joins that worktree. Two tickets in one worktree may own the same files.
- `dir/` owns everything under `dir`. An entry may use `*`, `?` and `**`, and may not be empty, absolute, climb with `..` or use `[ ]`.
- A change two worktrees both lean on, though they own different files (a shared interface, a schema, a setting), puts them in one worktree or gives one of them a risk.

## Splitting one ticket

When the owner asks to split a ticket, or a ticket fails the sizes above:

1. Find the cuts by the rules above. Every criterion of the original lands in exactly one piece, in its own words. A criterion that two pieces each need half of is two criteria: write both and say it was divided, because that changes what is promised. Every path the original owned lands in a piece.
2. Give the pieces new ids. The original's id is not reused, and each ticket that depended on the original names the piece that carries what it waited for.
3. Write the pieces out in full in your message: each one's id, title, why, criteria with their `required_by`, owned paths and dependencies. Below them, list what the split changes outside them: each dependency that moves, each criterion that was divided.
4. Ask with AskUserQuestion: split as shown, keep it as one ticket, or change the split (the owner says what through the free text). Nothing changes until the owner answers. A dialog that came back empty is not an answer: ask again.
5. On "split as shown", change the draft. On "keep it", change nothing. On "change the split", go back to step 1 with what the owner said.
