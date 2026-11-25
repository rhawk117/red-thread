# Duplication and sources-of-truth audit

Date: 2026-11-25. Baseline: the working tree at `193868f`, plus uncommitted edits in 20 files. Scope: `packages/`, `tests/`, `hooks/roster.py`, `conftest.py`, `.github/actions/test-suite/pytest_ci.py`.

## How this was produced

- Six `python-harness:pylens` agents ran over import-graph clusters (casefile core, casefile presentation, navigate, two casefile test halves, and navigate/plugin tests with tooling). Each answered the same four questions: duplication, conflicting sources of truth, missing abstraction and hand-rolled stdlib.
- An AST clone scan (normalized function bodies and statement windows), a module-constant and string-literal cross-reference, and a hand-rolled-stdlib pattern scan ran over every `.py` file.
- `python-harness:pep-talk` ruled each stdlib candidate against the Python 3.14 docs: drop-in, partial or none.
- The high-impact rows were re-read at their cited lines. `typing.get_args` equality was confirmed by running it. Line estimates are rough and count code lines only.

## Summary

| Section | Items | Est. lines removed |
| --- | --- | --- |
| 1. Conflicting sources of truth (prod) | 12 | ~40, mostly a single owner rather than fewer lines |
| 2. Duplication / missing abstraction (prod) | 10 | ~150 |
| 3. Duplication in tests | 7 | ~200 |
| 4. Duplication the project rules require (needs an owner decision) | 3 | 0 to ~60 |
| 5. Hand-rolled stdlib | 78 sites ruled (see 5.4) | ~30 |

Suggested order: section 1 (bugs hide there), then 3.1, 3.2 and 2.1 (largest line wins), then section 5 drop-ins as a mechanical sweep.

______________________________________________________________________

## 1. Conflicting sources of truth

### 1.1 The CLI program name has three spellings (values disagree)

| Site | Value |
| --- | --- |
| `packages/casefile/src/red_thread_casefile/cli.py:21` | `PROGRAM = 'casefile'` (prefix of every error line and the cyclopts app name) |
| `packages/casefile/pyproject.toml:16` | script `red-thread-casefile` |
| `packages/casefile/src/red_thread_casefile/lenses.py:217` | tells the reader to run `redthread-casefile check` (the `bin/` launcher) |
| `packages/navigate/src/red_thread_navigate/cli.py:18` | `PROGRAM = 'red-thread-navigate'` (the distribution name, unlike casefile) |

Fix: pick the name agents type, which is the `bin/` launcher (`redthread-casefile`, `redthread-navigate`). Set `PROGRAM` to it in both CLIs and have `packages/casefile/src/red_thread_casefile/lenses.py:217` interpolate `PROGRAM`. Decide whether `[project.scripts]` follows (that edit touches a `pyproject.toml`, so ask first).

### 1.2 Literal aliases and hand-written tuples of the same members (5 pairs plus 1 map)

| Alias | Tuple copy |
| --- | --- |
| `packages/casefile/src/red_thread_casefile/domain.py:11` `EntryKind` | `packages/casefile/src/red_thread_casefile/domain.py:16` `ENTRY_KINDS` |
| `packages/casefile/src/red_thread_casefile/domain.py:12` `Verdict` | `packages/casefile/src/red_thread_casefile/domain.py:25` `VERDICTS` |
| `packages/casefile/src/red_thread_casefile/domain.py:13` `CaseKind` | `packages/casefile/src/red_thread_casefile/domain.py:26` |
| `packages/casefile/src/red_thread_casefile/lenses.py:24` `LensName` | `packages/casefile/src/red_thread_casefile/lenses.py:27` `LENS_NAMES` |
| `packages/casefile/src/red_thread_casefile/policy.py:25` `CiteState` | `packages/casefile/src/red_thread_casefile/policy.py:32` `CITE_STATES` |
| `packages/navigate/src/red_thread_navigate/symbols/domain.py:9` `SymbolKind` | `packages/navigate/src/red_thread_navigate/symbols/store/treesitter.py:24` `KINDS`, an identity map that leaves out `'property'` without saying why |

