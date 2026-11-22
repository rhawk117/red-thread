# Lens: brief

Reader: a planning session that has not seen this work. It may be an agent without this plugin, or a person reading it inside an issue. From the brief and the lines it cites, the reader should be able to write an implementation plan.

Sections the script writes: Goal, Decided, Constraints (the `known` entries), Ruled out, Open, Pointers, How to read. Budget: 60 lines.

## Choosing

- `goal`: one or two sentences in terms of the decision the planner has to make. Put no findings here. Findings are entries, and an entry carries its citation.
- `include`: the knowns that bound the design, most constraining first, about twelve at most. Then every `ruled_out` entry a planner would otherwise chase, and every `open` entry. Leave out a known that only helped find the answer.
- `blocking`: the open entries planning cannot proceed without. If there are none, send an empty list so each open entry is labelled not blocking.

## Checklist

- A planner could start from this page without the conversation.
- The result of the investigation appears under Decided. If it does not, the owner has not accepted a conclusion yet: go back to the gate in investigate instead of writing the conclusion into the goal.
- Nothing in Goal claims more than the entries below it.
- No entry is flagged as a lead or as a changed citation without the owner knowing.

## Delivering

Give the owner the path. The next session starts by reading that file, then opens the citations it needs.
