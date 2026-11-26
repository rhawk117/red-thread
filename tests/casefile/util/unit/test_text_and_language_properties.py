"""squeeze and rank_languages: the text it keeps and the languages it ranks."""

from collections import Counter

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.util import LANGUAGE_LIMIT, rank_languages
from red_thread_core.util import squeeze

WHITESPACE = (
    ' \t\n\r\x0b\x0c\x1c\x1d\x1e\x1f\x85\N{NO-BREAK SPACE}\N{LINE SEPARATOR}\N{PARAGRAPH SEPARATOR}'
)
LANGUAGE_BY_SAMPLED_SUFFIX = {
    '.py': 'Python',
    '.PY': 'Python',
    '.rs': 'Rust',
    '.go': 'Go',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript',
    '.java': 'Java',
    '.c': 'C',
    '.h': 'C',
    '.cc': 'C++',
}
UNKNOWN_SUFFIXES = ('.txt', '.md', '.lock', '')


def join_name(stem: str, suffix: str) -> str:
    return f'src/{stem}{suffix}'


class TestSqueeze:
    spaced = st.text(alphabet='abc' + WHITESPACE, max_size=40)

    @given(text=spaced)
    def test_squeezing_twice_changes_nothing(self, text: str) -> None:
        assert squeeze(squeeze(text)) == squeeze(text)

    @given(text=spaced)
    def test_the_result_has_no_edge_whitespace_and_only_single_plain_spaces(
        self, text: str
    ) -> None:
        squeezed = squeeze(text)

        assert squeezed == squeezed.strip()
        assert '  ' not in squeezed
        assert all(character == ' ' for character in squeezed if character.isspace())

    @given(text=spaced)
    def test_every_character_that_is_not_whitespace_is_kept_in_order(self, text: str) -> None:
        kept = ''.join(character for character in text if not character.isspace())

        assert squeeze(text).replace(' ', '') == kept


class TestRankLanguages:
    stems = st.from_regex(r'[a-z]{1,6}', fullmatch=True)
    files = st.lists(
        st.builds(join_name, stems, st.sampled_from(tuple(LANGUAGE_BY_SAMPLED_SUFFIX))),
        max_size=40,
    )
    unknown_files = st.lists(
        st.builds(join_name, stems, st.sampled_from(UNKNOWN_SUFFIXES)), max_size=10
    )

    def count(self, files: list[str]) -> Counter[str]:
        suffixes = (name[name.rindex('.') :] for name in files)
        return Counter(LANGUAGE_BY_SAMPLED_SUFFIX[suffix] for suffix in suffixes)

    @given(files=files)
    def test_the_ranking_holds_each_present_language_once_up_to_the_limit(
        self, files: list[str]
    ) -> None:
        ranked = rank_languages(files)

        counted = self.count(files)
        assert len(ranked) == min(LANGUAGE_LIMIT, len(counted))
        assert len(set(ranked)) == len(ranked)
        assert set(ranked) <= set(counted)

    @given(files=files)
    def test_the_ranking_runs_from_most_files_to_fewest_and_drops_only_the_least(
        self, files: list[str]
    ) -> None:
        ranked = rank_languages(files)

        counted = self.count(files)
        totals = [counted[language] for language in ranked]
        assert totals == sorted(totals, reverse=True)
        left_out = [counted[language] for language in counted if language not in ranked]
        assert all(total <= min(totals) for total in left_out)

    @given(files=files, unknown=unknown_files)
    def test_files_of_no_known_language_change_nothing(
        self, files: list[str], unknown: list[str]
    ) -> None:
        assert rank_languages([*files, *unknown]) == rank_languages(files)

    @given(files=files)
    def test_a_suffix_counts_the_same_in_any_letter_case(self, files: list[str]) -> None:
        assert rank_languages(name.upper() for name in files) == rank_languages(files)
