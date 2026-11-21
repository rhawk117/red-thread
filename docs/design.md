# red-thread design

Status on 2026-11-21: the direction is agreed, and steps 1 to 5 of the build order in section 11 are built. No real case has been run yet. **Decided** marks a choice the owner made in a dialog. **Proposed** marks the designer's intent that the owner has not confirmed.

## How to read this

- Sections 1 to 3 are enough to understand the plugin.
- Sections 4 to 7 are the contract for building it.
- Section 8 is a separate track, the navigation tool, which red-thread does not depend on.
- Section 9 lists the evidence, section 10 the prompting guidance for agent files, section 11 what is open and the build order, section 12 the decision log.

## 1. Purpose

red-thread is a Claude Code plugin that runs a human-gated investigation and turns the result into something a later session, or a person, can act on without re-reading the investigation.

It replaces one part of the mightymodels plugin (`/home/rhawk/projects/personal/cc-marketplace/mightymodels`): the investigation loop. mightymodels wires that loop to tickets, tasks, a review pipeline, an MCP state server on SQLite with 36 tools, and nine hook entries, in about 15,600 lines of Python. red-thread keeps the loop and drops the rest.

Use cases:

1. Research a question, then hand a planning session a brief it can build an implementation plan from.
2. Large research worth several agents: security research, or learning how a system works.
3. Produce a hand-off, meaning a pointer to context that is useful to a person and to an agent, and a GitHub issue.
4. Troubleshoot to a root cause, or survey a codebase for technical debt: what it is, why it happened and what to do.

Out of scope: tickets, task tracking, code review, implementing changes, an MCP server and a database. Version 1 ships no hooks.

The owner steers every investigation from experience and reviews on a phone through Remote Control, so every gate has to be readable there.

## 2. How context is separated

Four rules do the separating. The number of agents is secondary.

1. **Questions go down, claims come up.** A dispatch carries a question, the decision it serves and the bar for "good enough". A report carries claims, each with a pointer (`path:line` at a commit, or `URL#heading` at a version) and a status. Content never travels.
2. **The case file is the only shared memory.** Every context, the main session's included, is disposable. Anything that is not in the case file is lost by design.
3. **Readers get tiers.** First a brief of 60 lines or fewer, then the ledger, then the cited line itself. A later session loads the brief and opens the rest only when it needs to.
4. **Status never upgrades in transit.** An inferred claim stays inferred however often it is repeated. Only a new lookup or the owner can upgrade it.

## 3. Org chart

```text
you         intent, priors, "is this sufficient"   sees the board at each gate
primary     target, thread list, your decisions    holds the rendered board, never raw reports
├ lead ×N   judgment for one thread                holds its scouts' reports
│ ├ code scout   reads the repository    path:line @ commit
│ ├ web scout    reads documentation     URL#heading @ version
│ └ lab scout    runs one experiment     command + output
└ skeptic   gets claims and citations only; tries to break them before an export
```

| Role | Agent file | Model | Limits |
| --- | --- | --- | --- |
| primary | none, it is the session | the session's model | never reads raw scout output when leads are in use |
| lead | `agents/research-lead.md` | `claude-sonnet-5-5` | six jobs a round, two rounds |
| code scout | `agents/code-sense.md` | `claude-haiku-5-5` | five tool calls, read-only |
| web scout | `agents/web-head.md` | `claude-haiku-5-5` | five tool calls, read-only |
| lab scout | `agents/research-cell.md` | `claude-sonnet-5-5` | one experiment per dispatch, in a git worktree |
| skeptic | `agents/peer-review.md` | `claude-sonnet-5-5` | receives claims and citations, never the reasoning; read-only |

**Decided: depth is adaptive.** With one thread, the primary dispatches scouts itself and stops at a gate every two or three lookups. With two or more independent threads, each thread gets a lead. The owner approves the thread split in round zero, and at each gate chooses which threads advance, redirect or stop. Leads cost steering precision: a lead runs up to six lookups between gates.

**Decided: a lab scout exists.** Root-cause work needs evidence that reading cannot give. The lab scout is the only piece that is not read-only, so it runs in a worktree.

**Decided: the skeptic is offered at the gate**, as "sufficient, verify first". It is never automatic.

Platform facts checked on 2026-11-21 against the Claude Code docs and one live probe:

- A subagent can dispatch subagents. The docs give a default depth of three layers below the main conversation. The probe confirmed dispatch and a follow-up to the child through SendMessage.
- A type list in a subagent's `tools:` line, such as `Agent(a, b)`, is ignored. It applies only to an agent run as the main thread. "Dispatch only these agents" is therefore enforced by the prompt alone, unless a plugin-level PreToolUse hook on the Agent tool is added. That hook can see the target type and the prompt.
- Plugin-shipped agents ignore the `hooks`, `mcpServers` and `permissionMode` frontmatter fields.
- A SubagentStop hook can block a subagent from stopping and send it feedback, which could enforce the report format later.
- A workflow cannot pause for input, so a workflow fits inside one round and never across a gate.

## 4. The case file

```text
.red-thread/<case-id>/
  case.json          target, kind, bar, publish choice, page URL, detected capabilities
  ledger.jsonl       entries written by the primary
  threads/T1.jsonl   entries written by one lead; one file per thread, so writers never share a file
  board.html         rendered at every gate
  out/               brief.md, issue.md, handoff.md, report.md and their HTML
```

`.red-thread/` is excluded from git locally and never committed. A case id is the UTC date and a slug of the target, such as `20261121-retry-queue-slowdown`.

### The script

**Decided:** one Python script is the only writer and renderer of the case file. It replaces the MCP server, the database and the recorder hooks. Its one dependency is msgspec, which reads and writes every JSON record. That reverses the earlier choice of the standard library alone. The launcher asks uv for msgspec with `--with`, so nothing is installed into the project under investigation, and the first run on a machine downloads it.

The code is the workspace package `packages/casefile`. The stored records (`Entry`, `Case` and `Capabilities`) are frozen msgspec Structs, so a ledger line or a `case.json` that does not match its type is refused with the file and the fault named. Batches and export plans keep their own validation, so `add` still reports every fault in a batch with its fix. The page's skeleton, styles, script and map header sit in `packages/casefile/assets/`, beside `src/`, where they are easy to find, and `assets.py` reads them by path from the module file. The package therefore runs from the source tree, which is how `scripts/casefile.sh` and an editable install run it; a built wheel would not carry the assets. The HTML fragments are Python 3.14 t-strings rendered through one escaping function. Imports inside the package are absolute.

| Command | What it does | Status |
| --- | --- | --- |
| `init` | creates the case, records HEAD, and detects capabilities once (repository languages, whether the navigation tool is installed) | Built |
| `add` | validates a batch of entries whole, stamps time and HEAD, redacts secrets, appends | Built |
| `render` | prints the board, capped at about one screen; writes `board.html` on request | Built |
| `check` | re-resolves every live citation against the current tree | Built |
| `export` | assembles a lens output from the ledger and fails when it is over its line budget | Built |
| `page` | records the link of the published board in `case.json` | Built |

**Decided:** the script is the workspace package `packages/casefile`, run through `scripts/casefile.sh`, which starts it with `uv run --no-project --python 3.14 --with-editable` on the package. uv takes the dependencies from the package's own `pyproject.toml` and keeps the environment in its cache, so nothing is installed into the project under investigation and the launcher repeats no requirement. The primary passes the launcher's absolute path in each brief as `SCRIPT`, since a brief already carries everything a worker needs.

### Entries

**Decided** (accepted on 2026-11-21 and built).

| Field | Meaning |
| --- | --- |
| `seq` | position in its file, shown with the thread, as in `T1.e4` |
| `round` | 0 for framing, then the round number |
| `kind` | `known`, `open`, `decision`, `hypothesis`, `ruled_out`, `resource` or `next` |
| `text` | the claim or question, after secret redaction |
| `source` | the agent that found it, `user` or `primary` |
| `verdict` | the scout's verdict, carried through unchanged |
| `cite` | `path:line`, `URL#heading` or a command |
| `quote` | the text of the cited line, so `check` can tell moved from changed |
| `addr` | optional symbol address, `path#Symbol` (**Decided:** reserve it now) |
| `diagram` | optional mermaid source for a flow or a structure, drawn on the HTML pages only; scrubbed for secrets like every text field (**Decided 2026-11-21**) |
| `rests_on` | the caveat an inference depends on, such as "a 4.x docs page" |
| `refute` | for a hypothesis, the observation that would refute it |
| `supersedes` | earlier entries this one retires |
| `at`, `head` | UTC time and the commit the repository was at |

Rules. The first six come from mightymodels. `add` enforces all eight.

1. A `known` needs a citation. A claim with no citation is `open`.
2. A `decision` comes only from the owner.
3. Files are append-only. An entry is retired by a later entry that names it, never edited.
4. A batch is validated whole before anything is stored.
5. Text matching a secret pattern is redacted before it is stored.
6. An entry whose `head` differs from the current HEAD is a lead to re-verify, not evidence.
7. A `hypothesis` needs a `refute` line.
8. A `ruled_out` entry needs a citation or the owner as its source.

