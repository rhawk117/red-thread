# red-thread-core

The shared base of the red-thread packages. It holds what every package needs to write a page or keep a record, and nothing that knows about a case or a plan.

- **The document tree** (`documents.py`): inline text, code and links; the `Block` protocol; the blocks every page uses (a paragraph, a list of points, a mermaid chart, a code listing); and the section, fact and document that hold them. A block renders itself to HTML and to Markdown, so a package adds its own blocks without changing this one: `red-thread-casefile` adds the entry list, and the plan page adds the ticket list.
- **The writers** (`writers/`): HTML through t-strings, with every value escaped by one function, Markdown, and the page, which takes the filter chips its caller computes.
- **The page assets** (`assets/`): the skeleton, the styles, the Tailwind theme and the script. `read_package_asset` reads another package's own assets the same way.
- **The primitives**: secret redaction (`redaction.py`), the source tree, clock and page store protocols with their real implementations (`store.py`), the mermaid label rules (`charts.py`) and `squeeze` (`util.py`).

It has no dependencies outside the standard library. Each package that uses it declares it as a workspace dependency, and the launchers in `bin/` install it editable beside that package.
