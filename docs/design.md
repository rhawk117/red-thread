# red-thread design

Status on 2026-11-26: the direction is agreed, and steps 1 to 5 of the build order in section 11 are built. One real case ran from framing to a brief on 2026-11-21 (section 11, step 6). Planning is built through step 3 of its build order in section 13: the selection rename, the plan record and the plan page. On 2026-11-26 the code was split into three packages (core, casefile and plans), lanes became worktrees, and plans and cases link to each other (section 12). **Decided** marks a choice the owner made in a dialog. **Proposed** marks the designer's intent that the owner has not confirmed.

## How to read this

- Sections 1 to 3 are enough to understand the plugin.
- Sections 4 to 7 are the contract for building it.
- Section 8 describes `navigate`, the code navigation red-thread ships in `packages/navigate`, which replaced the external agentlens.
- Section 9 lists the evidence, section 10 the prompting guidance for agent files, section 11 what is open and the build order, section 12 the decision log.
- Section 13 describes planning: the plan, the epic and its tickets as GitHub issues, and what the implementation plugin reads. Steps 1 to 3 of its build order are built; the rest is proposed.

## 1. Purpose

red-thread is a Claude Code plugin that runs a human-gated investigation and turns the result into something a later session, or a person, can act on without re-reading the investigation.

It replaces one part of the mightymodels plugin (`/home/rhawk/projects/personal/cc-marketplace/mightymodels`): the investigation loop. mightymodels wires that loop to tickets, tasks, a review pipeline, an MCP state server on SQLite with 36 tools, and nine hook findings, in about 15,600 lines of Python. red-thread keeps the loop and drops the rest.

Use cases:

1. Research a question, then hand a planning session a brief it can build an implementation plan from.
2. Large research worth several agents: security research, or learning how a system works.
3. Produce a hand-off, meaning a pointer to context that is useful to a person and to an agent, and a GitHub issue.
4. Troubleshoot to a root cause, or survey a codebase for technical debt: what it is, why it happened and what to do.
5. Debug a failure to a fix the owner approves, then say why it broke, why nothing caught it and what preventing it would cost (added 2026-11-25).

Out of scope: tickets, task tracking, code review, implementing changes, an MCP server and a database. Version 1 ships no hooks.

**Changed 2026-11-25:** the `debug` skill applies a fix, and the guards the owner chooses, after the owner approves each at a gate (section 12). Implementing anything else stays out of scope.

**Changed 2026-11-25:** planning is in scope (sections 12 and 13). red-thread turns a case into a plan, an epic and its tickets, and publishes them as GitHub issues. Executing a ticket, task state, code review and pull requests belong to a separate implementation plugin that reads what red-thread publishes. An MCP server and a database stay out of scope.

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
│ ├ lens scout   reads code structure  path:line @ commit
│ ├ web scout    reads documentation     URL#heading @ version
│ └ lab scout    runs one experiment     command + output
└ skeptic   gets claims and citations only; tries to break them before an export
```

| Role | Agent file | Model | Limits |
| --- | --- | --- | --- |
| primary | none, it is the session | the session's model | never reads raw scout output when leads are in use |
| lead | `agents/research-lead.md` | `claude-sonnet-5-5` | six jobs a round, two rounds |
| code scout | `agents/swarm/code-sense.md` | `claude-haiku-5-5` | five tool calls, read-only |
| lens scout | `agents/swarm/code-lens.md` | `claude-haiku-5-5` | 6,000 tokens of navigate output, read-only |
| web scout | `agents/swarm/web-head.md` | `claude-haiku-5-5` | five tool calls, read-only |
| lab scout | `agents/swarm/lab-rat.md` | `claude-sonnet-5-5` | one experiment per dispatch, in a git worktree |
| skeptic | `agents/peer-review.md` | `claude-sonnet-5-5` | receives claims and citations, never the reasoning; read-only |

**Decided: depth is adaptive.** With one thread, the primary dispatches scouts itself and stops at a gate every two or three lookups. With two or more independent threads, each thread gets a lead. The owner approves the thread split in round zero, and at each gate chooses which threads advance, redirect or stop. Leads cost steering precision: a lead runs up to six lookups between gates.

**Decided: a lab scout exists.** Root-cause work needs evidence that reading cannot give. The lab scout is the only piece that is not read-only, so it runs in a worktree.

**Decided: the skeptic is offered at the gate**, as "sufficient, verify first". It is never automatic.

Platform facts checked on 2026-11-21 against the Claude Code docs and one live probe:

- A subagent can dispatch subagents. The docs give a default depth of three layers below the main conversation. The probe confirmed dispatch and a follow-up to the child through SendMessage.
- **Changed 2026-11-21, after the real case:** a lead no longer follows up with a scout through SendMessage. In Claude Code 2.1.330 that call returns at once ("Resuming agent") and the answer arrives later as a message, which a subagent cannot wait for. All three follow-ups in the real case came back as a refusal ("my run has already ended") with the old report attached, and one lead slept and messaged the primary while it waited. A lead now briefs a fresh scout and puts what the first report established in the briefing, `SendMessage` is off its tool list, and each scout file says a message that arrives after its report is a new briefing. The primary still resumes a lead through SendMessage for a second round; that path is untested.
- A type list in a subagent's `tools:` line, such as `Agent(a, b)`, is ignored. It applies only to an agent run as the main thread. "Dispatch only these agents" is therefore enforced by the prompt alone, unless a plugin-level PreToolUse hook on the Agent tool is added. That hook can see the target type and the prompt.
- **Decided 2026-11-21: the roster is enforced by that hook.** `hooks/hooks.json` runs `hooks/roster.py` before every Agent call. The session may dispatch every agent, a lead may dispatch the four scouts, and a scout and the skeptic dispatch nobody. A dispatch outside the caller's roster is denied, and the reason names whom the caller may dispatch. A dispatch whose caller or target is not a red-thread agent is left alone, and so is any input the hook cannot read. The hook takes the caller from the `agent_type` field of its input, with or without the plugin prefix.
- Plugin-shipped agents ignore the `hooks`, `mcpServers` and `permissionMode` frontmatter fields.
- A SubagentStop hook can block a subagent from stopping and send it feedback, which could enforce the report format later.
- A workflow cannot pause for input, so a workflow fits inside one round and never across a gate.

## 4. The case file

```text
.red-thread/<case-id>/
  case.md            frontmatter (target, kind, bar, publish choice, page URL, capabilities), then the primary's rounds
  threads/T1.md      the rounds of one lead; one file per thread, so writers never share a file
  board.html         rendered at every gate
  out/               brief.md, issue.md, handoff.md, report.md and their HTML
```

`.red-thread/` is excluded from git locally and never committed. A case id is the UTC date and a slug of the target, such as `20261121-retry-queue-slowdown`.

**Decided 2026-11-26** (the decision log has the owner's answers): the case file is Markdown that the skills and the leads write by hand. The script creates it, checks it and renders it, and writes no finding. That replaced `case.json`, the JSONL ledgers and the `add` and `page` commands, which put every write through the script. A case file reads like this:

````markdown
---
id: 20261126-why-retries-starve-the-pool
target: why retries starve the pool
kind: root-cause
bar: name the line that starves it
created: '2026-11-26T22:13:41+00:00'
publish: false
head: 03d8e5e3e9d0a24811e535a31b02263b5576a6bf
page_url: null
capabilities:
  languages:
  - Python
---

# why retries starve the pool

## Round 0 · 2026-11-26 · 03d8e5e

## Round 1 · 2026-11-26 · 03d8e5e

### e1

```yaml
kind: known
text: The pool is sized from WORKERS, default 4
source: code-sense
verdict: VERIFIED
cite: src/pool.py:2
quote: WORKERS = int(os.environ.get("WORKERS", 4))
```
````

- `init` writes the frontmatter, the `# target` title and the `## Round 0` heading. The frontmatter decodes into a frozen Struct that refuses unknown keys. Nobody edits it by hand except `page_url`.
- A round is a `## Round N · YYYY-MM-DD · HEAD` heading: the round number, the UTC date and the short commit, or `none` outside git. Every finding under it takes its round, date and commit from it.
- A finding is a `### e<n>` heading over one fenced `yaml` block, which `msgspec.yaml` decodes into a strict Struct. The number in the heading is its `seq`, and the file names its thread. Text outside a round heading, a finding heading or a block is a fault.
- The skills append a round with a quoted heredoc (`cat >> CASE/case.md <<'EOF'`), so the shell leaves `$`, backticks and quotes as written, then run `check` until it exits 0. A lead does the same in its own thread file, and when `check` faults its file it removes its unread round with `sed` and appends it again, because it has Bash and no editing tool.

### The script

**Decided:** one Python package reads, checks and renders the case file. It replaces the MCP server, the database and the recorder hooks. It depends on msgspec and, through `red_thread_core`, on PyYAML, which `msgspec.yaml` uses.

The code is the workspace package `packages/casefile`. The stored shapes (`CaseFinding`, `Case` and `Capabilities`) are frozen msgspec Structs built on `red_thread_core.dto.DTO`, so a block or a frontmatter that does not match its type is a fault with its file and line named. Export selections keep their own validation. Each package keeps the files it ships under `src/<module>/assets/`, inside the package, and reads them through `red_thread_core.packaged` with `importlib.resources`: the page's skeleton, styles and script in core, and in casefile the map header, `wording.yaml` (the section headings, the note prefixes, the map and retired notes, and the glossary) and `lenses.yaml` (the lens parts, budgets and the reading lines). The YAML files decode into frozen Structs that refuse unknown keys, once, when the factory builds the case file, and are handed to the code that writes the board and the lenses. A built wheel carries them. The HTML fragments are built with core's element builder, `red_thread_core.elements`, which escapes every text and attribute value (historical: Python 3.14 t-strings until 2026-11-27, see the decision log). Imports inside the package are absolute.

| Command | What it does | Status |
| --- | --- | --- |
| `init` | creates the case directory and writes `case.md`: the frontmatter with HEAD and the capabilities detected once (repository languages), the title and the `## Round 0` heading | Built |
| `check` | reads every file of the case and reports each fault as `file:line finding id: problem` with its fix, then re-resolves every live citation against the current tree. It changes no file and exits 1 on a fault | Built 2026-11-26 |
| `render` | prints the board, capped at about one screen, after opening every citation again, so a changed, moved or missing one is flagged beside its finding; writes `board.html` on request. It refuses a case whose files cannot be read | Built |
| `export` | assembles a lens output from the ledger and fails when it is over its line budget. It refuses a case whose files cannot be read | Built |
| `add` | validated a batch of findings as JSON and appended it | Removed 2026-11-26: findings are written by hand |
| `page` | recorded the link of the published board | Removed 2026-11-26: `page_url` is a frontmatter key written by hand, and `check` faults one that is not an https link |
| `plan` | moved on 2026-11-26 to its own package and launcher, `bin/redthread-plan` (section 13) | Moved |

**Decided:** the script is the workspace package `packages/casefile`, run through `bin/redthread-casefile`, which starts it with `uv run --no-project --python 3.14 --with-editable` on the package. uv takes the dependencies from the package's own `pyproject.toml` and keeps the environment in its cache, so nothing is installed into the project under investigation and the launcher repeats no requirement. The primary passes the launcher's absolute path in each brief as `SCRIPT`, since a brief already carries everything a worker needs.

### Findings

**Decided** (accepted on 2026-11-21 and built; the format changed on 2026-11-26).

| Field | Meaning |
| --- | --- |
| `seq` | the number in its `### e<n>` heading, shown with the thread, as in `T1.e4` |
| `round` | from its round heading: 0 for framing, then the round number |
| `kind` | `known`, `open`, `decision`, `hypothesis`, `ruled_out`, `resource` or `next` |
| `text` | the claim or question |
| `source` | the agent that found it, `user` or `primary` |
| `verdict` | the scout's verdict, carried through unchanged |
| `cite` | `path:line`, `URL#heading` or a command |
| `quote` | the text of the cited line, copied by hand, so `check` can tell moved from changed |
| `addr` | optional symbol address, `path#Symbol` (**Decided:** reserve it now) |
| `diagram` | optional mermaid source for a flow or a structure, drawn on the HTML pages only; checked for secrets like every text field (**Decided 2026-11-21**) |
| `rests_on` | the caveat an inference depends on, such as "a 4.x docs page" |
| `refute` | for a hypothesis, the observation that would refute it |
| `supersedes` | earlier findings this one retires |
| `at`, `head` | the UTC date and the short commit, from the round heading |

Rules. The first six come from mightymodels. `check` enforces all eight and reports every fault at once.