Added while building, and not yet owner decisions:

- A citation is a path, a URL or anything else. `add` opens every `path:line`. An absolute path, or one containing `..`, is never read and stays unchecked.
- `add` compares a supplied `quote` with the cited line, and records the line itself when `quote` is left out.
- An entry from `user` cannot be written to a thread, and a thread can retire only its own entries.
- An INFERRED entry needs `rests_on`, and a `known` cannot carry a verdict weaker than VERIFIED.
- `check` redacts the lines it reads before comparing them, so a redacted quote still matches.

### The citation check

`check` answers one question for a later session: which of these claims can I still trust? For each live citation it reports one of four states.

- **ok**: the file exists and the quoted text is still at that line.
- **moved**: the quoted text is found elsewhere in the file, or the symbol address resolves to a new line.
- **changed**: the line or symbol exists and the text differs.
- **missing**: the file, line or symbol is gone.

It runs before every export. It also catches a citation a scout invented before the owner sees it at a gate.

### Pages

- **Decided:** the script renders the HTML for the board and for every output from the ledger. The model does not write the page.
- **Decided:** whether a case is published to claude.ai is asked once, at framing. A published case republishes its board to the same URL at every gate. Pages are private by default. A local-only case never leaves the machine.
- **Proposed, not built:** comments the owner sends to Claude from the page are recorded as ledger entries from `user`, so the owner can steer by annotating a finding.
- **Decided 2026-11-21, reversing the self-contained page:** a page loads two scripts from cdnjs, each pinned to an exact version with a sha512 integrity hash: the Tailwind browser build (4.3.5), which styles the page, and mermaid (12.3.0), which draws diagrams. Nothing else is fetched, so web fonts stay out. Opened offline, a page still reads top to bottom: every entry is in the HTML, the token colors apply and the controls stay hidden. Tailwind documents its browser build as a development tool; the owner chose it for a page that one person reads.
- Built: the page's own script, `assets/page.js`, uses no library. It filters entries by kind and by thread, folds sections and copies a ref or a citation. It holds no case data: entry text reaches the page only as escaped text and escaped attribute values.
- Built: after its sections the board page draws a map of the case, a mermaid flowchart the script writes from the ledger. Each thread is a line of its entries in order, a retired entry has a dashed outline, and an edge runs to it from the entry that retired it. An entry's own `diagram` is drawn under its claim. Diagram text is escaped into the page and mermaid runs at its strict security level.
- Built 2026-11-21, when the owner asked for more context on the page: the board page opens with the case facts (bar, kind, round, commit, created, languages, entry counts, threads and the totals of the citation check). Each section is a panel whose header names what the section holds and counts its entries. An entry shows its round, the day it was recorded, its verdict when it is not a `known`, the state of its citation at the last check and the source line the ledger quoted. A citation that changed, moved or went missing is that state badge on the page and stays a flag in markdown. The page ends with a folded list of the retired entries, each naming the entry that retired it. Lens pages share the panels and the entry details; the facts and the retired list are on the board only.
- The colors are tokens in `assets/page.css`, one set per theme, and `assets/tailwind.css` maps them to Tailwind utilities, so a palette change is made in one file.
- Facts: the Artifact tool publishes one `.html` or `.md` file. Remote Control keeps an AskUserQuestion dialog open until it is answered. The docs name an artifact as the route for a board that keeps updating.

## 5. The investigate skill

**Decided:** two skills only, `investigate` and `distill`. Use cases are kinds and lenses, each a small reference file loaded on demand. There is no skill per use case and no pickup skill.

### Round zero

One dialog before any dispatch: the target as one line the owner can disagree with, the kind, the bar (what the answer must establish for the decision to be acted on), what the owner already knows or has ruled out, and publish or local. If the target splits into independent threads, the owner approves the split.

As built, the dialog has four questions, because a dialog holds four: the target with its kind, the bar, what is already known, and publish or local. A thread split is asked in a dialog of its own.

### Each round

1. Choose two or three questions the ledger cannot answer, or the threads to advance.
2. Dispatch. Each brief stands alone: the question, the scope or subject, the decision it serves and what is already known.
3. Fold each report into the ledger by its verdict (table below).
4. Persist, then render. The primary restates from `render`, never from memory, so the summary cannot drift from the record and a compaction costs nothing.
5. Stop at the gate.

