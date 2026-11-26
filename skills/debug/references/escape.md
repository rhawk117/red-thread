# Escape: why it broke and why nothing caught it

Read this when the fix is in and the reproduction passes. It covers phase 6 and prepares the dialog of phase 7. The work is two or three lookups in one round, recorded like every other round. Keep it in proportion: for a one-line slip this phase is one lookup and three sentences.

## Why it broke

Find the change that introduced the defect, and separate it from the change that exposed it.

- `code-sense`: `git blame` on the lines the fix changed, and `git log -S` for the defective expression, to find the introducing commit and its message. If phase 4 bisected, the commit it named is where the failure began to show, which may be a different commit.
- From that commit, state the assumption that was false: what the author took for granted about an input, a caller, an order, a version or a default. Cite the line that shows it. If the history does not show it, the assumption is `open` with `rests_on`, not a story.
- Say whether the defect was live from the day it was written or lay dormant until something else changed. A dormant defect has two answers to "why did it break", and the owner needs both.

Record: a `known` for the introducing commit (cite `git show --stat COMMIT` or the `path:line`), and a `known` or an `open` for the assumption.

## Why nothing caught it

Walk the guards from the cheapest to the latest and give each one a verdict with a citation. Skip none silently: "no such guard here" is an answer.

| Guard | Lookup |
| --- | --- |
| type checker | does it run on this file, and could a type have expressed the false assumption |
| linter | is there a rule for this pattern, and is it enabled or suppressed here |
| unit tests | `code-lens`: which tests refer to the defective function, and does any of them reach the defective branch |
| integration and end-to-end tests | does any test run the real path, or is the failing part replaced by a mock or a fixture that differs from production |
| CI | does CI run those tests at all: markers, path filters, skipped or allowed-to-fail jobs |
| review | was the introducing change reviewed, and was the defect visible in its diff |
| runtime checks | an assertion, a validation or a log line on the path that would have shown it earlier |

Each guard gets one of four verdicts:

- **absent**: no such guard exists for this code.
- **not run**: it exists and did not run on this code or this change.
- **blind**: it ran and could not see the defect, because of a mock, a fixture, a type that was too wide, or a branch it never reached.
- **ignored**: it reported, and the report was suppressed, flaky or passed over.

Record each verdict that explains the escape as a `known` with its citation. A verdict you could not check is `open`.

## Class each finding

Every finding from the two sections above gets one class. Give your reason in a sentence at the close.

- **Slip.** A one-off mistake. A careful author with the regression test in place would not repeat it, and no guard short of the regression test is clearly worth its cost.
- **Gap.** A guard that could reasonably exist is absent, not run, blind or ignored, and adding or repairing it is a contained piece of work. Gaps become the guard candidates in phase 7.
- **Debt.** The structure of the code keeps producing this kind of defect, or makes the missing guard impractical to write. Signs: the same pattern is wrong or fragile in other places; the logic is duplicated and the copies have drifted; the code cannot be tested without mocking away the part that broke; a guard existed and was switched off because it was too noisy or too slow; the fix had to work around something instead of correcting it.

One cheap lookup separates a slip from debt: ask `code-sense` or `code-lens` whether the same pattern exists elsewhere in the area. Record what it finds. Do not go further than that one lookup. How widespread the debt is, and what to do about it, is an investigation of its own, and that is the owner's to start.

## Price each guard

For each gap, write one candidate guard, and prefer the cheapest layer that can see the whole class of defect: a type before a lint rule, a lint rule before a unit test, a unit test before an integration test, a test before a CI job, any of them before a process rule. For each candidate, state:

- **Catches**: this defect only, or the class it belongs to. Name the class.
- **Costs to build**: small (one file, under an hour), medium (several files or a new fixture) or large (new infrastructure, or a refactor first). Say what must exist before it can be written.
- **Costs to keep**: time added to every run, the chance of false alarms, and what has to be maintained when the code changes.
- **Your recommendation**: build it or not, and what would change your mind.

"Not worth it" is a real recommendation. The regression test from phase 5 already pins this defect. A guard earns its place only if it catches the class, or catches the defect earlier and more cheaply than that test does. A guard that costs more to keep than the failures it prevents is a new liability, so say so plainly when you think it is one. The owner decides.

## Hand debt to an investigation

For each debt finding, prepare what phase 7 asks the owner:

- The target, as one line the owner can disagree with, and its kind: `survey` for "how widespread is this and where", `research` for "how should this work", `root-cause` for "why does this keep happening".
- What the investigation would establish, and what decision that would serve.
- The entries of this case that it starts from, by ref.

Do not estimate the size of the debt or propose its remedy here. One instance and one lookup are not a survey, and a plan built on them would rest on facts nobody has checked.
