"""Slice addresses: the file and the symbol or lines an agent asked for."""

from red_thread_navigate.address.domain import (
    Address,
    LineTarget,
    SymbolTarget,
    Target,
    parse_address,
)
from red_thread_navigate.address.errors import (
    ADDRESS_FORMS,
    AddressError,
    MalformedAddressError,
    OutsideRootError,
)

__all__ = [
    'ADDRESS_FORMS',
    'Address',
    'AddressError',
    'LineTarget',
    'MalformedAddressError',
    'OutsideRootError',
    'SymbolTarget',
    'Target',
    'parse_address',
]