Every pair agrees today (`get_args(EntryKind.__value__) == ENTRY_KINDS` and the same check for `Verdict` both print `True`). Nothing keeps them in sync, though.

Fix: `ENTRY_KINDS: tuple[EntryKind, ...] = typing.get_args(EntryKind.__value__)`, and the same for each pair. Replace `KINDS` with a frozenset built the same way, minus `'property'`, and name that exclusion.

### 1.3 The Draft field list is defined in four places

- `packages/casefile/src/red_thread_casefile/domain.py:86`: `Draft` fields `kind` through `supersedes`
- `packages/casefile/src/red_thread_casefile/domain.py:109`: `Entry` repeats the same 11 fields and adds `seq`, `round`, `at`, `head` and `thread`
- `packages/casefile/src/red_thread_casefile/schemas.py:24`: `OPTIONAL_TEXT_FIELDS` and `DRAFT_FIELDS` at `packages/casefile/src/red_thread_casefile/schemas.py:25`
- `packages/casefile/src/red_thread_casefile/services/casefile.py:27`: `TEXT_FIELDS` spells out the same names plus `text`

Fix: derive the field-name tuples from `dataclasses.fields(Draft)` (minus `position`), and keep the "optional text" subset in one place, in `schemas.py`, with `services/casefile.py` importing it. Adding a field then takes one edit plus the struct.

### 1.4 Line splitting has three rules

- `LINE_BREAK = re.compile(r'\r\n|\r|\n')` is copied verbatim at `packages/navigate/src/red_thread_navigate/slice/services.py:47`, `packages/navigate/src/red_thread_navigate/symbols/store/python.py:17` and `packages/navigate/src/red_thread_navigate/symbols/store/treesitter.py:22`.
- `str.splitlines()` is used at `packages/casefile/src/red_thread_casefile/lenses.py:119` and `packages/navigate/src/red_thread_navigate/slice/views.py:44`.
- `existing.split('\n')` is used at `packages/casefile/src/red_thread_casefile/store.py:177`.

Fix: put one `split_lines(text)` in `packages/navigate/src/red_thread_navigate/util.py` and import it in all three navigate modules. Keep the regex there: pep-talk confirms `str.splitlines` also breaks on VT, FF, FS, GS, RS, NEL, LS and PS, which would shift line numbers against tree-sitter and `ast`. Change `packages/casefile/src/red_thread_casefile/store.py:177` to `splitlines()`.

### 1.5 Date width: two constants and one bare literal

`DATE_WIDTH = 10` appears at `packages/casefile/src/red_thread_casefile/pages.py:25` and `packages/casefile/src/red_thread_casefile/boards.py:25`, and `packages/casefile/src/red_thread_casefile/domain.py:39` uses a bare `created[:10]`. Fix: one `date_of(timestamp)` helper in `domain.py` (see 5.2 for the `datetime` option).

### 1.6 The head placeholder disagrees: `'none'` vs `'no commit'`

`packages/casefile/src/red_thread_casefile/boards.py:26` sets `NOTHING = 'none'` and `packages/casefile/src/red_thread_casefile/views.py:179` repeats the literal `'none'`, while `packages/casefile/src/red_thread_casefile/views.py:122` uses `'no commit'` for the same missing-head fact. The `[:SHORT_HEAD]` slice is repeated 3 times. Fix: one `short_head(head: str | None) -> str` in `domain.py`.

### 1.7 Cite-state subsets live outside the policy that owns the states

`packages/casefile/src/red_thread_casefile/views.py:18` (`FAILING_STATES`) and `packages/casefile/src/red_thread_casefile/views.py:19` (`QUIET_STATES`) partition `CITE_STATES` from `packages/casefile/src/red_thread_casefile/policy.py:32`, and `packages/casefile/src/red_thread_casefile/pages.py:104` hard-codes `'moved'`. Fix: move both subsets into `policy.py` beside `CITE_STATES`.

