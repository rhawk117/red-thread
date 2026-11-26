"""The words a board uses, each with what it means, for the page's own glossary."""

from red_thread_core.documents import Term

BOARD_TERMS = (
    Term(
        word='Case',
        meaning=(
            'One investigation, kept in .red-thread/ with its ledger and this board. The board is'
            ' drawn from the ledger every time, never edited by hand.'
        ),
    ),
    Term(
        word='Bar',
        meaning='What would count as an answer: the case is done when the bar is met.',
    ),
    Term(
        word='Entry and ref',
        meaning=(
            'One recorded finding, question or step. Its ref, such as e4 or T1.e2, is its address,'
            ' and a link to board.html#e4 opens the board at that entry.'
        ),
    ),
    Term(
        word='Thread',
        meaning=(
            'A line of entries on one question, such as T1. An entry outside a thread belongs to'
            ' the case as a whole.'
        ),
    ),
    Term(
        word='Round',
        meaning='One pass of research by the scouts, and the review of what they found.',
    ),
    Term(
        word='Decided, known, hypothesis, open, ruled out',
        meaning=(
            'The kinds of entry: what the owner decided, a claim with a checked citation, an'
            ' explanation still to test, a question not settled yet, and a dead end.'
        ),
    ),
    Term(
        word='Citation',
        meaning=(
            'The file and lines a claim rests on. It reads ok while the lines still say what was'
            ' quoted, and moved, changed or missing once the code has drifted.'
        ),
    ),
    Term(
        word='Retired',
        meaning=(
            'An entry a later entry replaced. The ledger keeps it, and the board folds it away at'
            ' the bottom.'
        ),
    ),
    Term(
        word='Plans',
        meaning=(
            'The plans that rest on this case, each a page of tickets that cite its entries. The'
            ' list is read from .red-thread/plans/ every time the board is drawn.'
        ),
    ),
)