| Verdict | Becomes |
| --- | --- |
| VERIFIED | a `known` with its citation |
| INFERRED | an `open` entry with `rests_on` filled in |
| NEEDS-ANALYSIS | a judgment the primary makes in chat; a `decision` only if the owner accepts it |
| BLOCKED | an `open` entry carrying where the answer lives |
| two scouts disagree | its own `open` entry with both citations, never reconciled silently |

### The gate

The gate is a dialog plus, for a published case, the board link. The primary says what one more round would change, recommends one choice and still asks.

Choices: **sufficient**, **sufficient, verify first** (runs the skeptic), **dig further**, **stop here**. A dialog allows four options, so redirecting is the typed answer (Decided).

### Kinds

| Kind | First questions | Bar | Extra |
| --- | --- | --- | --- |
| root cause | the code path and the runtime configuration | one hypothesis survives a test that could have refuted it, and its rivals are ruled out | rival hypotheses as entries; lab scout |
| claim | the exact lines that would make it true or false | verified true or false with citations | none |
| research | the docs for the pinned version, and the call sites that depend on it | both halves cited | a web scout paired with a code scout |
| survey | orientation, then a thread per area | coverage the owner sets at framing | each finding says what, where, why it happened and what to do |

## 6. The distill skill

`distill` projects the ledger through a lens. Each lens is a template with a hard line budget.

| Lens | Reader | Notes |
| --- | --- | --- |
| `brief` | a planning session | 60 lines or fewer |
| `issue` | GitHub | findings, open questions, references |
| `handoff` | a person or agent resuming the work | pointers, not narrative |
| `report` | the owner or a team | root cause, debt survey or explainer |

Rules:

- `check` always runs first.
- The skeptic runs only when the owner chose it at the gate.
- With no case open, `distill` first builds a ledger from the conversation, and any claim it cannot cite becomes `open`.
- The brief carries its own reading instructions, so it works for a person, for an agent without the plugin, and inside a GitHub issue.

`export` takes an optional JSON plan on standard input: `title`, `goal`, `include` (refs, most important first) and `blocking` (open refs). The model chooses and ranks. The script writes each entry's own text, citation and ref, flags leads and changed citations, redacts the title and goal, and writes nothing when the output is over budget. A budget counts lines that carry text: brief 60, issue 80, handoff 40, report 200. The last three were set while building and are not owner decisions.

Brief template (Decided):

1. **Goal**: one or two sentences, in terms of the decision.
2. **Decided**: the owner's decisions.
3. **Constraints**: the knowns that bound the design, each cited, at most about twelve.
4. **Ruled out**: one line each, with why, so the next session does not chase them again.
5. **Open**: ranked, each marked as blocking planning or not.
6. **Pointers**: the ledger path, the commit, the check command.
7. **How to read**: citations are pointers, so open them instead of trusting the summary; entries from another commit are leads; run the check first.

## 7. Agent changes

All scouts share one report contract, already used by `code-sense` and `web-head`: YAML frontmatter with `verdict` (VERIFIED, INFERRED, NEEDS-ANALYSIS or BLOCKED), `confidence`, the commands run or pages fetched, and `follow_up`; then an answer of one to three sentences and evidence bullets that each start with a pointer.

| Agent | Change |
| --- | --- |
| `research-lead` | writes its thread file through the script instead of a ledger in a temporary directory; gains the lab scout on its team |
| `code-sense` (was `eyes`) | renamed; LSP dropped; navigates with `rg` and ranged reads until the navigation tool passes its gate; cites paths from the repository root, because the ledger opens them |
| `web-head` | the brief gains today's date |
| `research-cell` (lab scout) | new: one experiment per dispatch in a worktree, returns the command and its output |
| `peer-review` (skeptic) | new: tries to break each claim from its citation alone, against a four-question rubric. It is read-only, so the primary records its verdicts |

Every agent file is rewritten against section 10 before it ships.

## 8. Navigation tool (separate track)

agentlens (`/home/rhawk/dev/agentlens`) is the owner's Rust tool for code navigation by weaker models. Version 0.2.0 has about 9,000 lines of Rust, resolves symbols in Python only, and ships a second binary, `doclens`, for json, yaml and markdown.

Decisions:

- **Decided:** it is an optional accelerator. red-thread works the same without it.
- **Decided:** it is distributed as wheels through uv from its own repository. Nothing binary lives in the plugin, and the source is not ported here.
- **Decided:** it is gutted to three verbs that work in any language.
- **Decided:** red-thread is built first. The tool plugs in only if it passes the gate below.

### What it becomes

| Verb | Output |
| --- | --- |
| `outline <file or dir>` | signatures with line ranges |
| `find <name>` | hits shaped like `rg` output, each labelled definition, call or reference, with its enclosing symbol; capped, with a message to narrow the query |
| `slice <path#Symbol or path:line>` | the enclosing definition, bounded |

