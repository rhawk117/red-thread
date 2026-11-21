"""Splits the flags a scenario expects into the lead flags and the citation state labels."""

CITE_PREFIX = 'citation '
LEAD_PREFIX = 'lead, '
INTACT_STATE = 'ok'


def list_lead_flags(flags: tuple[str, ...]) -> list[str]:
    return [flag for flag in flags if flag.startswith(LEAD_PREFIX)]


def list_state_labels(flags: tuple[str, ...]) -> list[str]:
    labels = [flag.removeprefix(CITE_PREFIX) for flag in flags if flag.startswith(CITE_PREFIX)]
    return labels or [INTACT_STATE]