### 1.8 The state directory `.red-thread` is spelled in three modules

`packages/casefile/src/red_thread_casefile/cli.py:118`, `packages/casefile/src/red_thread_casefile/lenses.py:212` and `packages/casefile/src/red_thread_casefile/services/casefile.py:28` (`EXCLUDED`). Fix: one `STATE_DIRECTORY = '.red-thread'` in `domain.py`. Tests restate it too (3.4).

### 1.9 Hand-typed CLI vocabulary next to cyclopts

- `packages/casefile/src/red_thread_casefile/cli.py:22`: `COMMAND_NAMES = 'init, add, render, check, export or page'` copies the six `app.command` registrations.
- `packages/navigate/src/red_thread_navigate/cli.py:20`: `VALID_OPTIONS` copies the option set.
- `packages/navigate/src/red_thread_navigate/cli.py:117` and `packages/navigate/src/red_thread_navigate/cli.py:158` each write the verb table, once to register the commands and once to dispatch them.
- `packages/casefile/src/red_thread_casefile/cli.py:23` defines `EXIT_OK`, but `packages/casefile/src/red_thread_casefile/cli.py:130`, `:150`, `:163`, `:194` and `:204` return a literal `0`.

Fix: build each verb table once and derive the registrations and the error text from it. Use `EXIT_OK` at every return site.

### 1.10 URL scheme rules differ between cites and page links

`packages/casefile/src/red_thread_casefile/domain.py:50` accepts `http://` and `https://` for a cite, while `packages/casefile/src/red_thread_casefile/policy.py:187` accepts only `https://` for the board link. The difference looks deliberate, but neither rule is named. Fix: two named constants in `domain.py` (`CITE_URL_SCHEMES`, `PAGE_URL_SCHEME`) so the difference is visible.

### 1.11 Navigate hints for "not a file" are worded differently

`packages/navigate/src/red_thread_navigate/slice/services.py:122` says "map <path> to see what it holds" and `packages/navigate/src/red_thread_navigate/slice/policy.py:73` says "map <path> to see the names there". Fix: one hint table in `slice/`.

### 1.12 `pytest_ci.py` parses `--random-seed` two ways

`.github/actions/test-suite/pytest_ci.py:372` uses `type=parse_random_seed`, but `.github/actions/test-suite/pytest_ci.py:377` takes a raw string. Fix: use the same `type=` on both subparsers.

______________________________________________________________________

## 2. Production duplication and missing abstractions