- No index and no cache.
- Languages come from tree-sitter grammars and their `tags.scm` queries, so a language is data, not code. An unknown language falls back to `rg` and line windows in the same output shape.
- Every output line starts with `path:line`, so it drops into the ledger as a citation.
- `rg` flags are accepted, and an error prints the corrected command.

Removed: the index, `callers`, `dead`, `packet`, `literals`, `sym` and all Python-specific resolution. `doclens` can stay. The evaluation harness stays; it is the most valuable part of that repository.

### The gate

The strongest competitor is no tool. In the agentlens 0.2.0 evaluation, `rg` with `sed` ranges was the most accurate arm. The new tool is added as an arm, on repositories in three languages, with the current Haiku running the red-thread scout prompt and budget. It passes when it beats the `rg` and `sed` arm on cost at equal accuracy with fewer than 2% malformed calls. If it fails, red-thread keeps the line-range prompt and the tool stops there.

### In red-thread

- `init` detects the tool once per case and the brief carries that down, so no scout spends a call probing. If it is missing the owner gets one hint; nothing installs from a tool call.
- A dedicated scout uses it, with the same report contract, a short command card instead of the 982-line agent kit, and a token budget in place of five calls.

### To fix in the agentlens repository first

- Only v0.1.0 is released, so the evaluated build cannot be downloaded.
- The release workflow builds four targets and has no Linux arm64 or musl target.
- `Cargo.toml` points `repository` at `github.com/agentlens/agentlens`, not the real remote.
- Add maturin with `bindings = "bin"` for wheels. Whether the PyPI name is free has not been checked.

### Why not the other routes

- uv from a git source makes every user compile Rust.
- Binaries in `bin/` cost about 6.4 MB per platform per version in git history. Plugin clones never fetch Git LFS content, and claude.ai and organisation-synced installs reject a plugin with a top-level `bin/`.
- A language server as the foundation needs a server per language, and the one study of it found it usually adds tokens.

## 9. Evidence

"Twice" means a scout fetched the source and the designer re-fetched it. "Once" means a scout fetched it. Quotes come from page extraction, not from the raw PDF. Papers dated after June 2026 are newer than the designer's training data.

### The agentlens 0.2.0 evaluation

Source: `EVAL_RESULTS_0_2_0.md` in the agentlens repository. 162 runs on Django middleware with Claude Haiku 4.5.

| Measure | agentlens | `rg` + `cat` | `rg` + `sed` |
| --- | --- | --- | --- |
| tool-result tokens per rubric point | 7,511 | 15,523 | 8,257 |
| accuracy, median | 0.6044 | 0.5875 | 0.6833 |
| calls per run, median | 12 | 4 | 12 |
| runs that hit the cap | 7 of 54 | 1 of 54 | 8 of 54 |
| malformed calls | 6.3% | 1.0% | 1.8% |

The malformed calls were mostly `rg` flags the model invented for agentlens. One repository, one feature area, three repetitions.

### Published sources

