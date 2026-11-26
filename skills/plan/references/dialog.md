# The planning dialogs

Two dialogs put the plan's choices to the owner: the design dialog before you draft, and the risk dialog after. Both use AskUserQuestion only. When no dialog is available, ask in chat in the same shape, numbered with the options listed and one recommended, and wait for the answers.

## Talking to the owner

From mightymodels `game-plan` and `cross-examine`. The owner has not read the cases line by line or seen your tool output, and a dialog may be all they read. They are a senior engineer who has watched work like this go wrong, so write to let them use that.

- **Name things.** Say what a ticket, an entry or a risk is, with its id after it: "the ticket that caps retries (`retry-cap`)", "the owner's choice to keep one pool (C1.e2)". An id never stands alone.
- **Weigh the decision.** Open each question with what it drives: what gets built differently on each answer, and how hard that is to undo. A choice that is cheap to reverse gets a line per option. A choice that fixes a boundary, a public shape or stored data gets the entries that bear on it.
- **Stack the options evenly.** Two to four options, written as the actual choices. Each says what it buys and what it costs, the recommended one included, at the same length. Before you send a question, check that someone who favours each option would call its description fair, and that you can name a real cost of the one you recommend. Drop an option nobody would pick.
- **Recommend one.** Mark exactly one option recommended, and say which cost you judge worth paying and what fact would change your answer.
- **Use their answer.** A typed answer that names a problem you did not list is a finding: check it with a scout if it is a fact, and ask again with it included.

## The design dialog

From mightymodels `cross-examine`. A plan drafted from a vague intent is a plan you wrote and the owner nodded at. This dialog moves the deciding to the owner before anything is drafted.

### Depth first

Open with one dialog of two questions:

- **Depth**: Skim (one round, the top of the tree; everything below is assumed and listed), Standard (up to three rounds), or Relentless (rounds until nothing is left to ask).
- **Width**: every question that can be asked now, in dialogs of up to four, or one question per dialog. One at a time is slower and easier to steer; offer it without recommending it.

### The frontier

Map the plan as a tree of decisions, where each decision branches into the ones that hang off it. The frontier is every decision whose prerequisites are settled. Ask the frontier, wait for the answers, then work out the next frontier. A question whose answer depends on another question still open belongs to the next round, because asking it now makes the owner answer under an assumption they have not made.

A decision already on a board is settled. Do not ask it again; build on it.

Three kinds of question reach the frontier, and only one goes to the owner:

- **Facts** (what the code does, where a setting lives, what a library defaults to) go to a scout, as investigate sends them: `code-lens` or `code-sense` for this repository, `web-head` for documented behaviour. Record a VERIFIED answer as a `known` in the case it bears on, and an INFERRED one as an `open` with its `rests_on`. Only the questions downstream of a running scout wait for it.
- **Decisions** (which behaviour, which boundary, which trade-off, what done looks like) go to the owner.
- **Feel** (how an interaction should feel) does not settle by question. Record it as open, "needs a prototype", and move on.

Pitch the questions at what the plan needs: the outcome and what shows it is reached, what must stay true throughout, what is out of scope, which work must land before which, which work can run side by side, and the owner's appetite for each trade-off.

```text
How many attempts does a job get before it is dropped? It sets the criterion of the ticket that caps
retries, and the limit becomes a documented setting, so changing it later is a breaking change.
  A fixed limit of 5 (recommended)
    buys: matches the current check in retry(); one test covers it
    costs: a slow downstream service can hold a worker through five attempts
  A setting with a default of 5
    buys: operators can tune it without a release
    costs: one more setting to document and to test at both ends
  I don't know
Recommended because the pool is small and nobody has asked to tune it. A second consumer with
different limits would move this to the setting.
```

In the dialog, the weight goes in the question text and each option's buys and costs in its description. The last option is always "I don't know". It means the question is a fact (send a scout) or needs a prototype, and it stays open.

### Recording the answers

After each round, record every answer as a `decision` with `source` `user`, in one `SCRIPT add` batch per case, at the round after the one the case's board header shows. Put each decision in the case it bears on; a choice that spans two cases goes in the first case the plan cites. Write the decision as the choice itself, a sentence a criterion can rest on: "Cap retries at five attempts per job", not "Option 1" or "the owner agreed".

Then restate where the dialog stands in a few lines: what was decided, by ref; what is open and why; what was assumed because the depth ran out; and the next frontier.

### Ending

The dialog ends when the frontier is empty, when the depth's round cap is reached, or when the owner says stop. Close with one question: the understanding is shared, one more round, or stop here. Draft only after the first. If the questions are getting worse, say so and recommend stopping where you are.

### Into the draft

From mightymodels `game-plan`. Lift the dialog into the draft before you write anything of your own:

- A decision becomes the approach, an invariant, a non-goal, or a criterion of the ticket it bears on. A decision that fits none of these is a ticket.
- A verified fact becomes ground a criterion rests on, through its ref.
- An open question becomes a risk whose signal is what would settle it.
- An assumption becomes a risk whose signal is the assumption proving false, so the risk dialog covers every assumption the depth left unexamined.

## The risk dialog

From mightymodels `game-plan`, as `docs/design.md` section 13 changed it. Every risk in the draft gets a handling the owner chooses. Each states the risk, a signal someone can observe while the work runs and not only after it, and the tickets it touches.

The handlings a risk can have:

- **Accept**: proceed, and note the signal. In the draft: `{"kind": "accept"}`.
- **Mitigate**: show the change itself, so the owner judges a diff and not a promise: the criterion you would add to a named ticket, word for word, or the new ticket with its title, why and criteria. In the draft: `{"kind": "mitigate", "ticket": "...", "criterion": "..."}`, with `criterion` left out when the ticket itself is the mitigation.
- **You intervene**: work on the touched tickets stops when the signal appears, and the owner decides. Name the tickets that would be cut again. In the draft: `{"kind": "you-intervene", "recut": [...]}`, where `recut` holds some of the risk's own tickets.

Offer only the handlings a senior engineer could pick for this risk, each with its cost, the recommended one included. When only two are sensible, offer two. Do not fill the dialog with the full list: a fixed list of four is what padded mightymodels' risk dialogs. Put up to four risks in one AskUserQuestion call.

Record each answer as a `decision` before you write it into the draft, as the design dialog does. A mitigation adds a criterion, and that criterion's `required_by` names this decision.
