# ExoHarness Skills

English | [简体中文](README.zh-CN.md)

A collection of reusable agent Skills: task instructions, reference material, scripts and design resources. Skills define how to approach a task; executable capabilities come from the host's authorized tools, model APIs, MCP services and isolated runtimes.

Use this collection with [ExoHarness](https://github.com/jason571/Exoharness) or another agent that supports the package's Skill format and required tools. The examples cover multiple domains, but the collection is extensible: importing a new Skill does not require adding its business rules to the agent framework.

## Available packages

| Area | Skills | What they contribute |
| --- | --- | --- |
| Web and visual design | [web-site-builder](web-site-builder/), [frontend-design](frontend-design/), [canvas-design](canvas-design/), [theme-factory](theme-factory/) | Website delivery, interface design, visual compositions, typography and themes |
| Video direction and music videos | [minimax-h3-director](minimax-h3-director/), [music-video-from-audio](music-video-from-audio/) | Narrative direction, H3 prompts/storyboards, reference-image roles and multi-clip MV planning |
| Regional promotion | [yongjia-product-promo](yongjia-product-promo/) | Narrated promotional videos for products, culture and tourism |
| Music production | [yue2-song-production](yue2-song-production/) | Sung songs through an authorized YuE2 service; optional cover art |
| Teaching | [elementary-lesson-video](elementary-lesson-video/) | Age-appropriate lesson plans and synchronized narrated animations |
| Space entertainment | [clhh-space-entertainment](clhh-space-entertainment/) | Domain context for entertainment venues and spatial workflows |
| Extension authoring | [skill-creator](skill-creator/), [mcp-builder](mcp-builder/), [find-skills](find-skills/) | Authoring Skills, building MCP services and finding existing packages |
| Search and extraction | [tavily-search](tavily-search/), [tavily-dynamic-search](tavily-dynamic-search/), [tavily-extract](tavily-extract/) | Query planning, focused web searches and content extraction |
| Site exploration and research | [tavily-crawl](tavily-crawl/), [tavily-map](tavily-map/), [tavily-research](tavily-research/) | Crawl/map operations and research workflows |
| Tavily integration | [tavily-best-practices](tavily-best-practices/), [tavily-cli](tavily-cli/) | Integration guidance and CLI usage |

There are 21 packages in this initial publication. A Skill listing is not a promise that its dependent service is deployed on your machine.

## Install and import

```bash
git clone git@github.com:jason571/skills.git
```

For ExoHarness:

1. In the capability import page, select the **individual package directory** containing `SKILL.md`, for example `skills/web-site-builder`. Keep its references, scripts, fonts and other resources alongside that file.
2. Register and enable the Skill, then grant it to the intended assistant.
3. Register and authorize the execution dependencies declared by that package: relevant MCP connections, TTS/image/video models or sandbox runtimes.
4. If the package contains executable scripts, prepare its approved isolated runtime before using them. Importing instructions does not itself execute code or install dependencies.
5. Test one representative task and inspect the trace and final artifact.

For another agent, follow its Skill installation mechanism and check tool compatibility. Copying a Skill into a directory does not automatically provide the APIs it references.

## Package structure

```text
package-name/
  SKILL.md       # Required: name/description and task instructions
  references/    # Optional: documentation loaded when needed
  scripts/       # Optional: executable helpers
  assets/        # Optional: fonts, images, templates and other resources
  LICENSE*       # License supplied by the package's author
```

Directory names vary by package. Preserve package-relative paths; importing only `SKILL.md` can lose required resources. The host should discover relevant Skills, read only the instructions needed for the current task, and load executable tool schemas on demand.

## Execution dependencies

- Website/code tasks use the host's workspace and isolated coding tools. This collection does not require the legacy `skill-workspace` MCP when the host already provides equivalent native tools.
- Teaching animation requires a lesson renderer and configured TTS capability; registering the teaching Skill alone does not synthesize speech or render Manim.
- Song, image and video tasks require corresponding authorized model services. Multi-clip workflows also require media assembly; service parameters come from live tool schemas.
- Tavily packages require a matching Tavily integration and its API credential. CLI examples require the CLI and runtime as well. Search/research tools have different latency and billing characteristics.
- Python/Node dependencies used by scripts belong in approved isolated environments, not the user's host shell. Keep generated files in the task workspace and publish the final artifacts through the host.

The companion [MCP repository](https://github.com/jason571/mcp) contains several of these services. Model weights, private credentials, real runtime environments and generated outputs are not included here.

## Licensing and distribution

Each package retains its own license and attribution; this repository does not replace them with a collection-wide license. See [THIRD_PARTY.md](THIRD_PARTY.md), including licenses for bundled design fonts and upstream resources.

The local `docx`, `pptx`, `pdf` and `xlsx` packages are **not distributed in this repository** because their included upstream license restricts redistribution. They remain separate from this publication; obtain any such packages directly from their publisher under the applicable terms. This exclusion does not remove the framework's ability to run independently licensed document-generation Skills.

## Related projects

- [ExoHarness](https://github.com/jason571/Exoharness): agent framework, permissions, tracing, sandbox and artifact delivery
- [MCP services](https://github.com/jason571/mcp): executable service implementations and connection examples