| Finding | Source | Checked |
| --- | --- | --- |
| Claude Code navigates with glob and grep at run time, "effectively bypassing the issues of stale indexing and complex syntax trees" | Anthropic, Effective context engineering for AI agents, 2025-09-29, <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents> | once |
| Tool responses should be token-efficient and capped; errors should be specific and actionable; evaluate tools with real runs | Anthropic, Writing effective tools for agents, 2025-09-11, <https://www.anthropic.com/engineering/writing-tools-for-agents> | once |
| "Keep the format close to what the model has seen naturally occurring in text on the internet"; make mistakes hard to make | Anthropic, Building effective agents, 2024-12-19, <https://www.anthropic.com/research/building-effective-agents> | once |
| Tool-use examples raised accuracy on complex parameters from 72% to 90% in internal tests | Anthropic, Advanced tool use, 2025-11-24, <https://www.anthropic.com/engineering/advanced-tool-use> | once |
| Subagents explore with tens of thousands of tokens and return 1,000 to 2,000; token use explained 80% of performance variance | Anthropic, multi-agent research system, 2025-06-13, <https://www.anthropic.com/engineering/multi-agent-research-system> | once |
| A 100-line viewer scored 18.0, the full file 12.7; capped search 18.0, no search 15.7 (GPT-4 Turbo, SWE-bench Lite) | SWE-agent, 2024, <https://arxiv.org/abs/2405.15793> | once |
| Predefined tools against bash-only: weakest model 25.2 against 10.2; strongest 65.8 against 69.4 at half the cost | An Empirical Study of Harness Design for Coding Agents, 2026-09-17, <https://arxiv.org/abs/2609.20804> | twice |
| A language server's effect on tokens is "conditional and usually negative"; only Haiku 4.5 saved tokens (26% fewer); grep passed every rename and the server arm passed 0.67 | Does a Language Server Save Tokens for Coding Agents?, 2026-06-29, single author, preliminary, <https://arxiv.org/abs/2608.13568> | twice |
| Skeletons in place of whole files: 8,629 against 25,426 context tokens, solve rate 32.9% against 27.1%, not significant; localization was given by an oracle, 70 instances | What Context Does a Coding Agent Actually Need to Act?, 2026-06-19, single author, <https://arxiv.org/abs/2607.09691> | twice |
| One jump-to-definition tool with fine-tuned 7B to 32B models: 2.68k tokens per sample against 8.44k to 48.86k for graph approaches; Python only | One Tool Is Enough, 2025-12, <https://arxiv.org/abs/2512.20957> | twice |
| An error-recovery layer raised success on explicit errors by 14.2 points for 7B to 8B models and 10.5 for 32B to 70B | Same Error, Different Recovery, 2026-11-08, <https://arxiv.org/abs/2611.11581> | twice |
| Bash beat a typed tool catalogue for frontier models on enterprise tasks | <https://arxiv.org/abs/2609.11999>, 2026-09-10 | once |
| File skeletons for localization, 27.33% on SWE-bench Lite; a code graph added 2.3 points | Agentless, <https://arxiv.org/abs/2407.01489>; RepoGraph, <https://arxiv.org/abs/2410.14684> | once |
| Aider's repository map is built from each grammar's `tags.scm` and lists 63 languages | <https://aider.chat/docs/languages.html> | once |

Gaps: no study measures a current Haiku-class model on a custom navigation command; most localization papers evaluate Python only; the small-model results use fine-tuned open models.

## 10. Prompting by model tier

**Decided:** agent prompts are written for the model that runs them, from Anthropic's own guidance. The Haiku 5.5 and Sonnet 5.5 pages below were read as raw text on 2026-11-21; the other sources were fetched by a scout. Anthropic's own caveat applies to all of it: "Where a technique names a specific model, treat it as measured on that model and re-check it against your own evals."

### All current models

Source: Prompting best practices, <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>.

- Give the reason with an instruction: "Claude can generalize from the explanation."
- "Tell Claude what to do instead of what not to do."
- Put each type of content in its own XML tag.
- Use three to five examples and keep them diverse, because the model picks up patterns from them.
- Current models run independent tool calls in parallel, and a prompt can steer that.
- Forceful wording such as "CRITICAL: You MUST" made Opus 4.5 and 4.6 over-trigger, and the page's fix is plain wording. The page does not say this about the 5.x models.

### Haiku 5.5: the scouts

Source: Prompting Claude Haiku 5.5, <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5>.

| What the page says | What it means here |
| --- | --- |
| `medium` is the default effort: "Start here for most work, including agentic coding." At `low`, "In long agent prompts, the model is more likely to skip a search, stop early, or skip a check." | Scouts stay at `effort: medium`, as the three files already set, and never run at `low`. |
| `high` "suits knowledge work, longer agent tasks, and strict instruction following." | If a scout breaks its report format in testing, try `high` before adding prompt text. |
| "With a short system prompt, Claude Haiku 5.5 rarely stops before the work is done." | Scout prompts stay short. A command card goes in the agent file; the 982-line agentlens agent kit does not. |
| "Claude Haiku 5.5 is trained to resist prompt injection through tool results." | Instructions go in the agent file or the brief, never in a file the scout is told to read. It also backs the rule that file contents are data. |
| "When you give Claude Haiku 5.5 a search tool, also give it today's date." | The web scout's brief carries the date. |
| At `low` and `medium` it "sometimes reports a code change as done without running a check." | A Haiku lab scout has to return the command and its output, or it is the wrong model for that job. |
| "Existing Claude Haiku 4.5 prompts should perform well without changes, unless they ask the model to write its reasoning in the response." | The agentlens evaluation prompts carry over, but its numbers are from Haiku 4.5 and need a rerun. |

### Sonnet 5.5: the lead, and the candidates for skeptic and lab scout

Source: Prompting Claude Sonnet 5.5, <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5>.

