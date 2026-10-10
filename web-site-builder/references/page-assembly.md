# Optional assembly details

Use these only when the standard file-based manifest does not fit the project
or the helper reports a field problem. The assembler does not choose the design.

Manifest fields: title, language, description, css_file or css, parts,
languages, javascript_file or javascript. Only title/nonempty parts are required.
Each part has a unique id and file or html, never both. File and inline forms are
mutually exclusive. Prefer saved files for substantial content; inline forms are
useful for small pages, not embedding an entire website in page.json.

All paths are relative to the manifest's directory, without parent traversal.
Parts can contain header/nav, sections and footer in any intended order; there
is no fixed layout or section count. Document roots, main, styles and scripts are
assembled once. Each part must contain only inner HTML. Duplicate IDs, unresolved
anchors/ARIA, invalid roots or language mismatches reject assembly without changing
previous HTML. The report includes the affected part/field and missing-path inventory.

Bilingual languages must include the default language. Use type="button" on
data-setlang buttons, and paired data-copylang translated nodes. Inactive copies
start hidden. The generated handler supplies click behavior, document language,
ARIA selected state and a bounded click smoke test; custom interaction scripts
must not create a second language handler or override hidden-state semantics.

For a reported failure, correct only its saved manifest/source definition using
read_workspace(query=...) and edit_workspace, then run the existing build entrypoint
without code. Keep all unrelated fields, source and order. Create a missing source
part only if it genuinely was never saved. Do not inspect every file to reconstruct
the already returned inventory, or invent paths from planned names.
