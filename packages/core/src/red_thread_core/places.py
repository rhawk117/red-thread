"""Where the pages of one .red-thread/ directory sit, and the relative links between them."""

PLAN_HOME = 'plans'
BOARD_PAGE = 'board.html'
PLAN_PAGE = 'plan.html'
PLAN_INDEX = 'plan.json'


def link_board(case_id: str, anchor: str = '') -> str:
    target = f'../../{case_id}/{BOARD_PAGE}'
    return f'{target}#{anchor}' if anchor else target


def link_plan(plan_id: str) -> str:
    return f'../{PLAN_HOME}/{plan_id}/{PLAN_PAGE}'