1. A `known` needs a citation. A claim with no citation is `open`.
2. A `decision` comes only from the owner.
3. A finding is corrected where it stands until a gate or a report has shown it. After that it is retired by a later finding that names it, never edited. (2026-11-26: was "files are append-only", which the script enforced when it was the only writer.)
4. `check` reads every file whole and names each fault with its place and fix. `render` and `export` refuse a case whose files cannot be read. (2026-11-26: was "a batch is validated whole before anything is stored".)
5. Text matching a secret pattern is a fault, and `check` prints the text with the secret replaced, to put in its place. (2026-11-26: was redacted before it was stored.) **Decided 2026-11-26:** the patterns come from detect-secrets: its regex detectors (every one but the public IP detector) and its keyword detector. Core adds detectors only for what it misses: a whole PEM block, Stripe test and restricted keys, `sk-` API keys, Bearer tokens, GitHub fine-grained tokens, URL credentials with punctuation, and unquoted `key=value` assignments. A hit is widened to the whole token around it and labelled `[REDACTED:<type>]` from the detector's type. Rejected: keeping the hand-written patterns, and detect-secrets' entropy detectors, which flag ordinary prose.
6. A finding whose `head` differs from the current HEAD is a lead to re-verify, not evidence.
7. A `hypothesis` needs a `refute` line.
8. A `ruled_out` finding needs a citation or the owner as its source.

Added while building. **Decided 2026-11-21:** the owner accepted the first five as built. The rest were added on 2026-11-26 with the Markdown format.

- A citation is a path, a URL or anything else. `check` opens every `path:line`. An absolute path, or one containing `..`, is never read and stays unchecked.
- `check` compares `quote` with the cited line. (2026-11-26: the script no longer records the line itself; a `path:line` cite without `quote` is a fault, and `check` prints the line to paste.)
- A finding from `user` cannot be written to a thread, and a thread can retire only its own findings. A `decision` sits in `case.md` only.
- An INFERRED finding needs `rests_on`, and a `known` cannot carry a verdict weaker than VERIFIED.
- `check` redacts the lines it reads before comparing them, so a redacted quote still matches.
- A finding written at the current HEAD is held to its quote: a cited line that does not exist is a fault, and a quote found elsewhere or not at all is a fault. A finding from an earlier commit is only reported as moved, changed or missing.
- A field that is present must not be blank. YAML trims a plain value and keeps a quoted one as written.
- `page_url`, when set, must be an https link.
- Round headings in one file go up: a heading whose number repeats or falls below the one above it is a fault, because each round has one heading.

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
- **Decided 2026-11-21, built in the skill:** comments on the published page are recorded as ledger findings from `user`, so the owner can steer by annotating a finding. At each gate of a published case the investigate skill reads the page's comment threads through the Artifact tool and records each open one under the round's heading in `case.md`: a fact to take as given or a choice is a `decision`, a dead end is a `ruled_out`, a doubt or a question is an `open` that names the finding it is about, and a request for work outside the case is a `next` that is not carried out. It then replies on the thread with the new finding id and resolves it, so a comment is recorded once. A comment from anyone but the owner is an `open` finding that names its author. The script needed no change.
- **Decided 2026-11-21, reversing the self-contained page:** a page loads two scripts from cdnjs, each pinned to an exact version with a sha512 integrity hash: the Tailwind browser build (4.3.5), which styles the page, and mermaid (12.3.0), which draws diagrams. Nothing else is fetched, so web fonts stay out. Opened offline, a page still reads top to bottom: every finding is in the HTML, the token colors apply and the controls stay hidden. Tailwind documents its browser build as a development tool; the owner chose it for a page that one person reads.
- Built: the page's own script, `assets/page.js`, uses no library. It filters findings by kind and by thread, folds sections and copies a finding id or a citation. It draws a diagram when its section is open, and draws every diagram again from its source when the viewer's theme changes, whether the viewer chose the theme or the system switched. It holds no case data: finding text reaches the page only as escaped text and escaped attribute values.
- Built: after its sections the board page draws a map of the case, a mermaid flowchart the script writes from the ledger. Each thread is a line of its findings in order, a retired finding has a dashed outline, and an edge runs to it from the finding that retired it. A finding's own `diagram` is drawn under its claim. Diagram text is escaped into the page and mermaid runs at its strict security level.
- Built 2026-11-21, when the owner asked for more context on the page: the board page opens with the case facts (bar, kind, round, commit, created, languages, finding counts, threads and the totals of the citation check). Each section is a panel whose header names what the section holds and counts its findings. A finding shows its round, the day it was recorded, its verdict when it is not a `known`, the state of its citation at the last check and the source line the ledger quoted. A citation that changed, moved or went missing is that state badge on the page and stays a flag in markdown. The page ends with a folded list of the retired findings, each naming the finding that retired it. Lens pages share the panels and the finding details; the facts and the retired list are on the board only.
- The colors are tokens in `assets/page.css`, one set per theme, and `assets/tailwind.css` maps them to Tailwind utilities, so a palette change is made in one file.
- Facts: the Artifact tool publishes one `.html` or `.md` file. Remote Control keeps an AskUserQuestion dialog open until it is answered. The docs name an artifact as the route for a board that keeps updating.

### The document model (Built 2026-11-25)

**Decided 2026-11-25:** the board page and the Markdown lens output build from one typed tree, drawn by Python writers. The owner asked for the design that is easiest to maintain, gives the best page and needs the least code, and chose this one over Jinja and over a TypeScript page. The text board that `render` prints keeps its own path for now.

**Built 2026-11-25**, with these differences from the design below:

- The nodes are in `documents.py`: the inlines `Text`, `Code` and `Link`; the blocks `Paragraph`, `FindingList`, `PointList` (a list without finding ids, such as the pointers) and `Flowchart`; and `Section`, `Fact` and `Document`. A section carries its kind, note and fold, so no `Heading` or `Fold` node is needed. The board's map and retired list are sections in `Document.appendix`. A finding id and a state badge are fields of `FindingNode` that each writer draws, not inline nodes.
- Notes are typed `Note` values with a kind (`rests_on`, `refuted_by`, `retires`, `retired_by`, `urgency`, `source`), and a citation is a `CitationNode` holding its target, quote and citation check.
- Two Protocols, `InlineWriter` and `BlockWriter`, take the place of one `Writer`, because ruff allows ten public methods to a class. Each node's `write` calls its writer method, so ty fails a writer that lacks one.
- The writers are in `writers/`: `markdown.py`, `markup.py` (findings and blocks as HTML, with the one escaping `render`) and `page.py` (the toolbar, the header and `page.html`). `pages.py` and the old `Item`, `Section`, `Fact`, `Document` and `MarkdownWriter` in `views.py` are gone.
- The board page and every lens output were byte-identical before and after the port, checked on a sample case with every finding kind.
- Size: the source grew by about 300 lines (745 added, 437 removed), not shrank. `documents.py` is 250 lines, not 80, because the typed notes, citation and finding builder live there. The writers together are about the size of `pages.py` and the old `MarkdownWriter`.

What is wrong now:

- `Item` in `views.py` is one record with thirteen optional fields. It carries a ledger finding, a pointer line and a reading line, and a writer tells them apart by which fields are empty.
- Meaning becomes strings before a writer sees it: notes such as `rests on: X` and `retired by E3`, citations wrapped in backticks, flags with a prefix. `pages.py` parses the backticks back out with a regex, and the page cannot style a caveat apart from a flag.
- Special content has its own field on `Document` (`facts`, `map_lines`, `retired`) and its own code in each writer.
- Three paths build findings: `Board` (the text board, straight from the ledger), `BoardPage` and the lens `Composer`. Each has its own `list_notes`, and the last two each fill the thirteen fields in a `create_item`. The citation flag that the text board left out (the 2026-11-21 case, section 11) is the kind of gap this split allows.
- A new kind of content has no single place to start.

The design: one typed tree between the ledger and the page and Markdown outputs.

- The nodes are frozen dataclasses in one module: blocks (`Heading`, `Paragraph`, `EntryList`, `Facts`, `Diagram`, `Fold`) and inlines (`Text`, `Code`, `Link`, `Ref`, `Badge`). A finding node keeps its parts typed: claim, verdict, citation and its state, caveats, retirers, round, day and source. No writer parses text back.
- One builder turns a ledger finding and its citation check into a finding node. The text board, the board page and every lens call it and add only what is theirs, such as a lens's blocking mark.
- A `Writer` Protocol has one method per node kind, and the HTML, Markdown and text outputs are three writers. A new node kind adds a method to the Protocol, and ty names every writer that lacks it.
- The HTML writer keeps the t-string `render` and its one escaping function for leaf markup (historical: the element builder since 2026-11-27, see the decision log). `page.html`, `page.js` and the styles stay, so an offline page still reads top to bottom with every finding in the HTML.
- Tests assert on the tree for content and on one writer method at a time for format, in place of whole rendered strings.
- Size, estimated from reading the code: the duplicated finding building in `views.py`, `boards.py` and `lenses.py` and the backtick regex in `pages.py` go away, each writer becomes one short method per node, and the node module adds about 80 lines. No new dependency.

Routes not chosen:

| Route | Why not now |
| --- | --- |
| Jinja templates | Moves the same strings into template files without a model. Adds a third dependency, about 164 ms of import on every command, templates ty cannot check, and two escaping modes (on for HTML, off for Markdown). Estimated net saving about 120 lines. |
| Markdown as the only source, converted for the page | One renderer, but the page loses its data attributes, filter chips, folds and state badges. |
| TypeScript behavior on Python-drawn HTML (`page.ts` in place of `page.js`) | Typed browser code, but it adds a `package.json`, a build whose output is committed to `assets/` and a CI check that it matches. Not needed while the script stays short. |
| TypeScript drawing the page from the tree as JSON | Most room for search or sorting, and `pages.py` goes away, but with scripts off the page is empty, which reverses part of the 2026-11-21 page decision, and it brings the same build. |

## 5. The investigate skill

**Decided:** two user-facing skills, `investigate` and `distill`, plus the preloaded `navigate` support skill (see section 8). Use cases are kinds and lenses, each a small reference file loaded on demand. There is no skill per use case and no pickup skill.

**Changed 2026-11-25:** a third user-facing skill, `debug`, takes a failure to a fix. It keeps its record in a `root-cause` case and hands technical debt back to `investigate` (section 12).

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
| INFERRED | an `open` finding with `rests_on` filled in |
| NEEDS-ANALYSIS | a judgment the primary makes in chat; a `decision` only if the owner accepts it |
| BLOCKED | an `open` finding carrying where the answer lives |
| two scouts disagree | its own `open` finding with both citations, never reconciled silently |

### The gate

The gate is a dialog plus, for a published case, the board link. The primary says what one more round would change, recommends one choice and still asks.

Choices: **sufficient**, **sufficient, verify first** (runs the skeptic), **dig further**, **stop here**. A dialog allows four options, so redirecting is the typed answer (Decided).

### Kinds

| Kind | First questions | Bar | Extra |
| --- | --- | --- | --- |
| root cause | the code path and the runtime configuration | one hypothesis survives a test that could have refuted it, and its rivals are ruled out | rival hypotheses as findings; lab scout |
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

`export` takes an optional JSON selection on standard input (named a "plan" until 2026-11-25, renamed when the plan record took the word, section 13): `title`, `goal`, `include` (finding ids, most important first) and `blocking` (open finding ids). The model chooses and ranks. The script writes each finding's own text, citation and finding id, flags leads and changed citations, redacts the title and goal, and writes nothing when the output is over budget. A budget counts lines that carry text: brief 60, issue 80, handoff 40, report 200. The last three were set while building. **Decided 2026-11-21:** the owner accepted them as built. A budget that a real case shows to be wrong is reported, not changed on the spot.

Brief template (Decided):

1. **Goal**: one or two sentences, in terms of the decision.
2. **Decided**: the owner's decisions.
3. **Constraints**: the knowns that bound the design, each cited, at most about twelve.
4. **Ruled out**: one line each, with why, so the next session does not chase them again.
5. **Open**: ranked, each marked as blocking planning or not.
6. **Pointers**: the ledger path, the commit, the check command.
7. **How to read**: citations are pointers, so open them instead of trusting the summary; findings from another commit are leads; run the check first.

## 7. Agent changes

All scouts share one report contract, already used by `code-sense` and `web-head`: YAML frontmatter with `verdict` (VERIFIED, INFERRED, NEEDS-ANALYSIS or BLOCKED), `confidence`, the commands run or pages fetched, and `follow_up`; then an answer of one to three sentences and evidence bullets that each start with a pointer.

| Agent | Change |
| --- | --- |
| `research-lead` | writes its thread file through the script instead of a ledger in a temporary directory; gains the lab scout on its team |
| `code-sense` (was `eyes`) | renamed; LSP dropped; navigates with `rg` and ranged reads, and takes the behavior questions that `code-lens` does not; cites paths from the repository root, because the ledger opens them |
| `code-lens` (lens scout) | new: the `code-sense` contract over the navigate verbs `map`, `find` and `slice`, with a budget of tool output in place of five calls (section 8) |
| `web-head` | the brief gains today's date |
| `lab-rat` (lab scout, was `research-cell`) | new: one experiment per dispatch in a worktree, returns the command and its output |
| `peer-review` (skeptic) | new: tries to break each claim from its citation alone, against a four-question rubric. It is read-only, so the primary records its verdicts |

Every agent file is rewritten against section 10 before it ships.

