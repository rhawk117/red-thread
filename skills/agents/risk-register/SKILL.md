---
name: risk-register
user-invocable: false
description: >-
  How a red-thread plan names its risks and how the owner chooses each one's handling: risks taken from a reviewer who never heard the plan's reasoning when there was a review, each with a signal someone can observe while the work runs, the tickets it touches and what it rests on, and a handling of accept, mitigate or you intervene, each described as fairly as its advocate would. Loaded by name from game-plan; not a command you run.
---

# Risk register

Every risk in a plan gets a handling the owner chooses, not you. A risk without one is a risk that whoever runs the work will handle by improvising. Put each question to the owner by the rules in `red-thread:cross-examine`, under "Putting a question to the owner"; load that skill first if you have not.

You drafted the plan, so you are the worst-placed reader to say what is wrong with it. Your framing leaks into how a risk is worded and into how its handlings are described: a risk you would rather accept comes out small, and a handling you would rather not do comes out costly. The rules below keep the risks in an outside reader's words and the handlings even.

## Where the risks come from

- **After a review.** The reviewer's risks are the register. Keep each one's risk and signal in the reviewer's words; fix only an id that names no ticket of the plan. Do not merge, soften or drop one: if you think a risk is wrong, say so in its question, with your evidence, and let the owner choose accept.
- **What the interview left open.** Add, after the reviewer's, every question the design interview left open and every assumption it made because its depth ran out, when the reviewer did not already name it. The signal of an open question is what would settle it; the signal of an assumption is it proving false. Mark each as yours.
- **Without a review.** Write the risks yourself, from the draft and the interview: an `open` entry a criterion would otherwise need, a caller nobody listed, a version the plan assumes, a change two worktrees both lean on. Say in the first risk question that a reviewer did not check them.

## Writing a risk

- **The risk**: one sentence saying what could go wrong, with its subject named in full.
- **The signal**: something a person or a test can see happen while the work runs, not only after it. "A test or a caller expects a sixth attempt" is a signal; "things go wrong" is not.
- **The tickets**: the tickets it touches, by id.
- **The ground**: what it rests on, shown in the question and not stored in the plan: an entry ref, a `path:line` or the reviewer's finding. A risk you cannot ground is a guess; say so.

State a risk so that the person who built the plan and the person who doubts it would both call it fair: no "might possibly", no "unlikely", no word that sizes it before the owner does.

## The handlings

- **Accept**: proceed, and note the signal. Nothing changes in the plan.
- **Mitigate**: show the change itself, so the owner judges a diff and not a promise: the criterion you would add to a named ticket, word for word, or the new ticket with its title, why and criteria. The criterion rests on the decision this dialog records.
- **You intervene**: work on the touched tickets stops when the signal appears, and the owner decides. Name which of the risk's tickets would be cut again.

Offer only the handlings a senior engineer could pick for this risk. When only two are sensible, offer two. Do not fill the dialog with the full list: a fixed list of four is what padded the risk dialogs of mightymodels, where this rule came from (`game-plan`). Put up to four risks in one AskUserQuestion call.

## Describing the handlings fairly

- Write each handling as the engineer who would pick it would put it: what it buys, at its strongest.
- A cost is something the handling itself causes: work, time, a setting to maintain, a wait for the owner. "Does not get the benefit of the recommended handling" is not a cost; it restates the recommendation.
- No loaded words on the handlings you do not recommend ("silently", "blindly", "just", "hope"). Accept is a real choice: it costs nothing now and pays only if the signal appears.
- Give the recommended handling's worst realistic outcome, not only its upside.
- Before you send, read the options side by side: the same length, a cost on each, and nothing in one that is only there to make another look better.

## Recording

Record each answer as a `decision` with `source` `user` before you write it into the plan, in the case it bears on, as cross-examine records an answer. A mitigation's criterion names that decision in its `required_by`. The game-plan skill's draft reference gives the JSON shape of each handling.
