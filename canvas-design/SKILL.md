---
name: canvas-design
description: Create finished posters, promotional graphics and static artwork in PNG or PDF. Combine readable requested copy with strong visual design for company, product, event and informational posters; preserve explicitly requested wordless or abstract-art directions. Create original work, not copies of existing artists.
license: Complete terms in LICENSE.txt
---

# Canvas design

Deliver the requested finished poster, not an image-only background or a design essay. Preserve the exact subject/name, essential copy, language, dimensions and count supplied by the user. Default to one final PNG when no format is specified. Use a clear visual hierarchy, generous margins, coherent colors and readable typography; choose a design appropriate to the brief, not one fixed visual style.

## Select a supported production route first

**Text-bearing poster:** discover and activate the authorized isolated drawing executor. Current ExoHarness provides `sandbox_run` and task workspace tools. It does not require a `skill-workspace` MCP.

In the current native sandbox, external MCP image links are **not** owned, persisted sandbox artifact IDs. `workspace_import` cannot ingest those links or a generator job ID. Unless another available tool explicitly supports that transfer, create the complete poster using Pillow/drawing and CJK typography in the sandbox. Do not generate an external background and then attempt an unsupported import or a network download. A separate image model is optional, not a prerequisite for an illustrated poster.

When authorized transfer is actually available, image generation may supply material for composition. Confirm the live transfer schema before generating material. Reuse successful imagery for layout repairs. A background-only `no text` prompt is appropriate only when a supported subsequent composition step will add the required lettering.

**Explicitly wordless standalone image/art:** an authorized image generator may directly produce the final requested image. Do not add promotional text to intentionally wordless art. Preserve a requested photographic direction; do not claim a drawn illustration is a photograph.

## Isolated drawing workflow

1. Activate the actual sandbox tool names returned by discovery; `activate_tools.names` replaces the loaded set. Read live schemas, not guessed legacy interfaces.
2. For a new poster, one `sandbox_run` can create and run `files` with `runtime: "python"`, a relative `entrypoint` and `output_files: ["poster.png"]`. Do not supply `workspace_id` in this new-source mode.
3. If a font/environment check already created a workspace, that workspace contains only the check script. Save the actual poster script with `workspace_edit` at the returned ID/revision, then run the saved entrypoint with `workspace_id` and `expected_revision`, **without files**. A script mentioned in a plan is not a saved file.
4. Scripts write inside `/workspace`. Tool entrypoints and output paths are relative, e.g. `poster.py` and `poster.png`. Never use host execution, install dependencies during the run, fetch arbitrary URLs, or send image bytes/Base64 to the model.
5. Use exactly the same relative filename in the script's final save and `output_files`; do not rename only the tool argument. Publish only the complete requested poster. Checks use `output_files: []`; workspace files remain saved. If execution succeeded but output selection failed, select the actual filename from the returned workspace files and call `workspace_publish` at the returned revision; do not rerun the successful script. After an unchanged final file has been published, do not run or publish it again. If checks are separate, use `workspace_publish` for final delivery without rerunning successful code.

This instruction-only Skill need not be bound as an executable package. Bind its exact authorized `skill_id` only when using bundled assets at read-only `/skill`; fonts are in `canvas-fonts/`. Inspect only relevant resources. For Chinese use a font with CJK coverage; Latin fonts may render empty boxes. Check availability and glyph support before drawing required wording.

## Content and working-set checks

- Keep the real subject/title readable in the image itself. Chat text, filenames and metadata do not substitute for lettering. Draft concise creative copy when needed, but do not invent dates, prices, contacts, official agencies, account handles, awards, logos or product claims. A company name alone is not evidence of its services or qualifications.
- Respect supplied sizes. For an unspecified digital poster, around 1024×1536 is sufficient; draw at output size without default 2×/4× supersampling. Incrementally composite and release layers, use small local masks for soft effects, and avoid retaining many full-canvas RGBA/float arrays. Work within the executor's memory budget; do not silently shrink an explicitly requested size.
- Check output dimensions/format, essential wording, CJK glyphs, contrast, line breaks, margins and clipping. Inspect the composited file when a viewing tool is available; otherwise use concrete rendering checks and do not claim visual inspection.
- On failure keep saved files and successful results, fix only the failing source/layout step. Never call a background a finished poster. If a required capability is genuinely missing, describe that missing step clearly.

Return the final tool-provided file with a brief description and real limitations. Do not publish backgrounds, crops, QA images, extra variants or unrelated documents unless requested.
