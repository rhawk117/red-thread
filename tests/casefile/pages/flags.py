"""Splits the flags a scenario expects into the lead flags and the citation state labels."""

from red_thread_casefile.views import CITE_FLAG_PREFIX, LEAD_FLAG_PREFIX

INTACT_STATE = 'ok'


def list_lead_flags(flags: tuple[str, ...]) -> list[str]:
    return [flag for flag in flags if flag.startswith(LEAD_FLAG_PREFIX)]


def list_state_labels(flags: tuple[str, ...]) -> list[str]:
    labels = [
        flag.removeprefix(CITE_FLAG_PREFIX) for flag in flags if flag.startswith(CITE_FLAG_PREFIX)
    ]
    return labels or [INTACT_STATE]
