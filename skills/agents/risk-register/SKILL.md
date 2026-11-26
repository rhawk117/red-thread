---
name: risk-register
user-invocable: false
description: >-
  How a red-thread plan names its risks and how the owner chooses each one's handling: a risk with a signal someone can observe while the work runs, the tickets it touches, and a handling of accept, mitigate or you intervene, offered only where a senior engineer could pick it. Loaded by name from plan; not a command you run.
---

# Risk register

Every risk in a plan gets a handling the owner chooses, not you. A risk without one is a risk that whoever runs the work will handle by improvising. Put each question to the owner by the rules in `red-thread:cross-examine`, under "Putting a question to the owner"; load that skill first if you have not.

## Finding the risks

- Every question the design interview left open is a risk whose signal is what would settle it.
- Every assumption the interview made because its depth ran out is a risk whose signal is the assumption proving false.
- Every `open` entry on a board that a criterion would otherwise need is a risk.
- Anything else that could make a ticket land wrong: a caller nobody listed, a version the plan assumes, a change two worktrees both lean on.

## Writing a risk

- **The risk**: one sentence saying what could go wrong, with its subject named in full.
- **The signal**: something a person or a test can see happen while the work runs, not only after it. "A test or a caller expects a sixth attempt" is a signal; "things go wrong" is not.
- **The tickets**: the tickets it touches, by id.

## The handlings

- **Accept**: proceed, and note the signal. Nothing changes in the plan.
- **Mitigate**: show the change itself, so the owner judges a diff and not a promise: the criterion you would add to a named ticket, word for word, or the new ticket with its title, why and criteria. The criterion rests on the decision this dialog records.
- **You intervene**: work on the touched tickets stops when the signal appears, and the owner decides. Name which of the risk's tickets would be cut again.

Offer only the handlings a senior engineer could pick for this risk, each with its cost, the recommended one included. When only two are sensible, offer two. Do not fill the dialog with the full list: a fixed list of four is what padded the risk dialogs of mightymodels, where this rule came from (`game-plan`). Put up to four risks in one AskUserQuestion call.

## Recording

Record each answer as a `decision` with `source` `user` before you write it into the plan, in the case it bears on, as cross-examine records an answer. A mitigation's criterion names that decision in its `required_by`. The plan skill's draft reference gives the JSON shape of each handling.