## 8. Navigation tool

**Decided 2026-11-23:** red-thread ships its own code navigation, the workspace package `packages/navigate` (`red_thread_navigate`), run through `bin/redthread-navigate`. It replaces the external agentlens tool, which the first version of this section planned to gut and distribute as wheels. agentlens 0.2.0 (`/home/rhawk/dev/agentlens`) stays the source of the command surface and the evaluation harness, and nothing in the plugin depends on it. The launcher starts the package the way `bin/redthread-casefile` starts the case file script, so nothing is installed into the project under investigation. Both launchers run uv with `--no-config`, so a `uv.toml` or `pyproject.toml` uv setting in the investigated repository cannot change what they install.

### What it is

| Verb | Output |
| --- | --- |
| `map PATH` | a header with the file and symbol counts, then one line per file with its symbol count, its reference count and its most referenced symbols; files with the most references come first |
| `find NAME PATH` | the definitions of the name, each with its address, kind and line span, then the references as `path:line`; with no match, `no matches for NAME in PATH` and a next step |
| `slice ADDRESS` | the code the address names, with line numbers |

An address is `file#Symbol`, `file#A.b.c`, `file#Lnn` or `file#Lnn-Lmm`. A symbol of 100 lines or fewer comes back whole. A longer one comes back as its signature, its docstring and an outline of its children, each with its span and the line-range address of its body, and the scout reads the body with a second slice. An explicit line range comes back as asked. An address that matches several definitions returns all of them, each labelled with its context, and an unknown symbol lists the nearest names. Every output line starts with a path and a line, so it drops into the ledger as a citation.

**Hard budget cap.** `--budget N` is the most tokens a call prints, at least 32, and the default is 2,000. The tool estimates tokens at 3.5 characters each, rounded up, and no output goes over the budget by that estimate. When a result does not fit, it steps down to a shorter form and then cuts at a line boundary with the footer `showing N of M, raise --budget`. The footer counts against the budget too. Notes (below) lead `map` and `find` output, trail `slice` output, and are cut first, to `and N more notes`. A refusal also fits the budget and keeps the tail of a long file name, since the end of a path is the part that tells files apart. An unknown flag, `--no-cache` included, is an error that names the valid flags. There is no index and no cache.

### The file walk

- Inside a git repository only tracked files are listed. Outside git, dot-directories and the usual build and dependency directories (`node_modules`, `target`, `build`, `dist`, `venv`, `.venv`, `site-packages`, `__pycache__` and the like) are left out.
- A file over 1 MiB, a binary file (a null byte in its first 8 KiB) and a file that is not UTF-8 are skipped, and the output carries a note counting what was skipped and why.
- A symlink that resolves outside the root is not followed, and the tool resolves no path outside the root it was given. It runs nothing from the repository it reads and writes nothing into it.

### Backends

One symbol model sits behind a per-language backend, chosen by file suffix.

- Python uses the standard library `ast`, which is exact for the running Python version and has no grammar to lag behind it.
- JavaScript, TypeScript and TSX, Go, Rust and Terraform use tree-sitter with a vendored query for each language. Queries are vendored and not taken from the grammar packages, so a wheel upgrade cannot change the output without a change in this repository. The grammar wheels are pinned with `==` for the same reason. Terraform is parsed with the HCL grammar and a hand-written query that names blocks as Terraform references them (`aws_vpc.this`, `data.aws_ami.x`, `module.vpc`, `var.region`, `output.id`, `local.name`) and reports references between blocks with their lines.
- A Go method is addressed as `Type.Method`, for a value or a pointer receiver. A Rust method is addressed as `Type.method`. A method in a trait impl carries an optional impl field, printed as `function (impl NAME)`, and the kind stays `function`.
- A tree-sitter parse stops after 2 seconds, and the 1 MiB size cap bounds the rest.
- A syntax error is a note with the file and the line of the first error. For Python, `ast` stops at the first error, so the file returns no symbols and the note carries the parser's message. For the tree-sitter languages the file keeps the symbols that parsed, and the note carries the line only.
- A JavaScript or TypeScript assignment such as `app.init = function init() {}` is one symbol named `app.init`. A callback passed as an argument is not a symbol.
- Module-level Python and TypeScript constants and variables are symbols of kind `constant` or `variable`.
- A symbol's span starts at its `def` or `class` line, and a decorator above it is not part of the span. The tree-sitter languages differ: a TypeScript or JavaScript class decorator is inside the span, but Rust attributes (`#[derive(...)]`, `#[inline]`) and TypeScript or JavaScript member decorators sit outside it, so a slice of a Rust item does not show its `#[cfg]` or `#[test]` gate. This matches the gold spans of the Python evaluation cases.
- A missing PATH is a refusal that prints a message and exits 1, and an empty PATH is a usage error that exits 2.
- In Go, a use of a type counts as a reference to it, so `find` and the `map` reference counts include type uses.
- In Rust, a type name counts as a reference in these positions: parameter, return (including a trait method signature), `let` annotation, `const`, `static` and `type` right-hand sides, struct and tuple-struct fields, `fn(T)` pointer parameters, the left side of a `where` predicate, generic argument and generic head, struct literal, scoped type, types nested in `&T`, `*const T`, `[T; N]` and tuples, and the self type of an impl. A bare value that starts with an uppercase letter counts too, such as a unit struct or a constant, and so does a capitalized path segment such as `T` in `T::new()` or `E` in `E::Start`. Generic parameters match by name, as in Go. A declaring name is never its own reference. A lowercase path segment such as `std`, `fmt` or `m` is not listed as a reference.
- `find` matches a definition or a reference by its full address as well as by its last part, so `find aws_vpc.this` and `find this` both reach it.
- A refused slice names the next command, so a scout does not guess. An unknown name, an address past the end of the file, a path outside the root and a directory each print `Next step: ...`. The read refusals (over 1 MiB, binary, not UTF-8, unreadable) print no hint, and the navigate skill says what to do instead. The navigate skill describes a refusal by its stable markers (`Next step:`, `cannot be sliced:`, `nearest names:`, `is not valid:`) and not by the wording around them.

### Evaluation

The evaluation cases are in `evals/navigate`, six files (`python.json`, `javascript.json`, `typescript.json`, `go.json`, `rust.json` and `terraform.json`), one per language, in the task format of the agentlens evaluation (agentlens is the tool navigate replaced): Python on Django 6.0.7 (the 18 Django tasks of that evaluation, each with a follow-up line-range address where the required symbol is over 100 lines), and JavaScript, TypeScript, Go, Rust and Terraform on public repositories at pinned tags, with gold spans read from the pinned source. A disagreement between a case and the tool goes to the owner. Nothing has run these cases on a model yet.

### The gate

The strongest competitor is no tool. In the agentlens 0.2.0 evaluation (agentlens is the external tool that navigate replaced), `rg` with `sed` ranges was the most accurate arm. The tool is added as an arm, on repositories in three languages, with the current Haiku running the `code-lens` prompt and budget. It passes when it beats the `rg` and `sed` arm on cost at equal accuracy with fewer than 2% malformed calls. The gate is a measurement for the owner to run and no longer decides whether the tool ships: `code-lens` is the default scout for structure questions. If the tool loses to `rg` and `sed`, the owner decides what changes.

### In red-thread

- `init` does not look for the tool, the board header does not show it and a lead's brief does not mention it. The case file's `navigation_tool` field is gone from new cases, and a `case.json` that still has it loads and renders.
- `code-lens` runs only `bin/redthread-navigate` (named in the briefing as NAVIGATE) and `rg`, with a budget of 6,000 tokens of output a question. The primary or a lead, through `skills/investigate/SKILL.md`, sends it questions about the structure of code in the six languages. Questions about behavior still go to `code-sense`.
- `skills/agents/navigate` holds how to use navigate: the commands, addresses, output, recipes for common asks and every refusal with its next step. It is preloaded through the `skills` field into `code-lens`, `code-sense`, `lab-rat` and `peer-review`, and each of them gets NAVIGATE in its brief. `code-lens` runs only navigate and `rg`; the other three use navigate first for structure in the six languages and keep their own tools for the rest.
- `map` prints each symbol's signature line and `find` prints each definition's address, kind and span with no line text, so the scout cites only lines it saw in `slice` or `rg -n` output.

### Why not the other routes

- Porting agentlens's Rust (the external tool that navigate replaced), or shipping it as wheels, puts a binary in the plugin or makes every user compile Rust. Binaries in `bin/` cost about 6.4 MB per platform per version in git history, plugin clones never fetch Git LFS content, and claude.ai and organisation-synced installs reject a plugin with a top-level `bin/`. The launchers moved to `bin/` on 2026-11-25 regardless; see that day's decisions.
- A language server as the foundation needs a server per language, and the one study of it found it usually adds tokens.
- The upstream `tags.scm` queries differ by grammar and some grammars ship none, so a language would change when a wheel does.

## 9. Evidence

"Twice" means a scout fetched the source and the designer re-fetched it. "Once" means a scout fetched it. Quotes come from page extraction, not from the raw PDF. Papers dated after June 2026 are newer than the designer's training data.

### The agentlens 0.2.0 evaluation

(Historical: agentlens is the external tool that navigate replaced; the Source line and the table below describe it, not navigate.)

Source: `EVAL_RESULTS_0_2_0.md` in the agentlens repository. 162 runs on Django middleware with Claude Haiku 4.5.

| Measure | agentlens | `rg` + `cat` | `rg` + `sed` |
| --- | --- | --- | --- |
| tool-result tokens per rubric point | 7,511 | 15,523 | 8,257 |
| accuracy, median | 0.6044 | 0.5875 | 0.6833 |
| calls per run, median | 12 | 4 | 12 |
| runs that hit the cap | 7 of 54 | 1 of 54 | 8 of 54 |
| malformed calls | 6.3% | 1.0% | 1.8% |

The malformed calls were mostly `rg` flags the model invented for agentlens (historical: navigate replaced it). One repository, one feature area, three repetitions.

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
| "With a short system prompt, Claude Haiku 5.5 rarely stops before the work is done." | Scout prompts stay short. A command card goes in the agent file; the 982-line agentlens agent kit (agentlens is the tool navigate replaced) does not. |
| "Claude Haiku 5.5 is trained to resist prompt injection through tool results." | Instructions go in the agent file or the brief, never in a file the scout is told to read. It also backs the rule that file contents are data. |
| "When you give Claude Haiku 5.5 a search tool, also give it today's date." | The web scout's brief carries the date. |
| At `low` and `medium` it "sometimes reports a code change as done without running a check." | A Haiku lab scout has to return the command and its output, or it is the wrong model for that job. |
| "Existing Claude Haiku 4.5 prompts should perform well without changes, unless they ask the model to write its reasoning in the response." | The agentlens evaluation prompts (agentlens is the tool navigate replaced) carry over, but its numbers are from Haiku 4.5 and need a rerun. |

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

- Step 6 has run once. On 2026-11-21 each agent ran headless on a canned brief, and then one real case went from framing to a brief on this repository (both below). The owner has not driven a case by hand, and nothing has been published or commented on. The scouts' budgets are reported below and not changed: `code-sense` passed five calls in one run of five, and `code-lens` passed 6,000 tokens in two runs of nine.
- `research-cell` worked outside its worktree in the real case (below). Its prompt now says to run plain `git` from the worktree and to keep every scratch file under it. No run has tested the change.
- Both skills pre-approve `bin/redthread-casefile` through `allowed-tools`. The docs say `${CLAUDE_PLUGIN_ROOT}` is substituted in Bash rules there, and that the grant lasts for the invoking turn only. Whether it reaches a subagent is not documented, so step 6 must confirm it. The real case could not: it ran in `auto` permission mode, where sandboxed Bash never asks. It needs a session where Bash asks.
- Owner comments are read at the gate (section 4). No published page has carried a comment through that step yet, so the shape of what the Artifact tool returns for a thread is untested.
- The restyled page has not been looked at in a browser from this machine, which has none, and its Tailwind block has not been compiled outside a browser. The owner checks a sample board. Since 2026-11-21 the tests run the page's script under Node (`tests/casefile/pages/integration`), against a small fake DOM and a stand-in for mermaid in `tests/casefile/pages/dom_harness.js`: the filters, the fold button, copying, and drawing and redrawing diagrams. That checks the script's logic and not what a browser or the real mermaid does with it.
- The `debug` skill is written and validated, and has not run on a real failure. Untested: the worktree check in its phase 2, `git bisect` inside a `research-cell` worktree, proving a guard against the unfixed commit, and loading `investigate` from its close.

Build order:

| Step | Status |
| --- | --- |
| 1. The script and its tests | built: `init`, `render`, `check` and `export` (`add` and `page` were removed on 2026-11-26). `tests/casefile/launcher/e2e` runs `bin/redthread-casefile` as a child process from a copy of the plugin |
| 2. The agent files | written, validated, and each run once headless on its model |
| 3. `investigate`, with one file per case kind under `references/` | written |
| 4. `distill`, with one file per lens under `references/` | written |
| 5. HTML rendering and publishing | rendering built; publishing is a step in the skills, through the Artifact tool |
| 6. A real case from start to finish | agents run headless; one real case run from framing to a brief on 2026-11-21, through headless turns |

