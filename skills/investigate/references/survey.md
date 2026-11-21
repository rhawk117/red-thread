# Kind: survey

Use for a wide look across an area: technical debt, risk, dead code, an audit before a rewrite.

## Framing

A survey has no natural end, so the owner sets the coverage: which directories or packages, which kinds of finding count, and how many findings are enough. Record that as the bar.

## Round 1: orientation

One `code-sense` lookup for the layout of the area: its packages, entry points, and which parts are large or change often (`git log` for the path). Then propose a thread per area. Three to five threads is usual. Ask the owner to approve the split before dispatching.

## Later rounds: one lead per thread

Give each `research-lead` its area as SCOPE, the kinds of finding that count, and a cap on findings. Tell it that a finding is recorded as:

- what and where: a `known` with the `path:line` in `cite`;
- why it happened, when history shows it: part of the same entry if `git log` or `git blame` supports it, or else an `open` entry with `rests_on`;
- what to do: a `next` entry that starts with the ref of the finding it addresses.

A finding without a citation is `open`. A survey of impressions is worth less than five cited findings.

## At the gate

Show coverage per thread: done, partial or untouched, with the count of findings. Ask which threads advance. Rank findings only when the owner asks, and say what the ranking rests on.

Stop when the coverage the owner set is reached, even if more could be found. The rest is one `next` entry per area left out.
