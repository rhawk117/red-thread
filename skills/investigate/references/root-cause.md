# Kind: root cause

Use for a failure, a slowdown or a wrong result whose cause is unknown.

## Framing

State the symptom as observed: what happens, where, since when, and what was expected. A symptom the owner cannot state yet is the first open question, not something to guess.

Usual bar: one hypothesis survives a test that could have refuted it, and each rival is ruled out with a citation. A cheaper bar the owner may prefer: the failing code path is located and cited, with the cause still a hypothesis.

## Round 1

Ask where, before why:

- `code-sense`: the code path from the symptom (the error text, the endpoint, the job name) to the lines that produce it.
- `code-sense` or `web-head`: the runtime configuration that path reads, and the pinned versions of the dependencies on it.
- `code-sense`, when the symptom has a start date: `git log` for the path over that period.

Then record at least two rival explanations as `hypothesis` entries, each with `refute`: the observation that would prove it wrong. One hypothesis alone gets confirmed by whatever turns up next. Rivals keep the evidence honest.

## Later rounds

For each live hypothesis, pick the cheapest test that could refute it:

- A line can refute it: a `code-sense` or `web-head` lookup.
- Only a run can refute it: `lab-rat`, with HYPOTHESIS and REFUTE copied from the entry. Start EXPERIMENT with `git checkout --detach SHA`, where SHA is the commit under test (`git rev-parse HEAD`). By default a worktree branches from the repository's default branch, not from your HEAD, and it holds committed files only.

Fold the result:

- Refuted: a `ruled_out` entry with the command or line in `cite` and the hypothesis ref in `supersedes`.
- Survived: the hypothesis stays. Add a `known` only for what the experiment observed directly, with the command in `cite`. A hypothesis that survived one test is not proven.
- A cause seen only as a correlation, such as a commit near the start date, is `open` with `rests_on`.

## At the gate

Show the hypotheses as three groups: survived a test, ruled out, not yet tested. Recommend "sufficient" only when one survived and no rival is untested. Recommend "sufficient, verify first" when a fix that is costly to undo will rest on the answer.

Record a fix the evidence points at as a `next` entry. This kind ends at the cause.