Headless runs on 2026-11-21. Each was one `claude -p --plugin-dir` session in a scratch repository of three files, whose only job was to dispatch the agent with a canned brief. The cost covers the whole session.

| Agent | Model it ran on | Tool calls | Result | Cost |
| --- | --- | --- | --- | --- |
| `code-sense` | claude-haiku-5-5 | 3 to 5 Bash | VERIFIED, four `path:line` citations, all correct | $0.01 |
| `web-head` | claude-haiku-5-5 | 3 WebFetch | VERIFIED, quotes from the versioned docs pages | $0.02 |
| `research-cell` | claude-sonnet-5-5 | 1 Bash, in its own worktree | VERIFIED, the hypothesis survived | $0.04 |
| `research-lead` | claude-sonnet-5-5 | 3 scouts in one turn, 1 `add` | seven findings accepted in one batch, six citations ok | $0.09 |
| `peer-review` | claude-sonnet-5-5 | 2 Bash (`render --full`, `check`, then the source) | six HOLDS, and the conclusion marked FOLLOWS-WITH-CAVEATS because it claimed more than the findings showed | $0.06 |

What the runs changed:

- `research-lead` first dispatched its scouts by bare name, which the Agent tool did not find, and lost three calls. Its file now names them with the `red-thread:` prefix. The second run made three dispatches and wasted none.
- `code-sense` searched a path outside the repository when its first pattern found nothing, ran `fd` and `cat` although its allowed list names neither, and left the frontmatter unclosed. Its file now says the working directory is the repository, lists the files in SCOPE after an empty search, and checks the closing line and the allowed list before returning. The second run stayed inside the repository and took three calls. It still chains `cat -n` into a Bash call.
- A nested session cannot start its Bash sandbox inside another session's sandbox, so there a scout that needs Bash returns BLOCKED. `code-sense` and `research-cell` both said so plainly and guessed nothing.
- A run in worktree isolation leaves an empty `.claude/worktrees/` directory in the repository under investigation.
- The user's own settings approve sandboxed Bash without asking, so these runs could not show what `allowed-tools` adds.

The real case on 2026-11-21. The target was how a citation gets from `add` to a flag on the board, in the text board and on the HTML page, in this repository. It ran as five headless turns (`claude -p --plugin-dir`, outside the sandbox). A headless session has no AskUserQuestion and no Artifact tool, so the skill put each gate as numbered options in text, the replies were typed, and the case stayed local.

| Turn | Primary | What happened | Cost |
| --- | --- | --- | --- |
| 1 | claude-fable-5-2 | framing: target, bar, known facts and page, asked as options in text | $0.79 |
| 2 | claude-fable-5-2 | `init`, round 0, then round 1 with a lead on each of two threads; gate | $2.31 |
| 3 | claude-sonnet-5-5, in a new session | resumed from the case file alone; round 2 on one thread with a fresh lead; gate | $0.50 |
| 4 | claude-sonnet-5-5 | round 3, with scouts dispatched by the primary; gate | $0.73 |
| 5 | claude-sonnet-5-5 | the decision recorded, then `distill` wrote a brief of 37 lines against a budget of 60 | $0.83 |

The total was $5.17 against an agreed stop of $5. A call can end above its `--max-budget-usd`: turn 4 cost $0.73 against $0.55 and turn 5 cost $0.83 against $0.45. The primary's own estimate of its spending was low each time ($0.21 for the turn that cost $0.73).

The case ended with 43 live findings, 12 retired, and `check` at 36 citations ok and 1 unchecked (a command). Its finding: the text board never shows a citation flag. `render` builds the board without findings, so only `check`, `export` and the HTML page report a changed citation. A lab scout confirmed it by experiment, and no test pinned it either way. **Decided 2026-11-21:** `render` runs the check, so the text board carries the same flags as the page, and `tests/casefile/board/unit/test_board_citations.py` pins it.

What it showed:

- Resuming works from the case file alone. Turn 3 was a new session on another model, and it took the round, the threads and the open findings from `render`.
- The roster hook's input is as assumed. A dispatch by the session carries no `agent_type`, and a dispatch by a lead carries `agent_type: red-thread:research-lead`, with the prefix. 18 dispatches went through the hook and none was outside a roster, so the deny path has still run only in tests.
- `code-lens` took 9 of the 14 code lookups, then running the external agentlens 0.2.0 that the navigate package replaced. All 76 of its agentlens calls were well formed and carried `--no-cache` and `--budget`. Six reports were VERIFIED and three INFERRED. Two runs passed the budget of 6,000 tokens (6,800 and 7,700), and one ran `rg` four times against a cap of three. This is one repository with no baseline arm, so it says nothing about the gate in section 8, which no longer decides whether the tool ships.
- `code-sense` made 13 tool calls on one brief that held six numbered items, against its cap of five. Its other four runs made 3 to 5. The lead's file now says such a brief is several questions.
- Follow-ups through SendMessage failed (section 3), which left the whole HTML thread INFERRED after round 1. After the change, rounds 2 and 3 had no refused follow-up and no waiting.
- `research-cell` could not run `git -C` in its worktree: the harness refused it three times as too complex to verify. It built a scratch repository under `/tmp` instead and wrote its scripts there, one of them through a `..` path from the worktree. Its result was sound, but it worked outside the worktree the design puts it in. **Decided 2026-11-21:** fix the prompt and not re-test: it tells the scout to run plain `git` from the worktree, to keep scratch files under it, and to return BLOCKED when plain git is refused too.
- The brief lists the gate decisions, with their budgets, under Decided. Its constraints come in the order the model ranked them, not the order of the chain. Findings recorded before a commit made during the case show as leads.
- Still not shown: whether `allowed-tools` reaches a subagent, the primary resuming a lead through SendMessage, `peer-review` on a real conclusion, publishing, and comments.

## 12. Decision log

All made by the owner on 2026-11-21.

| Decision | Choice |
| --- | --- |
| Org chart depth | adaptive: flat for one thread, a lead per thread for two or more |
| Skills | two: `investigate` and `distill` |
| Ledger | one script over append-only JSONL, with msgspec for its JSON (first decided as standard library only; historical: Markdown written by hand since 2026-11-26, see below) |
| Pages | the script renders HTML; publishing is asked once per case at framing |
| Experiments | a lab scout in a git worktree |
| Skeptic | offered at the gate |
| Design document | a repository file plus a private page |
| agentlens role | optional accelerator (historical: replaced on 2026-11-23, see below) |
| agentlens distribution | wheels through uv, nothing in the plugin (historical: replaced on 2026-11-23) |
| Symbol addresses | reserve the field on ledger findings |
| agentlens direction | gut to three verbs, any language, grounded in published research (historical: built in this repository instead, 2026-11-23) |
| Order of work | document, then build red-thread; the tool was a separate track until 2026-11-23 |
| Agent prompts | written per model from Anthropic's guidance |
| Proposed items | all accepted as written |
| Case-file code | the workspace package `packages/casefile`, run through `bin/redthread-casefile` |
| Agent names | `code-sense`, `web-head`, `research-cell` and `peer-review`; `research-lead` unchanged |
| Lab scout and skeptic models | Sonnet 5.5 for both: `research-cell` at medium effort, `peer-review` at high |
| Skill pre-approval | both skills pre-approve the case file script through `allowed-tools` |
| Step 6 | each agent runs once headless on a canned brief, then the owner drives a real case |
| Skill support files | under each skill's `references/` directory |
| Package code | absolute imports, the page assets in `packages/casefile/assets/` (historical: inside each package since 2026-11-26, see below), t-strings for HTML fragments (historical: the element builder since 2026-11-27), msgspec Structs for stored records |
| Page | Tailwind and mermaid from cdnjs, pinned with integrity hashes; filters, folding, copying and a case map in plain JavaScript; case facts, section panels with a description, finding details and a folded list of retired findings; reverses the self-contained page |
| Finding diagrams | an optional `diagram` field on a finding, drawn on the HTML pages only |
| Test markers | tier marks come from the directory; a regression is an `@example` on a property marked `regression` |
| Rules and budgets added while building | accepted as built: the five ledger rules in section 4 and the line budgets for `issue`, `handoff` and `report` |
| Owner comments | read at each gate from the published page and recorded as `user` findings, then answered with the finding id and resolved |
| Text board flags | `render` opens every citation again and flags a changed, moved or missing one, as the page does |
| Navigation scout | `code-lens`, experimental, for the installed agentlens 0.2.0 and only where `init` found the tool; the evaluation gate stays open (historical: replaced on 2026-11-23, see below) |
| Lab scout worktree | the prompt says to run plain `git` from the worktree and to keep every scratch file under it; fixed without a paid re-test |
| Roster | a PreToolUse hook on the Agent tool denies a dispatch outside the caller's roster and says whom the caller may dispatch; a dispatch outside the plugin is left alone |
| Remnants | `.claude/CLAUDE.md` and `conftest.py` cleaned, the three renamed rules in `ty.toml` updated; then `ruff.toml`, `pytest.toml` and `SECURITY.md`; then the release workflow and its script, which name the package `red-thread-plugin`, and the pull request template. `pytest-anyio` (an empty placeholder) and `pytest-mock` left the test group. `anyio` stays with `anyio_mode` and the `anyio_backend` fixture, on the owner's word, though no test is async yet |

### 2026-11-23: in-repo navigation

Made by the owner from 2026-11-23; each row begins with its own date.

| Decision | Choice and reason |
| --- | --- |
| Navigation tool | built in this repository as `packages/navigate`, in place of the external agentlens: a binary in the plugin or a Rust build for every user was ruled out in section 8, and the tool blocks v0.1.0 so `code-lens` never points at an unfinished one |
| Command surface | the verbs of agentlens, the tool navigate replaced: `map`, `find` and `slice` and its addresses, so `code-lens` and the Django evaluation tasks carry over |
| Language backends | `ast` for Python, because it is exact for 3.14 and has no grammar to lag; tree-sitter with vendored queries for JavaScript, TypeScript and TSX, Go, Rust and Terraform, so a wheel upgrade cannot silently change the output |
| Grammar wheels | pinned with `==`, for the same reason as the vendored queries |
| Hard budget cap | the cap wins over showing notes: notes are cut to `and N more notes`, because a scout's context is the scarce thing and a note that overflows it helps nobody |
| Refusals | a cut refusal keeps the tail of the file name, since the end of a path is what tells files apart |
| Rust impl methods | an optional impl field printed as `(impl NAME)`, in place of a wider kind, so the set of kinds stays the same in every language |
| Syntax errors | every tree-sitter language keeps what parses and adds a syntax-error note, because a half-parsed file still answers most questions; Python keeps nothing, because `ast` stops at the first error |
| `code-lens` | the default scout for structure questions in six languages, no longer experimental and not conditional on an install check, because the tool ships in the plugin and a scout that exists only where an install was found would leave most cases without it |
| Navigation-tool detection | removed from `init`, the board header and the lead's brief, because the tool is always there and a check that cannot fail only adds a field; `case.json` files that carry the old key still load |
| Evaluation gate | kept as a measurement and no longer a condition for shipping, since the tool is part of the plugin |
| 2026-11-23: refusal next steps | a refused slice names the next command (unknown name, past the end, outside the root, a directory), so a scout does not guess |
| 2026-11-23: read refusals | not hinted by the launcher: the navigate skill (`skills/navigate/SKILL.md`, before it `code-lens.md`) names them (over 1 MiB, binary, not UTF-8, unreadable) and says what to do instead |
| 2026-11-23: JS names | `app.init = function init() {}` is one symbol named `app.init`, and callbacks are not symbols, because the express evaluation showed duplicates |
| 2026-11-23: `find` full address | `find` matches a reference by its full address as well as its last part, because the terraform evaluation found 0 references |
| 2026-11-23: module constants | module-level Python and TypeScript constants and variables are symbols of kind `constant` or `variable`, because the excalidraw and django evaluations missed them |
| 2026-11-23: spans start at def | a decorated Python symbol's span starts at its `def` or `class` line, over the plan's "line span including decorators", to match the evaluation gold; a TS/JS class decorator is inside the span, while Rust attributes and TS/JS member decorators are outside it |
| 2026-11-23: launchers ignore uv config | both launchers run uv with `--no-config`, because the investigated repository's uv settings could change what a launcher installs |
| 2026-11-23: missing PATH | a missing PATH is a refusal with exit 1, not an empty result, so a scout sees the mistake |
| 2026-11-23: Go type uses | a use of a type counts as a reference in Go, because `find` found none for types |
| 2026-11-24: Rust type and value uses | a Rust type use and a capitalized bare value (a unit struct, a constant) count as references, generics match by name, and declarations are excluded, following the Go decision of 2026-11-23 |
| 2026-11-23: refusal markers | the navigate skill describes refusals by their stable markers, so rewording a message does not break the agent |
| 2026-11-23: navigate skill | one preloaded skill (`skills/navigate`, `user-invocable: false`) in place of usage text in each agent, so the reference lives in one file; `disable-model-invocation` cannot be used because it blocks preloading, so the skill keeps a one-line description in the listing. The Bash scouts other than `code-lens` use navigate first for structure, and keep `rg` for text, config and other languages |

