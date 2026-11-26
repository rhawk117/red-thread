"""Small text helpers every package shares."""


def squeeze(text: str) -> str:
    return ' '.join(text.split())
