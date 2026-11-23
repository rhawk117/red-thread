"""Errors raised when a slice address cannot be used."""

ADDRESS_FORMS = (
    'path/to/file.py#Symbol',
    'path/to/file.py#Outer.inner',
    'path/to/file.py#L12',
    'path/to/file.py#L12-L20',
)


class AddressError(ValueError):
    """Base of every slice address failure."""


class MalformedAddressError(AddressError):
    def __init__(self, *, text: str, reason: str) -> None:
        self.text = text
        self.reason = reason
        forms = ', '.join(ADDRESS_FORMS)
        super().__init__(f'address {text!r} is not valid: {reason}. Valid forms: {forms}')


class OutsideRootError(AddressError):
    def __init__(self, *, text: str, root: str) -> None:
        self.text = text
        self.root = root
        super().__init__(f'address {text!r} reaches outside the root {root}')