### 2026-11-25: launchers in bin/

Made by the owner on 2026-11-25.

| Decision | Choice and reason |
| --- | --- |
| Launcher location | what ships with the plugin lives in `bin/` with no file extension (`bin/redthread-casefile`, `bin/redthread-navigate`); `scripts/` keeps repository tooling only. Section 8 notes that claude.ai and organisation-synced installs reject a plugin with a top-level `bin/`; the owner accepted that cost |
| Launcher names | prefixed `redthread-`, because Claude Code puts `bin/` on PATH and bare names such as `navigate` could shadow other tools |
| Shared launcher code | `bin/redthread-lib`, sourced and not executable; every function is prefixed `redthread::`. `redthread::run_package NAME` runs `packages/NAME` as `red_thread_NAME`, so a launcher passes only the package name |
| Launcher shape | bash, with `setup_environment` and `main` functions and no global state |

### 2026-11-25: document model

Made by the owner on 2026-11-25.

| Decision | Choice and reason |
| --- | --- |
| Output model | one typed tree of frozen dataclass nodes, one finding builder and two writer Protocols (`InlineWriter`, `BlockWriter`) with a method per node kind, so a new kind of content has one place to start and ty names every writer that lacks it (section 4, The document model) |
| Who draws the page | Python, through the t-string `render` (historical: the element builder since 2026-11-27); no Jinja and no TypeScript, so no new dependency and no build step, and the page still carries every finding in its HTML |
| Scope | the board page and the Markdown lens output; the text board keeps its own path for now |

### 2026-11-25: the debug skill

Made by the owner on 2026-11-25, in one dialog. The skill descends from `whats-broken` in mightymodels and is written for red-thread's agents and case file.

