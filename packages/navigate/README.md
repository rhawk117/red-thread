# red-thread-navigate

Code navigation for the red-thread plugin. It answers structure questions about a repository (what is in it, where a name is defined and used, what a symbol's code says) with output small enough for a scout to read and precise enough to cite. It reads Python, JavaScript, TypeScript and TSX, Go, Rust and Terraform.

The package depends on `red-thread-core`, which reads its vendored queries from `src/red_thread_navigate/assets/queries/`, and on tree-sitter and the grammar wheels for JavaScript, TypeScript, Go, Rust and Terraform, all pinned with `==`. Python uses the standard library `ast`. `docs/design.md` section 8 holds the design and the reasons for it.

## Who uses it

The `code-lens` scout runs only this tool and `rg`, with a budget of 6,000 tokens of output per question. `code-sense`, `lab-rat` and `peer-review` reach for it first on structure questions in the six languages and keep their own tools for the rest. The `skills/agents/navigate` skill is preloaded into all four and covers the commands, addresses, recipes and refusals.

The agents call it through `bin/redthread-navigate`, which starts it the same way `bin/redthread-casefile` starts the case file:

```sh
uv run --no-config --no-project --python 3.14 --with-editable <plugin>/packages/navigate -- python -m red_thread_navigate "$@"
```

Nothing is installed into the repository under investigation, and a uv setting in that repository can't change what gets installed.

## What it is for

- **Getting oriented.** `map` shows which files in a directory hold the most-referenced symbols, so a scout knows where to look before reading anything.
- **Following a name.** `find` lists where a function, type or Terraform block is defined and every line that references it.- **Reading one symbol.** `slice` prints just the code an address names, with line numbers, instead of a whole file.
- **Citing what it saw.** Every output line starts with a path and a line, so a finding goes into the case file's ledger as a citation unchanged.

It replaces agentlens, an external tool the plugin used to depend on, so the plugin ships no binaries and needs no Rust toolchain.

## Commands

```text
redthread-navigate [--budget N] map PATH
redthread-navigate [--budget N] find NAME PATH
redthread-navigate [--budget N] slice ADDRESS
```

| Verb | Output |
| --- | --- |
| `map PATH` | a header with the file and symbol counts, then one line per file with its symbol count, its reference count and its most-referenced symbols; files with the most references come first |
| `find NAME PATH` | the definitions of the name, each with its address, kind and line span, then the references as `path:line`; with no match, `no matches for NAME in PATH` and a next step |
| `slice ADDRESS` | the code the address names, with line numbers |

For example, `map` over this package's `slice` directory:

```text
6 files  61 symbols
policy.py  15 symbols  59 references  text, Refused, Wording, and 12 more
errors.py  9 symbols  27 references  __init__, __init__, __init__, and 6 more
views.py  12 symbols  27 references  Found, label, numbered, and 9 more
...
```

`find` matches a name by its full address or by its last part, so `find aws_vpc.this` and `find this` both reach the same Terraform block. `find` prints no line text for definitions, and `map` prints names only, so a scout cites only lines it actually read in `slice` or `rg -n` output.

### Addresses

An address is `file#Symbol`, `file#A.b.c`, `file#Lnn` or `file#Lnn-Lmm`. A Go method is `Type.Method` for a value or pointer receiver, and a Rust method is `Type.method`.

A symbol of 100 lines or fewer comes back whole. A longer one comes back as its signature, its docstring and an outline of its children, each with its span and the line-range address of its body, and the scout reads the part it needs with a second `slice`. An explicit line range comes back as asked. An address that matches several definitions returns all of them, each labelled with its context, and an unknown symbol lists the nearest names.

### The budget

`--budget N` caps how many tokens a call prints. It must be at least 32, and the default is 2,000. Tokens are estimated at 3.5 characters each, and no output goes over the budget by that estimate. When a result doesn't fit, the tool steps down to a shorter form, then cuts at a line boundary and ends with `showing N of M, raise --budget`. Notes about skipped files or parse errors are cut first. There is no index and no cache, so every call reads the tree as it is.

### Refusals

A refusal also fits the budget. One the scout can recover from names the next command: an unknown name, an address past the end of the file, a path outside the root and a directory each print `Next step: ...`. The navigate skill matches refusals by their stable markers (`Next step:`, `cannot be sliced:`, `nearest names:`, `is not valid:`) rather than the wording around them. A missing PATH exits 1, and an empty one is a usage error that exits 2.

## What it reads

Inside a git repository only tracked files are listed. Outside git, dot-directories and the usual build and dependency directories (`node_modules`, `target`, `build`, `dist`, `venv`, `.venv`, `site-packages`, `__pycache__` and the like) are left out. Files over 1 MiB, binary files and files that aren't UTF-8 are skipped, and a note counts what was skipped and why.

The tool resolves no path outside the root it was given and doesn't follow a symlink that leads out of it. It runs nothing from the repository it reads and writes nothing into it.

## Languages

Each language has a backend chosen by file suffix, behind one symbol model.

- Python uses `ast`, which is exact for the running Python version. A syntax error stops the parse, so the file returns no symbols and a note carries the parser's message.
- JavaScript, TypeScript and TSX, Go, Rust and Terraform use tree-sitter with a query for each language vendored in this package, so a grammar upgrade can't change the output without a change here. A parse stops after 2 seconds. A file with a syntax error keeps the symbols that parsed, and a note gives the line of the first error.
- Terraform is parsed with the HCL grammar and names blocks the way Terraform references them (`aws_vpc.this`, `data.aws_ami.x`, `module.vpc`, `var.region`, `output.id`, `local.name`), with the references between blocks.
- Go and Rust count a use of a type as a reference to it, so `find` and the `map` counts include type uses.

The design document covers the finer points: how decorators and Rust attributes fall inside or outside a span, which Rust positions count as a type reference, and how JavaScript assignments become symbols.

## Development

The tests are under `tests/navigate/` at the repository root. The evaluation cases are in `evals/navigate`, one file per language, each against a public repository at a pinned tag. No model has run them yet.