| ID | Sites | Problem | Fix | Est. lines |
| --- | --- | --- | --- | --- |
| 2.1 | `packages/navigate/src/red_thread_navigate/symbols/store/__init__.py:27` through `:80` | Six near-identical `TreeSitterSpec(...)` blocks; `aliases={}` appears 5 times and `query_name` equals `language` in 5 of 6 | Default `aliases` to an empty mapping and `query_name` to `language`, then map one tuple of specs through `create_tree_sitter_backend` | -25 |
| 2.2 | `packages/casefile/src/red_thread_casefile/schemas.py:50`, `packages/casefile/src/red_thread_casefile/schemas.py:55`, `packages/casefile/src/red_thread_casefile/schemas.py:177`, `packages/casefile/src/red_thread_casefile/schemas.py:182`, `packages/casefile/src/red_thread_casefile/schemas.py:124`, `packages/casefile/src/red_thread_casefile/schemas.py:220` | `DraftRecord` and `PlanRecord` repeat `unknown_field` and `malformed_text_field`; `load_records` and `load_plan` repeat the decode block | One `RecordShape(allowed, text_fields)` policy and one `decode_json(text)` that returns the error | -15 |
| 2.3 | `packages/casefile/src/red_thread_casefile/schemas.py:28`, `packages/casefile/src/red_thread_casefile/schemas.py:32` | `find_kind` and `find_verdict` have the same body | One `find_member(value, members)` | -3 |
| 2.4 | `packages/casefile/src/red_thread_casefile/views.py:235`, `packages/casefile/src/red_thread_casefile/boards.py:64`, `packages/casefile/src/red_thread_casefile/views.py:187`, `packages/casefile/src/red_thread_casefile/boards.py:72` | State tally and the thread listing are each built twice | One method each on `Board` or `Ledger` (`count_states()`, `describe_threads()`) | -8 |
| 2.5 | `packages/casefile/src/red_thread_casefile/services/casefile.py:188`, `packages/casefile/src/red_thread_casefile/services/casefile.py:132`, `packages/casefile/src/red_thread_casefile/services/press.py:55` | `patterns.scrub(x).text` 3 times | One `scrub_text` on the patterns object | -4 |
| 2.6 | `packages/casefile/src/red_thread_casefile/store.py:123`, `packages/casefile/src/red_thread_casefile/store.py:134`, `packages/casefile/src/red_thread_casefile/store.py:97`, `packages/casefile/src/red_thread_casefile/store.py:119`, `packages/casefile/src/red_thread_casefile/store.py:180`, `packages/casefile/src/red_thread_casefile/store.py:204` | `CaseNotFoundError` guard twice; `mkdir(parents=True, exist_ok=True)` followed by a write, 4 times | A `require_case()` guard and a `write_file(path, text)` helper | -8 |
| 2.7 | `packages/casefile/src/red_thread_casefile/views.py:20`, `packages/casefile/src/red_thread_casefile/views.py:29`, `packages/casefile/src/red_thread_casefile/lenses.py:62` | `SECTIONS` and `SECTION_NOTES` are parallel tuples keyed by the same kinds; `Part(title='Pointers', ...)` 4 times and `How to read` 3 times | One `(kind, title, note)` table and named `Part` constants | -10 |
| 2.8 | `packages/navigate/src/red_thread_navigate/find/views.py:41`, `packages/navigate/src/red_thread_navigate/map/views.py:47`, `packages/navigate/src/red_thread_navigate/slice/views.py:52`, `packages/navigate/src/red_thread_navigate/find/views.py:29`, `packages/navigate/src/red_thread_navigate/map/views.py:37` | 12 rung builders shaped "header plus per-item lines"; the `path#qualified_name` address is built at 4 sites | `rung(header, lines)` and `symbol_address(path, symbol)` | -15 |
| 2.9 | `packages/navigate/src/red_thread_navigate/find/services.py:47`, `packages/navigate/src/red_thread_navigate/slice/services.py:70`, `packages/navigate/src/red_thread_navigate/budget/policy.py:51`, `packages/navigate/src/red_thread_navigate/budget/policy.py:67`, `packages/navigate/src/red_thread_navigate/slice/util.py:17`, `packages/navigate/src/red_thread_navigate/slice/util.py:23` | `fit_to_budget(...).text` at 5 sites; `fit_notes` and `cut_rung` share an accumulate-while-it-fits loop; `shorten_path` and `shorten_name` share a guard | `fit_text()`, one `keep_prefix(items, fits)`, one `shorten(text, limit, keep)` | -15 |
| 2.10 | `packages/casefile/src/red_thread_casefile/cli.py:112` (and 5 more command classes), `packages/casefile/src/red_thread_casefile/cli.py:66` (and 4 more argument classes) | Six command classes with the same shape; five argument classes repeat `case: CaseOption` | A command table plus one shared case-only argument class for render, check, export and page | -20 to -40 |

Not proposed: the two `run_git` wrappers (`packages/casefile/src/red_thread_casefile/store.py:157`, `packages/navigate/src/red_thread_navigate/walk/store.py:32`) live in separately shipped distributions, and sharing them would add a cross-package dependency.

