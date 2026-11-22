"""Small text helpers the case file shares."""

from collections import Counter
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

LANGUAGE_LIMIT = 5
LANGUAGE_BY_SUFFIX: Mapping[str, str] = MappingProxyType({
    '.py': 'Python',
    '.rs': 'Rust',
    '.go': 'Go',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript',
    '.java': 'Java',
    '.kt': 'Kotlin',
    '.rb': 'Ruby',
    '.c': 'C',
    '.h': 'C',
    '.cc': 'C++',
    '.cpp': 'C++',
    '.hpp': 'C++',
    '.cs': 'C#',
    '.swift': 'Swift',
    '.php': 'PHP',
    '.scala': 'Scala',
    '.lua': 'Lua',
    '.ex': 'Elixir',
    '.zig': 'Zig',
    '.sh': 'Shell',
    '.sql': 'SQL',
    '.tf': 'Terraform',
})


def squeeze(text: str) -> str:
    return ' '.join(text.split())


def rank_languages(files: Iterable[str]) -> tuple[str, ...]:
    suffixes = (PurePosixPath(name).suffix.lower() for name in files)
    counted = Counter(
        LANGUAGE_BY_SUFFIX[suffix] for suffix in suffixes if suffix in LANGUAGE_BY_SUFFIX
    )
    return tuple(language for language, _ in counted.most_common(LANGUAGE_LIMIT))
