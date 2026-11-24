---
name: navigate
description: How red-thread scouts read code structure with the navigate script (map, find, slice). Preloaded into the scouts; not for direct use.
user-invocable: false
---

# navigate

The navigate script answers questions about the structure of code in Python, JavaScript, TypeScript and TSX, Go, Rust and Terraform, and never prints more than the budget you give it. Your briefing names its absolute path as NAVIGATE. Below, NAV is that path. Run it through Bash from the repository root, which is also the root it reads; it refuses paths outside it.

## When to reach for it

Use navigate first when the question turns on structure in those six languages:

- where a name is defined, and what refers to it
- what a file or a directory holds
- the body of one function, class, method, type, constant or Terraform block
- which definition holds a given line

It answers in a few hundred tokens what `rg` plus Read answers in thousands, and it gives you the line numbers to cite.

Use `rg -n` or Read with offset and limit instead for:

- text inside strings, comments and docs (`find` skips them)
- config and data files (YAML, TOML, JSON, Markdown) and any other language
- anything navigate refuses, as the refusal list below says
- every question, when the briefing gives no NAVIGATE or the script will not run

## Commands

| To learn | Command | What it prints |
| --- | --- | --- |
| what a directory or file holds | `NAV --budget 600 map PATH` | for a directory, files most-referenced first with symbol and reference counts; for a file, one line per symbol: kind, signature line, `L57-L66` range, address, reference count |
| where a name is defined and referenced | `NAV --budget 600 find NAME PATH` | `definitions` as `address  kind  Lstart-Lend`, then `references` as `file:line` |
| the code one address names | `NAV --budget 1500 slice ADDRESS` | a header with the span and parent, then the numbered lines |
| lines you know by number | `NAV --budget 300 slice FILE#L196` or `FILE#L184-L190` | those lines, numbered |

- The only option is `--budget N`, placed before the verb: the most tokens the call may print, at least 32, default 2000. Any `rg` flag such as `-n`, `-A` or `-g` is an error.
- A NAME or ADDRESS that starts with `-` goes after `--`: `NAV --budget 600 find -- -x PATH`.
- When a call is cut it says so, as in `showing 75 of 131, raise --budget`. Raise the budget only if the question needs the rest.

## Addresses

- `FILE#name` for a function, class, type, constant or module-level variable.
- `FILE#Outer.inner` for a method or a nested definition: `src/api/limits.py#RateLimiter.allow`, `h.go#Handler.Serve`, `lib.rs#Sq.area`.
- JavaScript assignments keep their written target: `lib/view.js#View.prototype.lookup`, `app.js#app.init`.
- Terraform blocks use their Terraform address: `main.tf#aws_s3_bucket.logs`, `main.tf#var.region`, `main.tf#module.vpc`, `main.tf#output.bucket`.
- `FILE#L12` or `FILE#L12-L20` for lines, in any text file.

`map` and `find` print addresses relative to the PATH you gave. A `find` over `src` prints `pkg/mod.py#name`, so the address to slice, and the path to cite, is `src/pkg/mod.py#name`.

## Reading the output

- `slice` numbers every line. Cite those numbers. `find` gives a line number without its text, so before citing a reference, slice that line (`FILE#L88`) or run `rg -n -F "text" FILE`.
- A Python span starts at the `def` or `class` line, after any decorators. A TypeScript class span starts at its first decorator.
- A `slice` shows up to 100 lines. A longer definition comes back as an outline: the signature, the docstring, one line per child with its span and address, and a last line `body: FILE#Lstart-Lend`. Slice a child, or a part of that range.
- When several definitions share a name, `find` lists them all and `slice` prints each one under `N definitions match`, labelled with its parent (`in Class` or `at the top level`), its span and, for a Rust method, `(impl Trait)`.
- A file with a syntax error: the tree-sitter languages keep what parsed and add a note; Python returns no symbols and a note, so use `rg -n` and Read there.
- `find` matches references by name or by full address. A call through an alias, a re-export, `getattr` or a string is not listed, so "nothing else uses it" is an inference unless the name is unique.
- In Go, a use of a type (a parameter, field, composite literal, conversion and so on) is listed by `find` as a reference to it, and the type's own declaration is not. The alias and re-export caveat above is the only exception.

## Recipes for common asks

| Ask | Calls |
| --- | --- |
| Where is X defined? | `find X SCOPE`, then `slice` the address for the line to cite |
| Who calls or uses X? | `find X SCOPE`; slice each reference line you cite (`FILE#L88`) |
| What is in this package or module? | `map DIR`, then `map FILE` for the file that matters |
| What does function or method M do? | `slice FILE#M` or `slice FILE#Class.M`; if it comes back as an outline, slice a child or part of the `body:` range |
| Which definition holds line N? | `map FILE` and read the ranges, then `slice` that address |
| Where else is a name like X defined? | `find X .` lists every definition, with its kind and file |
| What implements Rust trait T? | `find T SCOPE`: impl headers and trait bounds are references; slice each |
| Where is a Terraform value used? | `find var.region SCOPE` or `find aws_s3_bucket.logs SCOPE`, with the full address |
| What changed in a definition over time? | slice it for its span, then `git log -L START,END:FILE` if your tools allow git |

Budget habit: `map` and `find` at 600, `slice` of a definition at 1000 to 1500, `slice` of lines at 300. Most questions need two or three calls.

## Refusals

Read a refusal by its markers, because the wording around them changes. A refusal is plain text on the launcher's output, not a crash.

- A closing `Next step: ...` is an instruction. Do what it says. It follows a `find` with no match, a `slice` of an unknown name with no similar name, a `slice` of a path that is not a file, a `slice` of a line past the end and a `slice` of a path outside the root.
- `FILE cannot be sliced: REASON` means the launcher will not read that file. Act on the reason. No symbol backend for the suffix: slice lines, such as `FILE#L1-L20`, or use `rg -n`. Over 1 MiB or not UTF-8: use `rg -n NAME FILE` to find the lines. Binary: skip the file. It cannot be read: skip the file and say so in your report.
- `nearest names: ...` lists names similar to the one you asked for. Slice one of them.
- `address 'ADDRESS' is not valid: REASON` lists the valid forms. The reason changes with the fault, for example `there is no # between file and target`: rewrite the address in one of the Addresses forms.
- At a small budget the launcher shortens paths and names with `...` and may drop the `Next step:`. A path under the root is the fix for an outside-root refusal.
