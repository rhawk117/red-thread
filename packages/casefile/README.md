# red-thread-casefile

The case file behind the red-thread plugin: an append-only ledger of investigation entries under `.red-thread/<case-id>/`, the board rendered from it and the citation check. Its one dependency is msgspec. The HTML page's skeleton, styles and script are in `assets/`, and the package reads them from the source tree.

The plugin's skills and agents call it through `scripts/casefile.sh`. The commands are `init`, `add`, `render`, `check`, `export` and `page`; `docs/design.md` section 4 describes the format and the rules.
