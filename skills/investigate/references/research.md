# Kind: research

Use to learn how something works, or what upstream documents, before a plan is written: a dependency's behavior, a protocol, a migration path, how a subsystem fits together.

## Framing

Name the subject and the question the plan depends on. Pin the version: what the repository uses now, or the version the owner means to move to.

Usual bar: both halves cited, meaning what upstream documents for the pinned version and the call sites here that depend on it. A cheaper bar: the documentation half only.

## Round 1

Pair a web scout with a code scout, sent together:

- `code-sense`: the pinned version of the subject (the lockfile line) and the call sites that depend on the behavior in question.
- `web-head`: what the documentation for that version says. Give it VERSION when you have it, and a LEAD that is a URL when you know one.

When the version is not known yet, send `code-sense` first, since a page for the wrong version only yields an inference.

## Recording

- A page that documents another version than the pinned one is INFERRED, with `rests_on` naming both versions.
- A page worth keeping for the next session is a `resource`: the URL in `cite`, and one line in `text` on what it is for.
- A gap between what the docs say and what the call sites assume is its own `open` entry with both citations. It is often the finding the plan needs most.

## Large subjects

When the subject splits into parts that do not depend on each other (several dependencies, several protocols, the two sides of an integration), propose one thread per part and give each to a `research-lead` after the owner approves the split.

Security questions follow the same shape: scouts read, and `lab-rat` runs an experiment only in its own worktree against local code.

## At the gate

Say what the plan can now assume, what it cannot, and which open entry would change the design if it went the other way.
