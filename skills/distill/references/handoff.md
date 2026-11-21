# Lens: handoff

Reader: the person or agent who resumes this case, with the case file at hand. It gets pointers, not a narrative: the ledger already holds the detail.

Sections the script writes: Where this stands, Decided, Start here (the `next` entries), Open, Hypotheses, Pointers, How to read. Budget: 40 lines.

## Choosing

- `goal`: two sentences: what is established so far, and what the next round was going to ask.
- `include`: the `next` entries in the order to do them, then the open entries, then the hypotheses still standing. Leave the knowns out. The reader gets them from the board.
- `blocking`: the open entries that stop the next step.

If the case has no `next` entry, add them before exporting (`kind` `next`, `source` `primary`, one step each), because Start here is what the reader came for.

## Checklist

- Start here is not empty, and its first step can be done without asking anyone.
- Every decision the owner made is under Decided, so nobody reopens it by accident.
- Entries flagged as leads are expected: the reader verifies them again.

## Delivering

Give the path. Tell the reader that `/red-thread:investigate` resumes a case it finds under `.red-thread/`, and that the first thing to run is the check command under Pointers.
