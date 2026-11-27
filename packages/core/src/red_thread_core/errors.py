"""The one base every red-thread package's failures derive from, so a CLI can catch them all."""


class RedThreadError(Exception):
    pass
