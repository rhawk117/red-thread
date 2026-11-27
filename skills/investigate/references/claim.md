# Kind: claim

Use for one statement to prove true or false: "the cache is never invalidated on delete", "we no longer call the v1 API", "this flag is dead".

## Framing

Restate the claim as one sentence that could be false, and say what would make it false. "The retry logic is bad" is not a claim yet. "Retries have no upper bound" is.

Usual bar: verified true or false with citations. A cheaper bar: no counter-example found in a named scope, recorded as inferred.

## Round 1

Two lookups, sent together:

- `code-sense` or `web-head`: the exact lines that would make the claim true.
- `code-sense`: the strongest counter-example, such as a second definition, an override in another config layer, a call through an alias, or a code path the claim forgot.

A claim about behavior at runtime ("is never called", "is read at startup") that reading cannot settle goes to `lab-rat` in round 2.

## Recording

- Each line that bears on the claim is a `known`.
- "No counter-example found" is `open` with `rests_on` naming the scope that was searched, because absence in one search is an inference.
- The claim's verdict is your judgment in chat. It becomes a `decision` only when the owner accepts it at the gate.

## At the gate

Say true, false or true with a condition, and name the finding ids it rests on. A claim usually takes one round. Recommend "sufficient, verify first" when the claim will be published or acted on in a way that is costly to undo.