______________________________________________________________________

## 3. Test duplication

| ID | Sites | Problem | Fix | Est. lines |
| --- | --- | --- | --- | --- |
| 3.1 | `tests/casefile/services/fakes.py:35`, `tests/casefile/ledger/memory.py:25`, `tests/casefile/services/fakes.py:84`, `tests/casefile/ledger/builders.py:47` | `LedgerStore` copies `MemoryCaseRepository` method for method; `create_entry` exists twice with different default text and round | `fakes.py` imports `MemoryCaseRepository` and `create_entry` from `tests.casefile.ledger` | -40 |
| 3.2 | `NAVIGATOR = create_navigator()` in 7 modules, `BIG_BUDGET = 10_000` in 6, `CORE`/`CLIENT` in 5, `SHORT` in 3 (for example `tests/navigate/find/integration/test_find.py:31`) | The same module constants are copied across navigate test modules | One `tests/navigate/samples.py` (or a fixture in `tests/navigate/conftest.py` for `NAVIGATOR`) | -30 |
| 3.3 | `tests/navigate/symbols/unit/test_go_backend.py:33`, `tests/navigate/symbols/unit/test_rust_backend.py:31`, `tests/navigate/symbols/unit/test_typescript_backend.py:46`, `tests/navigate/symbols/unit/test_go_backend.py:85` (and 3 more), `tests/navigate/slice/integration/test_slice.py:39`, `tests/navigate/slice/integration/test_slice_budget.py:41` | `spans_of` 3 times; the "query carries the upstream notice" test 4 times, once per language; `long_class` twice | Move `spans_of` and `long_class` to `tests/navigate/symbols/samples.py`; parametrize the notice test over languages in one module | -50 |
| 3.4 | `tests/casefile/pages/asset_names.py:8`, `tests/casefile/lenses/cases.py:16`, `tests/casefile/pages/flags.py:3`, `tests/casefile/charts/unit/test_case_map_properties.py:19`, `tests/casefile/framing/integration/test_git_tree.py:18`, `tests/casefile/pages/unit/test_chips_properties.py:29`, `tests/casefile/charts/unit/test_case_map_properties.py:28`, `tests/navigate/slice/integration/test_slice_budget.py:28`, `tests/plugin/roster/cases.py:13`, `tests/casefile/pages/builders.py:41` | Tests restate production constants and key functions (`ASSET_NAMES`, `ALL_KINDS`, flag prefixes, `MAIN_LEDGER`, `EXCLUDED`, `order_name`, `order_thread`, `MIN_BUDGET`, `SCOUTS`, and a `DocumentField` Literal plus a tuple of the same names). A production change passes the test against the stale copy | Import from the package, or use `get_args` on the production Literal (`SCOUTS` from `hooks/roster.py` has to stay a copy only if the hook script cannot be imported) | -25 |
| 3.5 | `tests/casefile/pages/html_reading.py:171` (and `:175`, `:187`, `:191`, `:195`, `:233`, `:237`), `tests/casefile/pages/html_reading.py:23`, `tests/casefile/pages/html_reading.py:37` | Seven `list_*` functions do the same `[unescape(x) for x in RE.findall(page)]`; `CLAIM` and `CLAIM_MARKUP` are the same regex | One `read_all(pattern, page)` and a single `CLAIM` | -15 |
| 3.6 | The timestamp `'2026-11-21T09:30:00+00:00'` at `tests/casefile/ledger/memory.py:15`, `tests/casefile/framing/cases.py:11` and `tests/casefile/entries/strategies.py:58`; `GIT_SETTINGS` at `tests/casefile/ledger/git_repository.py:11`, `tests/navigate/walk/integration/test_walk.py:19` and `tests/plugin/release/repository.py:20` (the plugin copy has no user name and email, so the values differ); `DIAGRAM` 5 times, `SCRIPT`/`URL`/`LEAKED`/`KNOWN` 4 times each | Shared fixtures are copied per module | One owner module per value (`tests/casefile/ledger/builders.py` for case data, a `tests/git.py` for `GIT_SETTINGS`) | -30 |
| 3.7 | `tests/casefile/lenses/builders.py:56`, `tests/casefile/lenses/builders.py:110`, `tests/casefile/pages/unit/test_html_new_fields.py:39`, `tests/casefile/pages/unit/test_html_writer.py:50`, `tests/casefile/entries/cases.py:161`, `tests/casefile/batches/cases.py:199` | `export` has the same body on two harnesses; `payload_cases` is defined twice; `malformed_batch_params` and `invalid_thread_params` have the same structure | A module-level `export(harness, ...)`; move the shared cases into `tests/casefile/pages/builders.py` | -20 |

