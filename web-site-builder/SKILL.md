---
name: web-site-builder
description: "Create or improve websites, landing pages and browser-previewable HTML. 用于生成网站、宣传网页、落地页、可预览 HTML，以及在已有网页上继续修改。Use for an actual web deliverable, not general programming explanations, slides, posters or video."
---

# Website delivery

Deliver a useful, attractive website and an actual browser-preview link. Read
this Skill once. It is instruction-only: it does not require a package runtime
binding. Use authorized execution tools and their live schemas; this Skill
does not grant permissions or imply that a particular MCP is installed.

## Execution and delivery

1. Discover and activate the available workspace, execution and publication
   tools. The native interface uses `workspace_create`, `workspace_edit`,
   `workspace_read`, `sandbox_run` and `workspace_publish`. Another provider
   may expose different names or fields: follow its actual schema, not aliases.
   Do not send old `delivery`, `appends`, `inspection_jobs` or similar fields
   unless the live schema declares them. If file writing or publication is
   unavailable, explain that specific limitation without claiming delivery.
2. Create one workspace, or reuse the workspace for an existing page. Save the
   page using native JSON arguments and returned workspace ID/revision. For a
   self-contained promotional page, prefer one write of the complete
   `index.html`, including its HTML, CSS and necessary JavaScript. There is no
   fixed character cap or mandatory staged saving. Do not deliberately leave
   sections unfinished for later calls. Split files only when the requested
   project genuinely needs it, or when a demonstrated output constraint
   prevents a complete write. Keep notes short and factual.
3. Do not read the code you just wrote from start to end
   again to reconstruct context, enumerate styles or prove it is complete.
   For a reported defect, read only the affected definition/range and patch
   that exact location using the current revision. File size is bytes; read
   offsets may be characters or lines—follow the schema and returned cursor.
   End-of-file is not a reason to restart reading at offset zero.
4. A static HTML page can be published immediately after a successful complete
   write; sandbox execution is not a prerequisite for publication. If a check
   is actually needed, check saved files in the same sandbox, not by sending
   their full contents back to the model. Use one focused check where useful;
   return a short defect list, not source dumps. A minimal HTML preflight is in
   [references/custom-source-check.md](references/custom-source-check.md), only
   if needed. Reuse the check and repair only demonstrated defects. If an
   authorized browser inspector is available, check desktop/mobile rendering,
   console errors and relevant clicks. If unavailable, do not repeatedly search,
   install a browser, or claim screenshot/interaction coverage. State the limit.
5. Publish the final files with the actual publication tool and current revision.
   A write receipt, check result or checkpoint is not a published website.
   Use returned `preview_url` for “打开网页” and `download_url` for “下载 HTML”;
   do not invent URLs or output internal checkpoint JSON. Deliver final files,
   not private QA scripts. Stop after successful delivery; do not rebuild it.

For the native interface, a focused read includes the file path, not just a
query. Without `path`, `workspace_read` returns workspace metadata, not source:
`{"workspace_id":"returned-id","path":"index.html","query":"</main>","limit":200}`.
Only read an anchor when an actual follow-up edit is needed, not as a default
step after authoring. Use the exact snippet and file SHA from that result.
A native edit has this shape:
`{"workspace_id":"returned-id","expected_revision":2,"patches":[{"path":"index.html","sha256":"returned-sha","before":"exact saved snippet","after":"replacement"}],"notes":"short progress"}`.
`notes` belongs to the edit's root, **not** an item in `patches`. IDs, revisions,
SHA and snippets here are placeholders: always substitute real returned values.
When the activated tool uses another schema, follow that schema instead.

Native `sandbox_run` runs a saved script file, not an arbitrary shell command:
first save `check.py` or `check.sh` with `workspace_edit`, then supply the current
workspace ID/revision, `runtime:"python"` with `entrypoint:"check.py"` (or
`runtime:"shell"` with `entrypoint:"check.sh"`) and `output_files:[]` for checks.
`entrypoint:"sh"`/`"bash"` is not a saved script. With `workspace_id`, omit
`files` and `skill_id`: edit files separately and do not rebind the package.
Ordinary authored HTML/check scripts need no package binding; create that task
with `{}`. Only bind a Skill when actually using its packaged assets/scripts.

## Design and content

Respect the user's subject, style, stack and requested languages. Do not add a
second language unless requested. Unless a stack is specified, use offline,
self-contained HTML/CSS/JS; no remote fonts/scripts, backend requests or
parent-page access. Label demonstration forms and avoid invented contacts,
certifications, statistics or testimonials.

Choose a clear audience, visual concept, palette and typography before writing.
The first screen should show who the site represents, what it offers and the
visitor's next action. Use concrete subject-specific copy, varied section rhythm,
readable hierarchy and responsive layouts rather than interchangeable slogans
and repetitive cards. Match component selectors and markup; new components need
their styles. Bound icons/images deliberately, wrap mobile navigation and keep
controls reachable. Internal links must target real, unique IDs. Do not hide
body overflow to conceal defects. Support keyboard use and reduced motion.

Prefer supplied imagery. An available authorized image tool may provide a
purposeful hero image, but images are optional and must not block delivery.
Follow the actual artifact-import and preview rules. The native preview accepts
embedded data/blob images, not remote/relative image links. If embedding media,
do it inside the sandbox and keep Base64 out of model messages. Never download
through an unapproved network path or invent an image provider.

## Multiple languages and follow-up edits

For requested languages, use paired translations in one layout. Provide working
click listeners, visible default content, updated document language and selected
state. A label or planned handler is not implementation. A simple approach uses
`data-setlang`, `data-copylang` and inactive `hidden` translations with
`[hidden]{display:none!important}`; custom working approaches are equally valid.
Save the handler together with the controls and test it when browser execution
is available. Do not require a browser package the runtime does not have.

For follow-up edits, reuse the existing source and workspace, inspect the target
only and preserve unrelated bytes. Refresh state after a revision conflict.
Never create a replacement workspace to bypass a permission/runtime rejection.
Report only actual execution and publication results, with any unverified
behavior stated briefly.
