# red-thread-core

The shared base of the red-thread packages. It holds what every package needs to write a page or keep a record, and nothing that knows about a case or a plan.

- **The document tree** (`documents.py`): inline text, code and links; the `Block` protocol; the blocks every page uses (a paragraph, a list of points, a mermaid chart, a code listing); and the section, fact and document that hold them. A block renders itself to HTML and to Markdown, so a package adds its own blocks without changing this one: `red-thread-casefile` adds the entry list, and the plan page adds the ticket list.
- **The writers** (`writers/`): HTML through t-strings, with every value escaped by one function, Markdown, and the page, which takes the filter chips its caller computes.
- **The page assets** (`src/red_thread_core/assets/`): the skeleton, the styles, the Tailwind theme and the script.
- **Packaged files** (`packaged.py`): `read_asset_text(package, name)` reads a file under a package's own `assets/` directory through `importlib.resources`, and `load_asset(package, name, shape)` decodes a YAML file there into a frozen type with `msgspec.yaml`. Every package keeps its assets this way, so a built wheel carries them.
- **The primitives**: secret redaction (`redaction.py`), the source tree, clock and page store protocols with their real implementations (`store.py`), the mermaid label rules (`charts.py`) and `squeeze` (`util.py`).

It depends on msgspec and PyYAML, for `load_asset`. Each package that uses it declares it as a workspace dependency, and the launchers in `bin/` install it editable beside that package.