______________________________________________________________________

## 4. Duplication the project rules require (owner decision)

These are the biggest repeated blocks, but `.claude/rules/python.md` or `.claude/rules/testing.md` asks for them as written. Removing them means changing a rule first.

| ID | What | Count | Rule | Options |
| --- | --- | --- | --- | --- |
| 4.1 | The `param` property on scenario dataclasses | 28 copies in 21 files, plus 16 copies of `[case.param for case in cases]` | testing.md "Scenarios" requires `param` on each Scenario class; python.md bans base classes outside the allowed list | (a) Keep the property, and replace the 16 list comprehensions with one shared `as_params(cases)` built on `map(attrgetter('param'), cases)`, about -16 lines, no rule change. (b) Allow a shared `Scenario` base or a module-level `to_param(case)`, about -60 lines, rule change. |
| 4.2 | Exception constructors that rebuild the `entry {position}:` prefix | 14 in `packages/casefile/src/red_thread_casefile/errors.py` | python.md "Errors" requires one class per failure with a hand-written `__init__` | Add a module-level `entry_prefix(position)` function (one owner for the format, about 0 net lines). An `EntryError` base is ruled out because of "never on invented category bases". |
| 4.3 | Literal alias plus tuple pairs (1.2) | 5 | python.md prefers `Literal` aliases | `get_args` keeps the Literal as the single owner, so no rule change is needed. |

______________________________________________________________________

## 5. Hand-rolled stdlib (verified against the 3.14 docs)

Verdict key: yes means drop-in; partial means a swap works but behavior changes in the caveat; none means no stdlib fits, so keep the code.

### 5.1 Drop-in swaps

