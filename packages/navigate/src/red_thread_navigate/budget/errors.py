"""Errors raised by the budget policy."""


class BudgetError(ValueError):
    pass


class BudgetBelowMinimumError(BudgetError):
    def __init__(self, *, budget: int, minimum: int) -> None:
        self.budget = budget
        self.minimum = minimum
        super().__init__(f'budget {budget} is below the minimum of {minimum} tokens')


class NoRungsError(BudgetError):
    def __init__(self) -> None:
        super().__init__('at least one rung is required')
