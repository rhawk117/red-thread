"""The words a plan page uses, each with what it means, for the page's own glossary."""

from red_thread_core.documents import Term

PLAN_TERMS = (
    Term(
        word='Plan and revision',
        meaning=(
            'The work cut into tickets. Each revision is stored whole and never edited, so a'
            ' change is a new revision, and the page marks what changed since the one before.'
        ),
    ),
    Term(
        word='Case',
        meaning=(
            'An investigation recorded in .red-thread/, with its own board. The plan names each'
            ' case it rests on with an alias: C1, C2 and so on.'
        ),
    ),
    Term(
        word='Ref',
        meaning=(
            'The address of one entry in a case: C1.e4 is entry e4 of case C1, and C2.T1.e2 is'
            ' entry e2 of thread T1 in case C2.'
        ),
    ),
    Term(
        word='Decision and known',
        meaning=(
            'The two kinds of entry a plan can rest on: what the owner decided, and a claim'
            ' whose citation was opened and checked.'
        ),
    ),
    Term(
        word='Ticket',
        meaning=(
            'One pull request of work: what it is for, what must be true when it is done, and'
            ' the files it owns.'
        ),
    ),
    Term(
        word='Worktree',
        meaning=(
            'One git worktree and one stack of pull requests. Its tickets land in order, each on'
            ' the one before, and no two worktrees own the same file, so each can be built at'
            ' the same time as the others.'
        ),
    ),
    Term(
        word='Position',
        meaning="A ticket's place in its worktree's stack, counted from the bottom.",
    ),
    Term(
        word='Done when',
        meaning=(
            'The acceptance criteria: outcomes someone can observe once the ticket is done. Under'
            ' each is the entry that requires it, with its text and a link to its board.'
        ),
    ),
    Term(
        word='new, changed, unchanged',
        meaning='How a ticket compares with the same ticket in the revision before.',
    ),
    Term(
        word='Risk',
        meaning=(
            'What could go wrong, the signal that would show it, and its handling: mitigated by a'
            ' ticket, accepted, or you intervene and the tickets it touches are cut again.'
        ),
    ),
    Term(
        word='Lights on and off',
        meaning=(
            'Whether the owner is in the loop while the tickets are built. With the lights on,'
            ' they decide each fork in the road as it comes; with the lights off, they are away,'
            ' and a fork that would change what a ticket promises waits for them.'
        ),
    ),
    Term(
        word='Epic and issue',
        meaning=(
            'Where the plan and each ticket are published in the tracker. They read "not'
            ' published yet" until a publish step records them.'
        ),
    ),
)