| Sites | Current | Stdlib | Count |
| --- | --- | --- | --- |
| `tests/casefile/batches/cases.py:113` and 15 more cases modules | `[case.param for case in cases]` | `list(map(operator.attrgetter('param'), cases))` (or 4.1a) | 16 |
| `packages/casefile/src/red_thread_casefile/domain.py:153`, `packages/casefile/src/red_thread_casefile/lenses.py:170`, `packages/casefile/src/red_thread_casefile/cli.py:146`, `packages/casefile/src/red_thread_casefile/services/casefile.py:134`, `packages/casefile/src/red_thread_casefile/services/casefile.py:182`, `packages/casefile/src/red_thread_casefile/services/casefile.py:188`, `packages/casefile/src/red_thread_casefile/pages.py:204` | `f(x.attr for x in xs)` | `map(operator.attrgetter(...), xs)`, the pipeline style python.md asks for | 7 |
| `packages/navigate/src/red_thread_navigate/map/services.py:21` | `def by_source(item): return item.symbol.start_line` | `operator.attrgetter('symbol.start_line')` (dotted names are documented) | 1 |
| `packages/casefile/src/red_thread_casefile/store.py:89` | `tuple(line.parse() for line in lines)` | `operator.methodcaller('parse')` | 1 |
| `packages/navigate/src/red_thread_navigate/symbols/store/python.py:67`, `packages/navigate/src/red_thread_navigate/symbols/store/python.py:73` | nested flatten comprehension | `itertools.chain.from_iterable(map(target_names, ...))` | 2 |
| `packages/casefile/src/red_thread_casefile/views.py:195`, `packages/casefile/src/red_thread_casefile/boards.py:90` | `(f(k, t) for k, t in SECTIONS)` | `itertools.starmap` | 2 |
| `packages/casefile/src/red_thread_casefile/services/casefile.py:121`, `packages/navigate/src/red_thread_navigate/walk/store.py:46` | `tuple(x for x in xs if x)` | `filter(None, xs)` (builtin) | 2 |
| `packages/casefile/src/red_thread_casefile/policy.py:187` | `any(character.isspace() for character in url)` | `any(map(str.isspace, url))` | 1 |
| `packages/casefile/src/red_thread_casefile/store.py:177` | `existing.split('\n')` | `str.splitlines()` | 1 |
| `packages/casefile/src/red_thread_casefile/domain.py:16`, `packages/casefile/src/red_thread_casefile/domain.py:25`, `packages/casefile/src/red_thread_casefile/domain.py:26`, `packages/casefile/src/red_thread_casefile/lenses.py:27`, `packages/casefile/src/red_thread_casefile/policy.py:32`, `tests/casefile/pages/asset_names.py:8`, `tests/casefile/lenses/cases.py:16`, `tests/casefile/pages/builders.py:41` | hand-written tuple of a Literal's members | `typing.get_args(Alias.__value__)` (equality confirmed) | 8 |
| `tests/navigate/budget/unit/test_budget.py:44`, `tests/navigate/budget/unit/test_budget.py:82`, `tests/navigate/budget/unit/test_budget.py:98` | `tuple('x' * 40 for _ in range(20))` | `('x' * 40,) * 20` (sequence repetition) | 3 |
| 11 test sites, for example `tests/casefile/pages/unit/test_html_writer_properties.py:103` and `tests/plugin/quality/unit/test_no_lambda.py:35` | nested flatten comprehension | `itertools.chain.from_iterable` (optional; the comprehension reads fine) | 11 |

### 5.2 Partial swaps (read the caveat before you change anything)

| Sites | Current | Stdlib | Caveat |
| --- | --- | --- | --- |
| `packages/navigate/src/red_thread_navigate/slice/services.py:47`, `packages/navigate/src/red_thread_navigate/symbols/store/python.py:17`, `packages/navigate/src/red_thread_navigate/symbols/store/treesitter.py:22` | `LINE_BREAK.split(text)` | `str.splitlines` | Breaks on 8 more separators and drops the trailing empty element, so line numbers drift. Keep the regex and deduplicate it (1.4). |
| `packages/casefile/src/red_thread_casefile/pages.py:135`, `packages/casefile/src/red_thread_casefile/boards.py:78`, `packages/casefile/src/red_thread_casefile/domain.py:39` | `ts[:10]` | `datetime.date.fromisoformat(ts[:10])` | Raises `ValueError` on malformed input where the slice passed it through. Worth it only if the caller wants validation. |
| `packages/navigate/src/red_thread_navigate/slice/views.py:49` | `tuple(f'  {line}' for line in text.splitlines())` | `textwrap.indent` | Returns a `str`, not a tuple, and skips whitespace-only lines by default. |
| `packages/navigate/src/red_thread_navigate/budget/policy.py:53`, `packages/navigate/src/red_thread_navigate/budget/policy.py:69` | accumulate-while-it-fits loop | `itertools.takewhile` | Needs a stateful named predicate. Do it together with 2.9. |
| `packages/navigate/src/red_thread_navigate/walk/store.py:61` | `os.walk(...)` | `pathlib.Path.walk` | Yields `Path` objects, and the keyword is `on_error`. Re-test the in-place pruning. |
| `tests/casefile/ledger/memory.py:51`, `tests/casefile/services/fakes.py:61`, `tests/navigate/symbols/unit/test_python_backend.py:101` | `d.setdefault(k, []).append(v)` | `collections.defaultdict(list)` | A plain read then inserts the key. Leave the fakes alone (3.1 removes one copy anyway). |
| `tests/plugin/roster/cases.py:36`, `tests/plugin/roster/cases.py:64` | `name.partition(':')[2]` | `str.removeprefix` | Needs the exact prefix string. `partition` drops any prefix. |
| `tests/navigate/slice/integration/test_slice_budget.py:203` | `address.split('#')[0].rsplit('/', 1)[-1]` | `PurePosixPath(...).name` | The `#` split still has to happen first. |
| `packages/casefile/src/red_thread_casefile/assets.py:12` | `Path(__file__).resolve().parents[2]` | `importlib.resources.files` | The assets sit beside `src/`, outside the package, so they would have to move into the package first. |
| `packages/navigate/src/red_thread_navigate/symbols/store/treesitter.py:140` | `(start_byte, -end_byte)` key | two stable `sorted` passes with `attrgetter` | Not recommended: harder to read than the key function. |

