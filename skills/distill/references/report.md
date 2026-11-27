# Lens: report

Reader: the owner or a team who want the whole picture: a root-cause write-up, a survey of technical debt, or an explanation of how something works.

Sections the script writes: Summary, Decided, Findings (the `known` findings), Hypotheses, Ruled out, Open, Next steps, Resources, Pointers, How to read. Budget: 200 lines.

## Choosing

- `title`: what the report is about, as the reader would name it.
- `goal`: up to four sentences: the conclusion in the terms of the bar, how sure the evidence makes it, and what is still open. Say nothing here that a finding below does not support, and do not state an inferred claim as fact.
- `include`: leave it out to show everything. For a survey, list the findings in the order the owner asked for, and say in the goal what the order rests on.
- `blocking`: the open findings that would change the conclusion.

## Checklist

- The summary matches what is under Decided and Hypotheses. A cause the owner has not accepted is a hypothesis, and the summary calls it one.
- Each ruled-out line says what refuted it.
- For a survey, each finding has its `next` finding, so the report says what to do as well as what is wrong.

## Delivering

Give the path. Add `--html` to the export for a page. Publish that page only for a case the owner chose to publish, or when they ask now, and publish it privately.