| What the page says | What it means here |
| --- | --- |
| "For agentic coding and multistep tool use, start at `medium` for well-specified tasks and move to `high` for harder or longer ones." | The lead stays at `high`. A lab scout running one specified experiment can start at `medium`. |
| At `low` and `medium`, on long agentic tasks, "it's more likely to stop and check in with the user before it completes its work." | A lead cannot ask anyone during a round. Its prompt keeps the existing rule: state the assumption and carry on. |
| "The model tends to add tests, documentation, and small supporting files that fit your repository's conventions, even when you don't ask for them. It does this at every effort level, and more at higher effort." | The lead and the skeptic write only the thread file. A Sonnet lab scout gets the page's own wording: "Don't add features, tests, files, docs, or refactors that weren't asked for." |
| At `xhigh` and `max`, "it can start its own rounds of review and verification, sometimes with subagents if your harness provides them." | No agent runs above `high`, or the job budgets stop meaning anything. |
| "For the hardest long-horizon work, an Opus model is the better choice." | The primary keeps the judgment calls. A lead handles one bounded thread. |

Both pages give the same paragraph for an agent that stops too early: "Keep working until everything the user asked for is done, and only stop to ask when you can't go on without the user or before a risky step." Both also give a verification paragraph for agents that change code, which the lab scout's prompt starts from.

### Briefs and reports

Sources: Anthropic's multi-agent research system and context-engineering posts (section 9). The first was written for an Opus 4 lead with Sonnet 4 workers, so treat it as a starting point.

- A brief needs "an objective, an output format, guidance on the tools and sources to use, and clear task boundaries."
- "Simple fact-finding requires just 1 agent with 3-10 tool calls." The scouts' cap of five calls is at the low end of that range, so five is tested against eight.
- "Start wide, then narrow down."
- Workers "store their work in external systems, then pass lightweight references back to the coordinator." Here that is the case file.
- One model call scoring against a rubric was the most consistent judge, so the skeptic judges each claim against a short rubric.
- Prompts use "diverse, canonical examples" and not "a laundry list of edge cases".

### Agent and skill files

Source: the Claude Code docs on subagents, skills and best practices, fetched by a scout.

- The description decides delegation. The file body is the subagent's whole system prompt; it does not get the Claude Code system prompt.
- At `maxTurns` a subagent returns its output marked partial.
- A `SKILL.md` stays under 500 lines with detail in reference files. The description and `when_to_use` are cut at 1,536 characters in the listing, so the main use goes first.
- "What works perfectly for Opus might need more detail for Haiku." Each file is tested on the model that runs it.

### What changes in the agent files (Done, apart from item 6)

1. Scouts: `effort: medium`, short prompts, numbered steps, a reason attached to each constraint, two or three varied examples, and plain wording with no capitals for emphasis. The existing files already follow most of this.
2. Web scout: the brief gains the current date.
3. Lead: stays at `high`, is told to write only its thread file, and writes scout briefs that carry an objective, an output format, the sources to use and the boundaries.
4. Lab scout: Sonnet 5.5 at `medium`, with the scope wording above. A Haiku version is tested against it before it replaces it.
5. Skeptic: Sonnet 5.5 at `high`, a fresh context, and a rubric per claim.
6. Every file is run on its model before it ships.

## 11. Open items and build order

Open:

- Step 6 is half done. On 2026-11-21 each agent ran once headless on a canned brief in a scratch repository (results below). No real case has gone from framing to a brief yet: the owner drives that in a new session. The scouts' cap of five calls was not binding on a three-file target, so five against eight is still untested.
- Both skills pre-approve `scripts/casefile.sh` through `allowed-tools`. The docs say `${CLAUDE_PLUGIN_ROOT}` is substituted in Bash rules there, and that the grant lasts for the invoking turn only. Whether it reaches a subagent is not documented, so step 6 must confirm it.
- The budgets for `issue`, `handoff` and `report`, and the rules listed as added while building in section 4.
- Whether the roster is enforced by a hook. Version 1 enforces it by prompt alone.
- Owner comments from the published page as ledger entries (section 4).
- The restyled page has not been looked at in a browser from this machine, which has none, and its Tailwind block has not been compiled outside a browser. The owner checks a sample board.
- `page.js` is not run by any test. The tests pin its text, its place in the page and that it holds no case data.
- A diagram drawn before the viewer switches theme keeps its first colors until the page is reloaded.
- `ruff.toml`, `pytest.toml`, `SECURITY.md` and the root `pyproject.toml` still carry mightymodels remnants. `.claude/CLAUDE.md`, `conftest.py` and the renamed rules in `ty.toml` are done.

Build order:

