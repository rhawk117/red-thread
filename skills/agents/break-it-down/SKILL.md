---
name: break-it-down
user-invocable: false
description: >-
  How to size planned work and cut it: whether it is one ticket a reviewer can hold in their head,
  where to cut it when it is not, the ordered tasks inside one ticket, each leaving the repository
  passing, and how to put a split to the owner. Loaded by name from game-plan and
  course-correction; not a command you run.
---

# Break it down

One ticket is one pull request a reviewer can hold in their head, and one plan covers one ticket. A ticket past that size fails in a known way: whoever builds it runs out of room, the check proves half of it, and the reviewer gets a diff nobody can hold. Size is guidance, not a gate, and the owner decides whether to split. The rules come from mightymodels `break-it-down`.

## One ticket or more

- A ticket has one to four acceptance criteria. Work that needs more is more than one ticket.
- Cut where the work already has a seam, trying these in order:
  - by behaviour: criteria that can be proven apart go to different tickets;
  - by module: files that change for different reasons go to different tickets;
  - by order: what must land first, such as a schema before its callers or a helper before its users, is a ticket of its own.
- The repository passes after each ticket, not only after the last. A ticket that cannot be checked alone is not a ticket yet.
- Some work does not cut: one rename across thirty files is one change. Keep it whole and say why.

An epic holds the tickets of a cut, and the skill that writes one is not built yet. Until it is, a plan covers the ticket the owner picks, and names each other ticket of the cut under Non-goals with the reason "a ticket of its own".

## Tasks

The tasks of a ticket are the order its work is done in.

- A task is one change a reviewer could check alone, and the repository passes after it.
- Order the tasks so each needs only what the tasks before it made: a schema before its callers, a helper before its users, a test before the change it pins when the owner asked for one first.
- A task says what changes and where, in words, never the code: the code is written against the tree as it is when the task starts.
- Every criterion is met once the last task lands. A criterion no task moves forward is a gap; a task that moves no criterion forward and keeps no invariant is a task to drop.

## Splitting

When the owner asks to split a ticket or a task, or one fails the sizes above:

1. Find the cuts by the rules above. Every criterion of the original lands in exactly one piece, in its own words. A criterion that two pieces each need half of is two criteria: write both and say it was divided, because that changes what is promised.
2. Write the pieces out in full in your message: for tickets, each one's title, criteria with their refs and tasks; for tasks, each one's words and place in the order. Below them, list what the split changes outside them: each criterion that was divided, each task that moves.
3. Ask with AskUserQuestion: split as shown, keep it whole, or change the split (the owner says what through the free text). Nothing changes until the owner answers. A dialog that came back empty is not an answer: ask again.
4. On "split as shown", change the plan: the pieces of a task replace it in the order; of a ticket, this plan keeps the piece the owner picks and names the others under Non-goals. On "keep it", change nothing. On "change the split", go back to step 1 with what the owner said.
