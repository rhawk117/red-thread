"""What every mermaid chart shares: the characters a label may keep and how wide it may run."""

import re
from textwrap import shorten

LABEL_WIDTH = 44
UNSAFE = re.compile(r"[^\w .,:/()+='-]")


def clean_label(text: str) -> str:
    return shorten(UNSAFE.sub(' ', text), width=LABEL_WIDTH, placeholder='...')