| Step | Status |
| --- | --- |
| 1. The script and its tests | built: `init`, `add`, `render`, `check`, `export` and `page` |
| 2. The agent files | written, validated, and each run once headless on its model |
| 3. `investigate`, with one file per case kind under `references/` | written |
| 4. `distill`, with one file per lens under `references/` | written |
| 5. HTML rendering and publishing | rendering built; publishing is a step in the skills, through the Artifact tool |
| 6. A real case from start to finish | agents run headless; the owner's real case is next |

Headless runs on 2026-11-21. Each was one `claude -p --plugin-dir` session in a scratch repository of three files, whose only job was to dispatch the agent with a canned brief. The cost covers the whole session.

| Agent | Model it ran on | Tool calls | Result | Cost |
| --- | --- | --- | --- | --- |
| `code-sense` | claude-haiku-5-5 | 3 to 5 Bash | VERIFIED, four `path:line` citations, all correct | $0.01 |
| `web-head` | claude-haiku-5-5 | 3 WebFetch | VERIFIED, quotes from the versioned docs pages | $0.02 |
| `research-cell` | claude-sonnet-5-5 | 1 Bash, in its own worktree | VERIFIED, the hypothesis survived | $0.04 |
| `research-lead` | claude-sonnet-5-5 | 3 scouts in one turn, 1 `add` | seven entries accepted in one batch, six citations ok | $0.09 |
| `peer-review` | claude-sonnet-5-5 | 2 Bash (`render --full`, `check`, then the source) | six HOLDS, and the conclusion marked FOLLOWS-WITH-CAVEATS because it claimed more than the entries showed | $0.06 |

What the runs changed:

- `research-lead` first dispatched its scouts by bare name, which the Agent tool did not find, and lost three calls. Its file now names them with the `red-thread:` prefix. The second run made three dispatches and wasted none.
- `code-sense` searched a path outside the repository when its first pattern found nothing, ran `fd` and `cat` although its allowed list names neither, and left the frontmatter unclosed. Its file now says the working directory is the repository, lists the files in SCOPE after an empty search, and checks the closing line and the allowed list before returning. The second run stayed inside the repository and took three calls. It still chains `cat -n` into a Bash call.
- A nested session cannot start its Bash sandbox inside another session's sandbox, so there a scout that needs Bash returns BLOCKED. `code-sense` and `research-cell` both said so plainly and guessed nothing.
- A run in worktree isolation leaves an empty `.claude/worktrees/` directory in the repository under investigation.
- The user's own settings approve sandboxed Bash without asking, so these runs could not show what `allowed-tools` adds.

## 12. Decision log

All made by the owner on 2026-11-21.

| Decision | Choice |
| --- | --- |
| Org chart depth | adaptive: flat for one thread, a lead per thread for two or more |
| Skills | two: `investigate` and `distill` |
| Ledger | one script over append-only JSONL, with msgspec for its JSON (first decided as standard library only) |
| Pages | the script renders HTML; publishing is asked once per case at framing |
| Experiments | a lab scout in a git worktree |
| Skeptic | offered at the gate |
| Design document | a repository file plus a private page |
| agentlens role | optional accelerator |
| agentlens distribution | wheels through uv, nothing in the plugin |
| Symbol addresses | reserve the field on ledger entries |
| agentlens direction | gut to three verbs, any language, grounded in published research |
| Order of work | document, then build red-thread; the tool is a separate track |
| Agent prompts | written per model from Anthropic's guidance |
| Proposed items | all accepted as written |
| Case-file code | the workspace package `packages/casefile`, run through `scripts/casefile.sh` |
| Agent names | `code-sense`, `web-head`, `research-cell` and `peer-review`; `research-lead` unchanged |
| Lab scout and skeptic models | Sonnet 5.5 for both: `research-cell` at medium effort, `peer-review` at high |
| Skill pre-approval | both skills pre-approve the case file script through `allowed-tools` |
| Step 6 | each agent runs once headless on a canned brief, then the owner drives a real case |
| Skill support files | under each skill's `references/` directory |
| Package code | absolute imports, the page assets in `packages/casefile/assets/`, t-strings for HTML fragments, msgspec Structs for stored records |
| Page | Tailwind and mermaid from cdnjs, pinned with integrity hashes; filters, folding, copying and a case map in plain JavaScript; case facts, section panels with a description, entry details and a folded list of retired entries; reverses the self-contained page |
| Entry diagrams | an optional `diagram` field on an entry, drawn on the HTML pages only |
| Test markers | tier marks come from the directory; a regression is an `@example` on a property marked `regression` |
| Remnants | `.claude/CLAUDE.md` and `conftest.py` cleaned, the three renamed rules in `ty.toml` updated; `ruff.toml` and the root `pyproject.toml` left alone |