### 5.3 No stdlib replacement (keep as is)

`packages/casefile/src/red_thread_casefile/pages.py:60` (`order_name`), `packages/casefile/src/red_thread_casefile/domain.py:34` (`order_thread`), `packages/navigate/src/red_thread_navigate/find/services.py:13` (`by_path`, whose `str()` changes the ordering), `packages/navigate/src/red_thread_navigate/map/services.py:25` (`by_file_rank`, which negates), `packages/navigate/src/red_thread_navigate/slice/util.py:20` (left truncation, where `textwrap.shorten` cuts on the right), and `packages/casefile/src/red_thread_casefile/util.py:42` (`' '.join(text.split())`, already the idiom).

### 5.4 Counts

| Category | Drop-in | Partial | None |
| --- | --- | --- | --- |
| operator (`attrgetter`, `methodcaller`) | 25 | 1 | 2 |
| itertools (`chain.from_iterable`, `starmap`, `takewhile`) | 15 | 2 | 0 |
| typing (`get_args`) | 8 | 0 | 0 |
| builtins (`filter(None)`, `map(str.isspace)`, sequence repetition) | 6 | 0 | 0 |
| str (`splitlines`, `removeprefix`, `split`) | 1 | 5 | 1 |
| datetime (`date.fromisoformat`) | 0 | 3 | 0 |
| textwrap (`indent`, `shorten`) | 0 | 1 | 1 |
| collections (`defaultdict`) | 0 | 3 | 0 |
| pathlib / importlib.resources | 0 | 3 | 0 |
| sort keys with no stdlib helper | 0 | 0 | 2 |
| functools, contextlib, html, shlex, os.path joins | 0 | 0 | 0 |
| **Total** | **55** | **18** | **6** |

What the code already does well: `collections.Counter` (7 sites), `itertools.chain`, `pairwise`, `groupby`, `zip_longest`, `functools.cache` and `types.MappingProxyType` are in use. Grep found no hand-rolled HTML escaping, shell quoting, `os.path` string joins, `try/except: pass` or manual chunking in `packages/` or `hooks/`.

______________________________________________________________________

## Caveats

- Every one of the 160 `path.py:line` citations in this file was re-read and resolves to the code described (all lines hold the quoted construct as of this audit). `check_citations` flags 140 rows as `missing_quote` or `quote_not_found` only because rows list several sites without a backticked quote per site.
- The pylens reports were gathered at their turn limits. Four of the six could not re-run `check_citations` after trimming. Every row above was re-read at its cited line or re-derived by a scan in this session, but line numbers move with the uncommitted edits.
- The line estimates are rough. Section 4 numbers depend on the rule decision.
- `ty` reads `get_args` as `tuple[Any, ...]`. The annotated target (`tuple[EntryKind, ...]`) keeps the public type, but run `make typecheck` after 1.2.