| Decision | Choice and reason |
| --- | --- |
| Fix path | the skill applies a fix after the owner approves it at a gate: the session writes a regression test that fails first, then the smallest change. This reverses "implementing changes" in section 1 for an approved fix and an approved guard, and for nothing else. Rejected: stopping at the cause, which leaves the failure in place and the prevention advice resting on a fix nobody ran; and proving the patch in a worktree first, which needs `research-cell` to fix |
| Record | a case file of kind `root-cause`, so the ledger, the board, the citation check, `peer-review` and `distill` work unchanged and the package gains no kind |
| Name | `debug`, as `/red-thread:debug` |
| Evaluation | validation only (`vibe-code skill validate` and the repository's checks); the owner drives the first real failure by hand. No eval cases, because a headless run has no AskUserQuestion and the gates are the skill |

**Proposed**, as written into the skill and not yet confirmed by a run:

- Seven phases: frame, reproduce, evidence, hypotheses, fix, escape, close. No fix is proposed before a hypothesis has survived a test that could have refuted it.
- At least two rival hypotheses, as in the `root-cause` kind. Independent rivals are tested in the same turn, one `research-cell` each, and one experiment answers for one hypothesis.
- A failed fix is recorded as a `ruled_out` finding that starts "Fix attempt N:", so the count survives a compaction. At three the skill stops and asks the owner what they see.
- The escape phase answers why the defect was introduced and why no guard caught it, gives each guard a verdict (absent, not run, blind, ignored), and classes each finding as a slip, a gap or debt. Each candidate guard is priced by what it catches, what it costs to build and what it costs to keep, and the owner chooses in a dialog. "None: the regression test is enough" is always an option.
- A debt finding is not sized in the debugging case. The skill offers to load `investigate` on it, which opens a case of its own.
- The primary runs the reproduction command itself, once, in the checkout. Every experiment brief starts with `git checkout --detach SHA`, and the first experiment checks that the failure shows in a clean worktree at all.

Platform fact checked on 2026-11-25 against the Claude Code docs (sub-agents and worktrees pages): a subagent's worktree branches from the repository's default branch, not from the session's HEAD, unless `worktree.baseRef` is set to `"head"`. Whether uncommitted changes reach it is not documented. The `root-cause` kind of `investigate` did not pin the commit in its `research-cell` briefs; since 2026-11-25 its reference file says to start EXPERIMENT with `git checkout --detach SHA` (decided by the owner).

### 2026-11-25: the swarm layout

Made by the owner on 2026-11-25. Earlier findings keep the old names and paths.

| Decision | Choice and reason |
| --- | --- |
| Scout folder | the four scouts live in `agents/swarm/`. Claude Code makes a plugin agent's subfolder part of its name, so they are dispatched as `red-thread:swarm:<name>`. `research-lead` and `peer-review` stay in `agents/` |
| Lab scout name | `research-cell` is now `lab-rat` |
| Agent-only skills | `navigate` lives in `skills/agents/`, which `plugin.json` lists under `skills` because the default scan does not reach it |

### 2026-11-25: the meet-the-team skill

Made by the owner on 2026-11-25.

| Decision | Choice and reason |
| --- | --- |
| Team guide | `skills/agents/meet-the-team` introduces the six agents to whoever dispatches them: who may dispatch whom, which agent takes which question, an example brief and the required fields for each, budgets and limits, and what to do with each verdict. It is one file so that briefing guidance is not rewritten in every caller. Like `navigate` it is `user-invocable: false` |
| Lead | `research-lead` preloads it through `skills`. The lead's own file keeps only what is the lead's: the names of its team, that a follow-up is a new briefing, and that judgment is its job |
| Primary | `investigate` and `debug` keep their brief-field tables, which must be in context at every dispatch, and tell the primary to load the skill by name (`red-thread:meet-the-team`) before its first dispatch, for the detail. A relative link was tried first and `vibe-code skill validate` refuses a reference that leaves the skill directory. The tables and the skill overlap on field names, which the owner accepted in place of a required skill load. `tests/plugin/team_skill` fails when the skill stops naming an agent on the roster, when the lead stops preloading it, or when either skill stops naming it |

### 2026-11-25: the artifact-authoring skill

Made by the owner on 2026-11-25.

| Decision | Choice and reason |
| --- | --- |
| Writing guide | `skills/agents/artifact-authoring` says how to word what an agent writes for a reader who was not there. Like `navigate` and `meet-the-team` it is `user-invocable: false` |
| Scope | runtime handoffs only: a case file finding, a report up the chain, the gate summary, a distill title and goal, and a handoff. Writing the plugin's own agent and skill files is out of scope, because that reader is a contributor's session and not a shipped agent |
| Readers | `research-lead` preloads it through `skills`. `investigate`, `debug` and `distill` tell the primary to load `red-thread:artifact-authoring` before the first `add`, or before the title and goal. The scouts do not load it: their report format is fixed in their own files, and section 10 keeps a Haiku 5.5 prompt short |
| Briefs | `meet-the-team` stays the one place for writing a brief. This skill points at it and adds only what a handoff carries |
| Shape | one file with no `references/`: a core that holds for every artifact, then a section per artifact that ends on a "Done when" line, so each has a completion criterion the writer can check |
| Sources | the structure and several rules (completion criteria, single source of truth, the no-op test, stating the positive) are adapted from Matt Pocock's `writing-for-agents` skill, <https://github.com/mattpocock/skills/blob/main/skills/productivity/writing-for-agents/SKILL.md>, read on 2026-11-25. Its material on skill descriptions, invocation and progressive disclosure was left out with the prompt-file scope. The rest comes from the Anthropic sources in sections 9 and 10: reasons with instructions, plain wording, lightweight references passed back in place of copies, and steering the reader when something is truncated |
| Test | `tests/plugin/artifact_skill` fails when the lead stops preloading the skill, when one of the three skills stops naming it, or when it stops pointing at `meet-the-team` for briefs |

### 2026-11-25: the planning extension

Made by the owner on 2026-11-25, in two dialogs and the messages between them. Section 13 holds the design.

| Decision | Choice and reason |
| --- | --- |
| Plugin split | planning joins red-thread; implementation and review ship together as one separate plugin. Rejected: planning as its own plugin, because a plan keeps returning to the findings and that seam would carry a versioned contract at its busiest point; and four plugins, because review findings and per-task checks feed the same task state |
| Transport | the GitHub issue body carries a ticket, with a machine-readable block, and the case keeps a local JSON copy. `.red-thread/` is untracked, so another worktree or a cloud session does not see it. Rejected: files under the shared git directory, which are invisible remotely; and committed plan files, which reverse the never-commit rule and leave stale plans in history |
| Epics | one case can cut many tickets: a parent issue with one sub-issue per ticket. This reverses "tickets" in section 1's out-of-scope list. The case file stays the record of evidence, and the issue becomes the record of a ticket, which narrows "The case file is the only shared memory" in section 2 |
| Task briefs | written per ticket when the ticket starts, against HEAD at that time. Rejected: every brief at plan time, because briefs for later tickets go stale as earlier ones land; and the first ticket only, which is two code paths for one step |
| Progress | hooks stamp start and stop events, the page is republished at each transition, and GitHub shows the epic's rollup. Rejected: an MCP server pushing through channels, a research preview that must be named in `--channels` at every launch; and GitHub alone, which has no durations |
| Risks | "Gate" becomes "You intervene", and the re-plan trigger goes: a signal changes how the affected tickets are cut, not the whole plan |
| Visible plans | the plan is a page the owner reads, like the board |
| Direction, designed in section 13 | worktrees and tickets in parallel; stacked pull requests; an optional adversarial review of the plan; smaller tasks whose briefs carry machine-readable frontmatter and may name any installed subagent, skill or MCP tool; an optional interface preview by a dedicated agent; a retrospective that replaces `prune-ticket` and closes the issues |

### 2026-11-25: version 1 of planning

Made by the owner on 2026-11-25, in three dialogs.

| Decision | Choice and reason |
| --- | --- |
| Where version 1 stops | the plan and the epic: the plan record, the page, the plan skill, the interface agent, publishing, syncing a revision and a close step. Briefs, routing, events and the retrospective come after a real epic has run. Rejected: through ticket start, which fixes the brief schema before anything has consumed one; and everything, because three steps depend on a plugin that does not exist |
| Who executes a ticket | a plain Claude Code session in a worktree, working from the issue alone, so a ticket has to stand as a prompt. Rejected: mightymodels as a stopgap, which shapes tickets around the harness being replaced and assumes one active ticket per branch; and building both plugins together, which holds version 1 until both work |
| Brief cutter | a red-thread skill run in the ticket's worktree, built after version 1. Rejected: the implementation plugin, which would then own task decomposition and routing |
| One ticket | the same plan skill; a plan with one ticket publishes one issue with no parent. Rejected: keeping the `distill` issue lens for small work, which leaves two issue formats; and a separate fast skill |
| Ticket body | the script writes the findings each acceptance sentence rests on, in their own words with citations and the commit they were checked at, under a line budget. Rejected: pointers only, which makes the session derive again what the case established; and a link to the page, which a session cannot read through `gh` |
| Interface agent | in version 1, written for Opus 5.5: it runs only when asked, and a wrong interface misleads every ticket above it in the lane. Rejected by the owner: the field and the page alone with the primary drafting. Rejected: Sonnet 5.5; and inheriting the session's model, because an agent file is written for one model |
| Interface output | a checked preview: the agent type-checks its signatures in a scratch worktree that is thrown away, and returns text for the plan record. Rejected: unchecked text; and real stubs on a branch, which has red-thread committing code |
| Lanes | the plan computes lanes and stack order, and each ticket states its branch, its base and its place in the stack. The owner starts the sessions and runs `gh stack`. Rejected: dependencies alone, which drops the check that makes parallel work safe; and a helper that creates worktrees |
| Closing | a close step in version 1 checks that each ticket's pull request has merged, closes the sub-issues and then the epic, and reports what it could not close. The retrospective takes the step over later |
| Revisions | a new revision is synced to GitHub by ticket id: it edits the tickets it touches, adds new ones and closes dropped ones. Rejected: publishing once, after which the issue and the plan drift; and replacing issues, which churns the numbers pull requests point at |
| Done when | the work after version 1 is planned as an epic with version 1 and run through plain sessions |

### 2026-11-26: packages, worktrees and links

Made by the owner on 2026-11-26, after reading the first plan page and finding it unclear: it had no grounding text, no account of what changed, and words such as "lane" that it never explained, and it was laid out for a phone only.

| Decision | Choice |
| --- | --- |
| Packages | three: `packages/core` (`red_thread_core`) holds the document model, the page and Markdown writers, the page assets, redaction, the store protocols and where the pages sit; `packages/casefile` depends on core; `packages/plans` (`red_thread_plans`) depends on both. Rejected: keeping the plan inside casefile, which coupled the two records. The split went on top of the existing commits |
| Plan home | beside the cases: `.red-thread/plans/<plan-id>/` holds `plan.json` (the id, title, the cases its revisions cited, and the epic and issue links), `rN.json` and `plan.html`. A plan never writes into a case directory |
| Many cases | a plan names each case it rests on with an alias, and one plan can rest on many cases. A finding id is `C1.e4`, or `C2.T1.e2` for a finding in a thread |
| Acceptance | a criterion is `{criterion, required_by}`, replacing `{text, rests_on}`, so it is not confused with a finding's `rests_on` caveat |
| Worktree | "lane" became "worktree" everywhere: one git worktree and one stack of pull requests |
| Plan command | its own launcher, `bin/redthread-plan`, with `init`, `revise` and `render` |
| The plan page | each criterion shows the text of every finding that requires it, linked to that finding on its board; a "What changed" section opens a revision after the first; each ticket shows its why, and a changed ticket shows each field as it was and as it is; every page ends its rail with a fold that explains its words |
| Links | both ways: the plan page links each case's board, the epic and each issue, and reads "not published yet" until a publish step records them. Each board lists the plans that cite its case, read from `.red-thread/plans/*/plan.json` when the board is drawn, so nothing is written into the case |
| Layout | every page: at 1280px and up, a rail with the title, facts, toolbar, contents and terms beside the content, where the kind sections or the worktrees sit in columns; on a phone the rail sits on top and the columns stack |

### 2026-11-26: the plan skill

Made by the owner on 2026-11-26, before and during the build of `skills/plan/`. Section 13 holds the design.

| Decision | Choice and reason |
| --- | --- |
| Order | build step 5, the plan skill, before step 4, the interface agent. The plan command existed with no skill to drive it, so a session could not make a plan without typing `bin/redthread-plan` by hand. The skill leaves out the interface offer until step 4 is built. Publishing the epic stays step 6 |
| Lineage | the skill descends from three mightymodels skills, as `debug` descends from `whats-broken`: `game-plan` (intent, approach, invariants, acceptance as observable outcome sentences, non-goals, the consistency check, and the risk interview, with its fixed list of four handlings replaced as section 13 decided), `cross-examine` (the depth question, the frontier of decisions asked in rounds, the shape of a question with what each option buys and costs, facts to scouts and decisions to the owner) and `break-it-down` (cutting by behaviour, module and order, the size of a piece, and the repository passing after each one). It leaves behind `ticket.yml`, `plan.md`, the mighty-mcp state and its `task_*` tools, `terry-toolchain` and worker routing |
| Picking cases | the skill asks every time, with each case's target, kind and date, even when there is one. Rejected: taking a lone case without asking, which plans silently from a stale or unrelated case; and inferring the case from the conversation, where a wrong match looks plausible |
| Decisions made while planning | recorded as `decision` findings in the case they bear on, in that case's next round, so a criterion can name them. Rejected: a planning case per plan, which adds a case of decisions with no knowns; and no new decisions, which sends every small design choice back through investigate |
| Review | `peer-review` gains a plan briefing (PLAN, CASES) beside its case briefing. Rejected: reusing the case briefing unchanged, which judges whether claims hold and not whether a criterion follows from them; and deferring the review |
| The page | the skill asks at the gate whether to publish `plan.html` privately, and says first that its links to the boards do not open on the published page. Rejected for now: local only until step 6 records a link; and publishing whenever the cases were published |
| Skills split | the parts the plan skill took from mightymodels are skills of their own, so each can grow apart from the plan: `cross-examine` (`skills/cross-examine/`, invocable by the owner as well), the interview and the rules for putting any question to the owner; `risk-register` (`skills/agents/`, loaded by plan), finding risks, their signals and the handlings; and `break-it-down` (`skills/agents/`, loaded by plan), cutting tickets, worktrees and stacks, and splitting one ticket. The owner kept the names `cross-examine` and `break-it-down` because they say what the skill does, and asked for a project-management name for the risk dialog. The investigate and debug gates do not load `cross-examine` yet |
| Draft before acceptance | added while building and confirmed by the owner on 2026-11-26: the draft lives in `draft.json` in the plan directory and `revise` runs only once the owner accepts, because a revision is an accepted plan (section 13, "What crosses the boundary") and `revise` has no dry run. A refusal at that point is fixed and, when the fix changes what the owner saw, put to the gate again |

### 2026-11-26: game-plan, the review before the risks, the lights and course-correction

Made by the owner on 2026-11-26, after reading the first build of the plan skill.

| Decision | Choice and reason |
| --- | --- |
| Name | the plan skill is `game-plan` (`skills/game-plan/`, `/red-thread:game-plan`), as in mightymodels. "plan" said too little: it is also the record, the command and the page |
| Cross-examine | `game-plan` invokes `cross-examine` with the Skill tool on every run, before the draft, as mightymodels `game-plan` does. The owner keeps a small plan short by picking Skim. Rejected: loading it only for its question rules, which let a session draft from cases that looked settled |
| Review before the risk register | the adversarial review runs after the draft and before the risk dialog, so the risks are defined by a party that did not write the plan. The draft reaches `peer-review` with `risks` empty, and its fifth check, Risks, names them from the plan and the cases alone. `risk-register` then starts from the reviewer's risks in the reviewer's words, adds what the interview left open, and only then asks for handlings. Reason: in the first build the drafter wrote the risks and described their handlings, and some were misrepresented, close to straw-manning the options the drafter did not favour. The review stays optional: the skill asks the owner every run, recommending it; without it the drafter writes the risks and the dialog says they were not reviewed |
| Fair options | `cross-examine`'s rules for putting a question, which every red-thread skill follows, and `risk-register`'s rules for the handlings, now require each option written as its strongest advocate would, a cost the option itself causes (never "lacks what the recommended option gives"), no loaded words on the options not recommended, the recommended option's worst realistic outcome, and a side-by-side check before sending |
| Lights | the gate asks "Is this a lights on or off kind of task?". On: the owner is in the loop while the tickets are built and iterated on, and steps in at each fork in the road. Off: the owner is away, so whoever runs the work adapts how it is done and stops for anything that changes what a ticket promises. The answer is stored as `lights` (`"on"`, `"off"`, or absent when not asked) in the plan record and shown among the page's facts. Rejected: a note in the plan's text, which nothing downstream can read; and a per-ticket setting, which nobody asked for |
| The gate | four options, the most a dialog holds: Accept, Change tickets (drop or split, asked next), Redirect, Abandon. The first build had five |
| Course-correction | a user-facing skill, `skills/course-correction/`, for a fork in the road while a plan's work runs. It names the divergence as expected against observed, first-hand; sends the scouts in parallel (`code-lens` or `code-sense`, `web-head`, `lab-rat`) on one to three hypotheses; classifies the cause as a plan gap, a false assumption, the environment, or an implementation slip, which goes to `debug`; and adapts. With the lights on the owner chooses, and a changed promise becomes a new revision. With the lights off only how the work is done changes, recorded as a `next` finding, and a fork that would change a promise is recorded as an `open` finding and waits. The name is the owner's |

### 2026-11-26: one ticket per plan, in Markdown

Made by the owner on 2026-11-26, after the game-plan build. The owner objected to two things: a plan that held several tickets, and a plan stored as JSON behind a command line that worked like an MCP server, with every write going through it. red-thread is moving away from that.

| Decision | Choice and reason |
| --- | --- |
| Hierarchy | a plan is the plan of one ticket. An epic holds several tickets, and the skill that cuts an epic into tickets comes later. Until then, `game-plan` sizes the work by `break-it-down`, and when it is more than one ticket the owner picks the one this plan covers; the others are named under Non-goals as "a ticket of its own". Worktrees and stacks leave the plan and wait for the epic skill |
| Format | a plan is one Markdown file, `.red-thread/tickets/<plan-id>/plan.md`. YAML frontmatter holds what a script reads (`id`, `title`, `status`, `revision`, `created`, `head`, `cases`, `lights`, `epic`, `issue`), and the body holds the sections a person reads: Intent, Approach, Invariants, Non-goals, Acceptance, Tasks, Risks and Changes. A criterion is a `- ` line under Acceptance that ends with its finding ids, such as `(C1.e1, C1.e2)`. Rejected: the JSON record, which the owner did not want to read or write |
| Tooling | `bin/redthread-plan` has two verbs. `init --title T --case ID ...` writes the frontmatter and the section headings; the skill then writes the body by hand. `check --plan PATH` reads the plan and its cases and names every fault with its fix, and writes nothing. Rejected: a command that also rewrites the plan, which brings back the command-line-as-MCP shape |
| Tasks | the body has ordered tasks, numbered in the order the work is done. Each one is a change a reviewer could check alone, and the repository passes after it |
| Revisions | the plan is edited in place. After the owner accepts it, each change adds one to `revision` and a line under Changes. Rejected: one file per revision, which needs a command to write it |
| Page | the Markdown file is the artifact. `plan.html` is gone, and boards no longer list or link plans |
| YAML | PyYAML, through `msgspec.yaml`, decoding the frontmatter into a frozen Struct that refuses unknown keys. A bare `on` or `off` reads as a boolean, so `lights` is written with quotes and the refusal says so |
| The case file | moves to Markdown with frontmatter next, by the same rule. Built on 2026-11-26: see "the case file in Markdown" below |

### 2026-11-26: wording and tables as packaged YAML

Made by the owner on 2026-11-26. The board's glossary was a Python module of constants, and other tables were the same: text and structure a person edits without touching logic.

| Decision | Choice and reason |
| --- | --- |
| What moved | the glossary terms, the section headings with their notes, the note prefixes, and the map and retired notes into casefile's `wording.yaml`; the four lenses and the reading lines into casefile's `lenses.yaml`; the plan's section headings and the required ones into plans' `outline.yaml`. Error messages stay in code, beside the fields they name |
| Primitive | `red_thread_core.packaged`: `read_asset_text(package, name)` reads a file under the package's `assets/`, and `load_asset(package, name, shape)` decodes a YAML file into the shape with `msgspec.yaml`. Each shape is a frozen Struct that refuses unknown keys. Core therefore depends on msgspec and PyYAML, which ends its standard-library-only rule. Rejected: a text-only core with the decoding in each package |
| Loading | at the edge: the `CaseFiles` and `Plans` factories load the tables once and inject them into the case file, the press, the board, the lens composer and the planner. Nothing reads a file at import |
| Asset home | every package keeps its assets under `src/<module>/assets/` and reads them through `importlib.resources`, so a built wheel carries them. navigate's vendored queries moved to `red_thread_navigate/assets/queries/` and load through the same primitive, so navigate depends on core |
| Checks | tests hold each table complete: a heading for every finding kind, a prefix for every note kind, a lens for every lens name, every required plan section among the sections |

### 2026-11-26: the case file in Markdown

Made by the owner on 2026-11-26, at the gate before the build, by the rule that moved the plan to Markdown: the case file was JSON behind a command line that every write went through.

| Decision | Choice and reason |
| --- | --- |
| Layout | `case.md` holds the frontmatter and the primary's rounds, and each lead appends to its own `threads/T<n>.md`, so two writers never share a file. A lead appends with a quoted heredoc and runs `check`. `research-lead` keeps Agent and Bash and gets no editing tool |
| Finding syntax | a `### e<n>` heading over a fenced `yaml` block, decoded by `msgspec.yaml` into a strict Struct. |
| Outputs | `render` and `export` stay. They read the files and write only `board.html` and `out/`. `page` goes: `page_url` is a frontmatter key written by hand |
| Stamps | each round is a `## Round N · YYYY-MM-DD · HEAD` heading, and its findings take their round, date and commit from it. `check` faults a missing or malformed heading, a `path:line` cite with no `quote` (and prints the line to paste) and a secret, and writes nothing |
| Pre-approval | the skills' `allowed-tools` still name only the scripts. Appending is a plain Bash command, so a session in a permission mode that asks prompts once per round; the owner's sessions run sandboxed Bash without asking. Rejected: `Bash(cat >> *)`, which would approve an append to any file |
| Compatibility | none. The JSON code, the `add` and `page` commands and their tests were deleted; a case made before this change is not read |

### 2026-11-27: an element builder for the HTML

Made by the owner on 2026-11-27. The HTML fragments moved from the t-string `render` to Jinja templates (commits b562212 and d7d129c on `chore/code-quality-fixes`), and the owner then had both commits reverted in favor of standard-library primitives.

| Decision | Choice and reason |
| --- | --- |
| Primitive | `red_thread_core.elements`: a frozen `Element(tag, attrs, children)` built with `element(tag)`. `attributes(mapping)`, `nest(*children)` and `set_text(text)` each return a new element, and `nest` skips `None`, so a writer passes an optional part without a branch. `render()` writes it. No dependency: `html.escape` escapes every text and attribute value. Rejected: a mutable builder, and Jinja for the reasons in section 4 |
| Attributes | `True` is written bare, `None` and `False` are left out. `href` and `src` keep only a relative URL or an http or https one, read after the characters a browser strips; any other scheme, such as `javascript:`, leaves the attribute empty |
| Layout | indented two spaces per level. An element stays on one line when it is a `pre`, is empty, holds text, holds only phrasing children, or holds two phrasing children side by side, so no whitespace appears between inline elements a reader sees. Every other element puts each child on its own line |
| Skeleton | `page.html` stays a `string.Template`. The writers build the fragments that fill its slots, and `render_fragment` writes each on its own line |
| Scope | HTML only. The Markdown writer keeps drawing from the document tree |
| Checks | the builder's tests cover escaping (as properties), the URL guard and the layout rules. The page tests read the page with whitespace allowed between tags |

### 2026-11-27: data values as DTOs

Made by the owner on 2026-11-27. The DTO base (`red_thread_core.dto.DTO`) carried only the records read from files; every other value was a frozen dataclass copied with `dataclasses.replace`.

| Decision | Choice and reason |
| --- | --- |
| What is a DTO | every class that only carries data: the document tree and the element builder, the case file's domain records and readings, the plan document, and navigate's symbols, addresses, walks and results. They subclass `DTO` with `gc=False` and copy with `replace_with` |
| What stays a dataclass | policies, services, writers, stores, backends, views and the cyclopts argument classes, which hold collaborators or make decisions; and three values with a mutable or live field (`SkipTally`'s `Counter`, the tree-sitter `Definition`'s node, `Detector`'s compiled patterns) |
| Rule | `.claude/rules/python.md` picks the type by role in place of by boundary |
| Narrowing | ty does not treat a Struct as disjoint from `str`, so a union of `FrontSplit` and `FenceProblem`, or of `SourceFile` and `SkipKind`, narrows with `isinstance(value, TheStruct)` |

### 2026-11-27: findings and finding ids

Made by the owner on 2026-11-27. "Entry" did not say what it was an entry of, and "ref" meant nothing to a reader of one file.

| Decision | Choice and reason |
| --- | --- |
| The record | an entry of a case is a finding: `CaseFinding` in code, "finding" in prose. The citation result that held the name `Finding` is now `CitationCheck`, and `Ledger` is `CaseLedger` |
| Its address | a ref is a finding id: `finding_id` in code, "finding id" in prose, `FINDING_IDS` as a dispatch placeholder. The text stays `e4` and `T1.e2` |
| On disk | the case file format does not change: a block keeps its `cite`, `addr` and `refute` keys, which the Python fields `citation`, `code_address` and `refuted_if` encode to |
| Other names | each function, constant and field says what it holds or does, such as `write_citation_state_badge` in place of `write_state` and `opening_tag` in place of `opening` |

### 2026-11-27: time in one core module

Made by the owner on 2026-11-27. Time handling was spread out: the clock sat in core's `store.py`, the tree-sitter deadline in navigate, and the case file kept its days and moments as strings checked by `date_of` and `is_day`.

| Decision | Choice and reason |
| --- | --- |
| Where | `red_thread_core.timekeeping` holds the `Clock` protocol, `SystemClock`, the day and moment text (`write_moment`, `write_compact_day`, `read_day`) and `Deadline` |
| Typed values | `Clock.now()` returns an aware `datetime`; `Case.created` is a `datetime`, and a finding's `at`, a round stamp's `day` and a finding node's `at` are `date`s. Text exists only where a file is read or written |
| Reading `created` | the frontmatter is converted with `strict=False`, so a quoted ISO moment (what `init` writes) and a bare one both read. A bare day or a word is still refused, and so is `publish: 'yes'` |
| Writing `created` | written through `write_moment`, so a case file keeps the quoted `'2026-11-21T09:30:00+00:00'` form older case files hold |
| Errors | `InvalidTimestampError` is gone: a bad `created` is a `MalformedFrontmatterError`, and a bad round day a `MalformedRoundError` |
| Tests | `tests/core/timekeeping` holds the fixed clock, `MOMENT`, `DAY` and the `days` and `moments` strategies every test tree imports |

## 13. Planning

**Changed 2026-11-26** (section 12, "one ticket per plan, in Markdown"): a plan is now the Markdown plan of one ticket, `.red-thread/tickets/<plan-id>/plan.md`, started by `redthread-plan init` and checked by `redthread-plan check`. "The plan file" below describes it. The JSON plan record, its revisions, the plan page, worktrees and stacks in a plan, and the board's links to plans described further down are superseded, and their code is gone. They stay here as the record of what was built.

Added 2026-11-25. Section 12 records what the owner decided. The build order at the end says which steps are built; everything else here is **Proposed**.

**Changed 2026-11-26** (section 12): a plan lives in `.red-thread/plans/<plan-id>/`, not in a case, and rests on one or more cases through aliases. "Lane" is now "worktree", and an acceptance sentence is now a criterion `{criterion, required_by}`. The `plan` command is `bin/redthread-plan` with `init`, `revise` and `render`. The text below uses the new names.

### Version 1

Decided 2026-11-25 (section 12).

| In version 1 | After version 1 |
| --- | --- |
| The plan record, the `plan` command and its checks | Briefs and the routing agent |
| The plan page | Events, and status and elapsed time on the page |
| The game-plan skill: draft, the optional review, risks, the gate | The retrospective |
| The interface agent | The implementation plugin, a separate project |
| Publishing an epic or a single ticket, and syncing a revision | |
| The close step | |

A plain Claude Code session in a worktree executes a ticket from the issue alone. It writes no events, so progress in version 1 is GitHub's rollup and the page as of the last revision.

### What crosses the boundary

red-thread ends at a published ticket and its briefs. The implementation plugin starts there and never reads the case file. Whatever crosses a worktree goes through the issue, because the case directory exists in one checkout only.

| Artifact | Record | The owner reads | Read by |
| --- | --- | --- | --- |
| Plan | `.red-thread/tickets/<plan-id>/plan.md`, one Markdown file per ticket, edited in place, beside the cases it rests on (changed 2026-11-26; until then `.red-thread/plans/<plan-id>/r<n>.json`) | the file itself | the owner and `peer-review` |
| Epic | a parent issue | the issue and GitHub's sub-issue progress | the retrospective |
| Ticket | a sub-issue: prose, then one fenced JSON block under a `red-thread ticket v1` summary | the issue | the implementation plugin, through `gh issue view` |
| Brief | `briefs/T<n>.md` in the ticket's worktree: YAML frontmatter, then the body | the page when the ticket starts | the subagent the brief names |
| Events | a JSONL file the implementation plugin's hooks append to, summarised in an issue comment when the ticket closes | status and elapsed time on the page | the retrospective |

Each record carries a schema version, so the two plugins release separately.

### The plan file

**Built 2026-11-26.** `red_thread_plans` is the only code that starts or checks a plan, and the skill writes the body by hand.

- `init --title T --case ID [--case ID ...] [--slug S] [--root R]` refuses no case, a case that is not under `.red-thread/`, and a plan that exists already. Otherwise it writes `plan.md` with the frontmatter (`status: draft`, `revision: 1`, the date, the short HEAD, the cases as C1, C2 in the order given) and one heading per section, and prints `created` and the path. The plan id is the UTC date and a slug of the title, as for a case.
- `check --plan PATH` takes the file or its directory. It refuses a file that does not open with `---`, has no closing `---`, or whose frontmatter does not decode, at the first fault. A readable plan is checked whole and every fault is named with its line: no case, a case missing from `.red-thread/`, an accepted or done plan with no `lights`, a section heading missing, Intent, Approach, Acceptance or Tasks left empty, no `- ` criterion, a criterion with no finding id, a finding id anywhere in the body that is not a finding of its case or was retired, and a criterion finding id that is not a `decision` or `known`. Finding ids to a missing case are not checked twice. It prints `checked <path>: N criteria rest on M findings`.

### The plan record (superseded 2026-11-26)

The plans package is the only writer of a plan. `revise` reads one JSON document on standard input or from `--file`, checks it whole as `add` checks a batch, and stores it as the next revision. A revision is never edited: the page shows the latest and what changed from the one before.

- Fields: intent, approach, the cases it rests on, invariants, non-goals, tickets and risks.
- A ticket has an id, a title, a why, acceptance criteria, the files it owns, the tickets it depends on, a worktree and an optional interface.
- An acceptance criterion states an outcome someone can observe, and names the live `decision` or `known` findings that require it. The script refuses one that rests on nothing. This is the guard against "that is not what I asked for": every promise in the plan traces to something the owner decided or a scout verified.
- The script refuses a dependency cycle, and refuses two tickets in different worktrees that own the same file.
- "Plan" already named the JSON that `export` reads (section 6, `lenses.py`). That document is now the "selection", and `--plan` is `--selection` (built 2026-11-25).

**Built 2026-11-25**, with the owner's approval of the record and its refusals:

- A revision is `r<n>.json` in the plan directory: the drafted fields, plus `schema` (`red-thread/plan@1`), `revision`, `at` and `head`, which the script stamps. It is created exclusively, so a stored revision is never overwritten.
- A ticket's `id` and `worktree` are lowercase slugs. An acceptance criterion is `{criterion, required_by}`, where each finding id names a case alias. The interface is `{language, source}`.
- A risk has an `id` (`R1`, `R2`), `risk`, `signal`, the `tickets` it touches and a `handling` tagged by `kind`: `accept`; `mitigate` with the `ticket` that carries the change and an optional `criterion`, which must be one of that ticket's criteria word for word, or is left out when the ticket itself is the mitigation; or `you-intervene` with the `recut` tickets, which must be among the risk's own.
- The drafter names each ticket's worktree, and the script computes its position: a stable topological order of the worktree's tickets, ties kept in drafted order. This settles section 12's "the plan computes lanes and stack order" against "the plan records only lane and position" below: the plan computes the stack and checks the worktrees, and does not invent them.
- A dependency on a ticket in another worktree is refused (owner, 2026-11-25), because a worktree is one stack.
- Two worktrees collide when some path, existing or not, matches an `owns` finding of each. The check is exact for `*` (any run of characters within one segment, a leading dot included), `?` and `**` (zero or more segments, or at least one at the end), the rules of `PurePosixPath.full_match`, and the refusal names a path both worktrees could change. `dir/` means `dir/**`. A finding that is empty, absolute, climbs with `..` or uses a `[ ]` class is refused. Two tickets in one worktree may own the same files.
- A plan that cannot be read is refused at its first shape fault, with the JSON path. A readable plan is checked whole and every fault is named with its fix: blank text, no tickets, a ticket without acceptance or owns, a malformed or duplicate id, no case or a case missing from `.red-thread/`, a ticket without a why, a criterion required by nothing or by a finding id that is unknown, retired or not a decision or known, an unknown or cross-worktree dependency, a cycle, a worktree collision, and a risk that names an unknown ticket, a criterion the ticket does not have, or a recut that is empty or strays outside the risk. Text is checked as sent, then redacted, then stored.

**The page, built 2026-11-25, rebuilt 2026-11-26, removed 2026-11-26:**

- `revise` writes `plan.html` in the plan directory each time it stores a revision, from that revision, the one before it and the cases it rests on. A refused plan writes nothing. `render` draws it again from the latest revision.
- `PlanPage` (`red_thread_plans/page.py`) composes the page. Its sections are What changed (from the second revision on: the tickets added, changed and dropped, then each plan field as it was and as it is), Approach, Cases (each alias linked to its board, with the case's question), Invariants, Non-goals, one `Worktree <name>` column per worktree with its stack bottom first, and Risks. The appendix holds the `Worktrees` chart and, when tickets were dropped, a folded `Dropped` list. The facts are the revision, the date, the commit, the ticket and worktree count, the changes and the epic.
- A ticket shows its mark, its title, its why, its place, its dependencies, the paths it owns, its issue link or "not published yet", each criterion under "Done when" with every finding that requires it (its kind, its finding id linked to `../../<case>/board.html#<finding id>` and its text), its interface, and for a changed ticket a fold of each field as it was and as it is. A finding id whose finding is gone reads "This finding is no longer in the case."
- The status mark compares each ticket with the ticket of the same id in the revision before: `new` when it had none, `unchanged` when every field is equal, `changed` otherwise. Status from events stays after version 1.
- `Flowchart` draws each worktree as a subgraph, with an arrow from each dependency to its dependent and each node coloured by its mark (header `packages/plans/assets/worktrees.mmd`).
- `CodeListing` is a general block in the document model, written as `<pre class="listing">` on a page and as a fenced block in Markdown. The plan's own nodes, `TicketNode`, `Promise`, `Ground`, `TicketList` and `ChangeList`, live in `red_thread_plans/nodes.py` and reach the writers through `BlockWriter.write_tickets`, as every other block does.
- The toolbar adds worktree and status chips beside the kind and thread chips. `page.js` filters any finding that carries `data-kind` or `data-worktree` on every chip group, so `Section.kind` stays a finding kind. It also opens the folded section that holds the target of a `#ref` link, on load and when the hash changes.
- The board lists the plans that cite its case as a `Plans` fact linking `../plans/<plan-id>/plan.html`, read from each `plan.json` when the board is drawn; a plan index that cannot be read is skipped. Each finding is an anchor named by its finding id.

### The game-plan skill

1. Start from a case. Run `check` first, as `distill` does, so a plan is not cut from changed citations.
2. Draft the tickets from the case's decisions and knowns. Stay at intent, acceptance and ownership: task detail waits for the ticket to start.
3. Offer the interface preview.
4. Put each risk to the owner.
5. Offer the review.
6. Gate: the owner accepts, redirects or drops tickets. On acceptance the script stores the revision and the page is published.
7. Publish the epic to GitHub after one approval that covers every issue it will create.

**Built 2026-11-26** as `skills/plan/`, renamed `skills/game-plan/` the same day, with steps 3 and 7 left out (section 12, "the plan skill"). The skill asks the owner which cases the plan rests on, runs `check` on each, then settles the design in rounds of questions before drafting, through `cross-examine`. Each answer is recorded as a `decision` in the case it bears on, through `redthread-casefile add`, so a criterion can name it in `required_by`. The draft is `draft.json` in the plan directory, cut into tickets by `break-it-down` and checked by the consistency check in `references/draft.md`; `revise` reads it only once the owner accepts at the gate, and the file is deleted once the revision is stored. The risk dialog, `risk-register`, records each handling as a `decision` too, so a mitigation's criterion rests on it. After storing, the skill draws each board again so it lists the plan, and asks whether to publish `plan.html`. The interface offer waits on step 4 of the build order, and publishing the epic on step 6.

**Changed 2026-11-26** (section 12, "game-plan, the review before the risks"): the order is now cases, check, the cross-examine interview on every run, the draft with no risks, the optional review that names the risks, the risk dialog, then the gate, which also asks whether the lights are on or off. Forks in the road during the work go to `course-correction`.

**Changed 2026-11-26** (section 12, "one ticket per plan, in Markdown"): after the interview the skill sizes the work by `break-it-down`, and when it is more than one ticket the owner picks the one the plan covers. It runs `init`, writes the body into `plan.md` as `references/plan.md` says, and runs `check` with the consistency check. At the gate, Change tickets became Change the tasks. Accepting sets `status: accepted` and `lights` in the frontmatter and runs `check` again. No board is drawn again and nothing is published.

### Risks

Each risk states the risk, a signal someone can observe, and the tickets it touches. The handlings are:

- **Accept**: proceed, and note the signal.
- **Mitigate**: shown as the change itself, a criterion added to a named ticket or a new ticket, so the owner judges a diff and not a promise.
- **You intervene**: work on the touched tickets stops when the signal appears and the owner decides. The plan names which tickets would be cut again.

Since 2026-11-26 a risk touches tasks of the one ticket, by number, and a risk is a `- R<n>:` line under Risks with its signal, tasks and handling nested below it.

The dialog offers only handlings a senior engineer could pick, states the cost of each including the recommended one, and offers two when there are only two. mightymodels had the same rule in prose (`game-plan`, "Stack the options evenly") and a fixed list of four, and the list is what produced the padding.

### Review

Optional, asked at step 5. One `peer-review` pass in a fresh context that gets the plan and the rendered case, not the conversation. It checks that each criterion follows from the findings that require it, that no decision is left without a ticket, that worktrees do not collide, and what the plan assumes without evidence. A finding without a finding id or a `path:line` is dropped. The owner picks which findings change the plan. There is one pass and no debate round.

**Built 2026-11-26:** `peer-review` takes a plan briefing, PLAN (the draft file) and CASES (one alias and case directory per line) in place of CASE and CONCLUSION, and returns a table of findings, each with its place in the plan, its check and its evidence. Its collision check looks for a dependency between worktrees that own different files, such as a shared interface, because the script already refuses two worktrees that own the same path.

**Changed 2026-11-26** (section 12, "game-plan, the review before the risks"): the review runs before the risk dialog, on a draft whose `risks` are empty, and a fifth check, Risks, names the plan's risks with a signal, the tickets and the evidence of each, in a second table. `risk-register` starts from those risks in the reviewer's words, so the risks are defined by a party that did not write the plan. The review stays optional, and the skill asks every run.

**Changed 2026-11-26** (section 12, "one ticket per plan, in Markdown"): PLAN is the `plan.md` file, and the third check, Apart, became Ordered: whether the tasks can be done in the order written and whether the last one meets every criterion.

### Course correction

A fork in the road while a plan's work runs goes to `course-correction`, built 2026-11-26 (section 12). It reads the plan from the main checkout's `.red-thread/`, also from a worktree, names the divergence as expected against observed, sends the scouts in parallel on one to three hypotheses, and classifies the cause: a plan gap, a false assumption, the environment, or an implementation slip, which it hands to `debug`. The plan's `lights` decide who adapts: with the lights on the owner chooses and a changed promise is a new revision; with the lights off only how the work is done changes, and a fork that would change a promise waits as an `open` finding. It has not run on a real plan.

**Changed 2026-11-26** (section 12, "one ticket per plan, in Markdown"): it finds `plan.md` under `.red-thread/tickets/` and edits it in place, adding one to `revision` and a line under Changes. The intent, the approach, the criteria, the invariants, the non-goals and the risks' handlings are what the plan promises; a change to the tasks that keeps them is how the work is done, so with the lights off it is written into the plan with its Changes line.

### Interfaces

Optional, per ticket, by a dedicated agent written for Opus 5.5 and not yet named. It writes the public surface only: signatures, types, error cases and the names of the tests. It type-checks them in a scratch worktree that is thrown away and returns the text for the plan record, so the preview is known to compile and nothing lands in the repository. The preview shows on the page and in the issue. A worktree may open with a ticket that lands the interfaces and their failing tests, so the bottom pull request of the stack is the contract. Internals stay out, because detail fixed this early is wrong often enough to cost more than it saves.

### The epic on GitHub

- The epic is a parent issue, and each ticket a sub-issue created with `gh issue create --parent`. Order is `--blocked-by`. Both need gh 2.94.0 or later.
- A plan with one ticket publishes one issue with no parent.
- The script assembles a ticket body: the goal, the acceptance sentences, the owned files, the branch, its base and its place in the stack, each "You intervene" signal as a condition to stop on, then the findings the acceptance rests on, in their own words with citations and the commit they were checked at. The body has a line budget.
- A new revision is synced by ticket id: it edits the bodies of the tickets it touches, adds sub-issues for new tickets and closes dropped ones. The case keeps the map from ticket id to issue number.
- Limits: 100 sub-issues per parent, eight levels, 50 links per dependency type.
- GitHub reports the rollup itself, as `sub_issues_summary.percent_completed`.
- Closing is explicit. Closing keywords are read only when a pull request targets the default branch, and the stacked pull request pages say nothing about them, so a close step checks that each ticket's pull request has merged, runs `gh issue close` for the ticket and then the epic, and reports what it could not close. The step is part of the game-plan skill in version 1, and the retrospective takes it over.

### Worktrees and stacks

**Changed 2026-11-26:** worktrees and stacks belong to the epic, whose skill is not built, and no longer to a plan.

A worktree is one git worktree and one stack (called a lane until 2026-11-26). Tickets that depend on each other share a worktree and become one pull request each, bottom up. Worktrees that own disjoint files run in parallel. The plan records only `worktree` and position. In version 1 the owner creates the worktrees and runs `gh stack`; later that belongs to the implementation plugin. A ticket that cannot keep its files apart from another worktree joins that worktree.

### Ticket start: briefs and routing

After version 1. When a ticket starts, a red-thread skill run in the ticket's worktree cuts its tasks against HEAD. It reads the ticket from the issue, because the case directory is in another checkout. A task is one deliverable with one verification command: a function, a test file or a review.

```yaml
---
schema: red-thread/brief@1
ticket: 42
task: T3
depends_on: [T1]
owns: [packages/casefile/src/red_thread_casefile/lenses.py]
acceptance:
  - export refuses a selection that names a retired finding id
verify: uv run pytest -q tests/casefile/lenses
agent: python-harness:test-engineer
skills: [python-harness:design-tests]
mcp_tools: []
---
```

A routing agent, the successor to `terry-toolchain`, fills `agent`, `skills` and `mcp_tools`. It reads the names and descriptions of what is installed, narrows the candidates by the language and paths of the owned files, and picks among the few that remain with one line of reason. With no match it names the implementation plugin's default implementer. The owner sees the choice with the brief and can change it. In mightymodels the survey never changed which worker a task went to: the choice was a fixed table, and `subagent_type` had to start with the plugin's own prefix. The implementation plugin must not carry that restriction.

### Progress

After version 1. red-thread ships no hook for this. The implementation plugin's hooks append one event per transition, with the time, the ticket, the task and what happened, and stamp the time themselves because `SubagentStop` carries none. The page shows each ticket's status and elapsed time and is republished at each transition.

### Retrospective

After version 1. Replaces `prune-ticket`. Friction is recorded when it happens: a blocked task, an escalation, a brief written again, a scope expansion, a "You intervene" that fired, and the owner saying the result is not what they asked for. The retrospective reads that record, says what slowed the work and where it left the plan, and classes each item as a plan gap, a brief gap, a routing miss or an environment problem. It proposes changes to instruction files, skills and hooks as diffs the owner approves, then closes the issues.

### Evidence

Read on 2026-11-25.

| Claim | Source |
| --- | --- |
| A planner that fixes granular detail early passes its errors down; a contract for "done" is agreed before code | Anthropic, "Harness design for long-running apps" |
| JSON for state an agent must not rewrite; one feature at a time | Anthropic, "Effective harnesses for long-running agents" |
| A brief needs an objective, an output format, tool guidance and boundaries | Anthropic, "How we built our multi-agent research system" |
| A fresh reviewer helps, and one asked to find problems always finds something | Claude Code docs, best practices |
| Each parallel worker gets its own checkout and its own files | Claude Code docs, best practices and agent teams |
| A server pushes into a session only through channels, a research preview | Claude Code docs, MCP and channels |
| Stacked pull requests are generally available since 2026-10-06, with `gh stack` and a REST API | GitHub changelog and docs |
| Closing keywords are ignored off the default branch | GitHub docs, "Linking a pull request to an issue" |
| Specification and verification failures dominate multi-agent runs; a high-level verification step added 15.6% task success | MAST, arXiv 2503.13657 |
| Self-correction without outside feedback can lower accuracy | Huang et al., arXiv 2310.01798 |
| Interfaces first, and tests from a separate agent, raise pass rates | Parsel, arXiv 2212.10561; AgentCoder, arXiv 2312.13010 |
| The best method finds the decisive failing step 14.2% of the time after the fact | Who&When, arXiv 2505.00212 |

Not verified: no study was found of padded options in agent plans or of interface previews as a review aid, and the routing accuracy figures came from search summaries.

### Open

- Section 10 has no guidance for an agent file written for Opus 5.5.
- How the interface agent's scratch worktree gets the project's toolchain, and what it checks in a language with no type checker.
- The line budget for a ticket body.
- Which session republishes the page, and from what, when the case directory is in another checkout.
- Which plugin owns the retrospective. It reads execution events and reasons like an investigation.
- Whether a skill can dispatch another plugin's subagent by name. The docs do not say; a run has to confirm it.
- Whether a closing keyword takes effect after GitHub retargets a stacked pull request onto the default branch.
- The names of the routing agent and the interface agent.
- `plan.html` links each board as `../../<case-id>/board.html`, and a board links its plans as `../plans/<plan-id>/plan.html`. On a page published through the Artifact tool neither link opens, and `plan.json` has no field for the published page, so a later session publishes a new artifact. The game-plan skill says so when it offers to publish.
- `peer-review`'s plan briefing ran once headless on 2026-11-26 (Sonnet 5.5, `claude -p --plugin-dir`, $0.33, 2 turns of the primary) against a scratch plan with one criterion planted that its finding did not support. The report kept the plan format and listed 8 findings, the planted criterion first, each with a finding id or a `path:line`. One line of text followed the report, from the agent or from the primary that relayed it. It ran `check` and `git ls-files`, both on its allowed list. It has not run from a real game-plan session, and its Risks check, added the same day, has not run at all.

Build order for version 1:

| Step | Status |
| --- | --- |
| 1. Rename the export plan to a selection | built 2026-11-25 |
| 2. The plan record, the `plan` command and its checks: traceability, cycles and lane collisions | built 2026-11-25 |
| 3. The plan page | built 2026-11-25 |
| 3a. Core, casefile and plans packages; worktrees; criteria; cases by alias; `bin/redthread-plan`; the page's grounds, changes and terms; the rail and columns layout; links between plans and boards | built 2026-11-26 |
| 4. The interface agent | not started |
| 5. The game-plan skill: draft, the interface offer, the optional review, the risk dialog and the gate | built 2026-11-26, before step 4, without the interface offer; course-correction built the same day |
| 6. Publishing: the ticket body, issues, sub-issues and dependencies | not started |
| 7. Syncing a revision | not started |
| 8. The close step | not started |
| 9. The first epic: plan the work below with version 1 and run it through plain sessions | not started |

After version 1: ticket start with briefs and the routing agent, the event schema with status on the page, and the retrospective.
