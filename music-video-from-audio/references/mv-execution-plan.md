# Persisted MV plan and recovery

Use the active media-workflow MCP tool schemas and returned checkpoint as the
execution contract. Do not construct a second handoff plan in conversation.

## Ordinary authoring

1. Select one global style for the work. Reuse it throughout planning and recovery.
2. `create_music_video_plan` measures the immutable audio and stores the segment
   timeline. Set resolution/aspect ratio once here or use the defaults. No audio
   energy analysis, transcription, or repeated duration probe is required for
   title-informed work.
3. Save the song-wide overview, then write all sections in the advertised window
   together. Supply creative fields only. The service owns segment durations,
   shot timestamps, silent output and reference-frame handoffs.
4. For ordinary multi-shot segments, **write at least four shots; accept three**.
   Do not rewrite a complete three-shot section to add a fourth. One/two-shot
   writes retain their existing fields and request only missing slots up to three.
   Explicit single-shot requests use the separate one-shot mode; never select it
   just to evade the multi-shot requirement.
5. After validation, call the declared `render_validated_music_video` checkpoint.
   The service performs serial generation, last-frame extraction, next first-frame
   delivery and assembly with the original audio. Do not repeat those operations
   as separate model-directed calls.

## Recovery

- Keep the exact draft ID/digest, required tool/arguments and returned error paths.
  Complete storyboards and execution evidence remain in MCP Store and the journal.
- On a rejected field, patch only that field or missing shot at its saved index.
  Other accepted fields and queued later sections remain saved.
- For a previously stored full-plan draft, follow its declared patch tool and
  exact JSON Pointer targets. Do not replace it with a new draft or copy its full
  contents into every model request.
- Preserve immutable attachment references, successful job IDs and artifacts.
  Do not invent URLs, serialize Base64, or repeat completed generation calls.
- Trust completion only when the final ToolResult contains the assembled artifact.
  MCP progress is displayed directly, without model polling or progress narration.

## Evidence boundaries

Song title/artist can support a title-informed visual interpretation, not verified
lyrics or measured lyric timing. Every song uses people and places from its own
language and culture for the whole MV unless the user explicitly asks otherwise.
Original audio is preserved. Timing and segment
counts come from the measured duration; pixel dimensions and download URLs come
from completed service results, not guesses in the prompt.
