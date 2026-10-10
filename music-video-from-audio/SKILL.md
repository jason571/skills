---
name: music-video-from-audio
description: Create a complete MV of at most 6 minutes from uploaded audio and a known song title; reject longer inputs before planning or generation. If the title is missing or unknown, ask for it first. People and places must match that song's language and culture. Select one global visual style and use media-workflow for continuous clips and final assembly with the original audio.
---

# Music video from audio

Produce one coherent MV with the uploaded audio as its only music source. The model owns creative interpretation; media-workflow owns timing, saved sections, generation, continuity frames and final assembly.

## Host interface and uploaded files

Use the host's actual discovery and activation tool schemas. On the native host, use `search_capabilities`, `read_skill` with the registered Skill ID and package-relative `path`, and `activate_tools` with the exact returned `names`. Older host-specific names elsewhere in this document are not executable tool names. Read instructions once, and load only the needed executable schemas.

Uploaded files are supplied as saved attachment metadata: name, media type, SHA-256 and a signed immutable `url`. Pass the audio `url` to `create_music_video_plan.audio_url`; never pass Base64, a host path or a fabricated link. For a still, use `first_frame_url` or `reference_image_url` according to its actual user-requested role and the live schema. Native `artifact-...` IDs are host handles, not media-workflow `att_...` IDs: never copy or rename them into an `*_attachment_id` field. Legacy `att_...` fields apply only when a real legacy attachment handle was returned. A saved URL does not prove visual understanding; inspect only with an authorized vision capability, or ask for a short image description when required.

Rendering and final assembly belong to the declared media-workflow checkpoint. Keep the original song as the final audio track, retain already completed clips, and deliver the final assembled MP4 rather than the intermediate clips.

## Duration limit

An MV may be at most 6 minutes (360 seconds). If the user explicitly requests a longer MV, stop before style selection, planning, TTS or video generation and tell them: “MV 最长支持 6 分钟，请缩短音频或时长后重试。” For uploaded audio whose exact duration is not yet known, `create_music_video_plan` measures it once and rejects anything over 360 seconds before saving a plan or submitting a video job. Do not crop, accelerate or split an over-limit song unless the user first asks for that different deliverable.

## Confirm the song before starting

A title is usable only when it is clearly a song name: already given in this chat, or an uploaded filename whose stem looks like a real title (for example `恋人.wav` → 恋人, `《恋人》.wav` → 恋人). WAV/MP3/M4A are containers, not titles.

Ask one short question such as “这首歌叫什么名字？” and **wait** when any of these is true:

- the user says the title is unknown, unsure, or “不知道”
- there is no title in the chat and no filename
- the filename is not a trustworthy title: generic recorder/export names (`audio`, `recording`, `track`, `untitled`, `new recording`, `voice`, `weixin`, `录音`, `未命名`), dates/times only, device/camera IDs, hashes, or other strings that are not a song name

Do not guess a title from lyrics, style, or the image. Do not select a style, create a plan or start generation while waiting. Keep the existing audio (and still) references; after the user provides the title, continue with those uploads. Ask for the artist only if needed to distinguish songs with the same title. For an original song, use the title the user gives it.

## Every song matches its own culture

This applies to every song, not to one title. After the title is confirmed, decide the song's language and culture from the title, supplied lyrics, the user's statement, or title-informed knowledge. A romanized filename does not change a song whose title or lyrics are in another language. Han characters, or knowledge that the song is sung in Chinese, mean a Chinese song.

People, faces, wardrobe, streets, interiors, props and atmosphere must belong to that culture for the whole MV. A Chinese song uses Chinese people and places in China. A song from another language uses that culture's people and places. Do not default to Western faces or a foreign city when the song is not from that culture, and do not give a non-Chinese song a Chinese cast. Genre words such as cinematic, film or cyberpunk do not cancel this; apply them inside the song's own culture.

Use `generate-video-prompts` only when the chosen record shows people and places of this song's culture. Otherwise do not load it. Compose one culture-matched global style and save provenance `{"planning_mode":"user-specified","model_profile":"not-selected"}` with no `pack_id` or `document_id`.

Creative fields stay concise English (`output_language: "en"`). English wording without an explicit culture makes the video model draw Western faces, so name the culture in:

- `subject_identity`: that culture's people and features, and not another culture's faces.
- `wardrobe_or_materials` and places: clothing and locations from that culture.
- Every segment `negative_prompt`: faces, crowds and street defaults from a different culture.
- Shots that show people keep the same cultural identity. Do not switch cultures in a later segment.

The only exception is an explicit user request for a different culture, or a still they explicitly asked to keep as that exact person. A style-only reference must not import a face or city from another culture; keep only palette, light and texture that still fit the song.

## Required capabilities

- When the user has not specified a usable visual style, `generate-video-prompts` can contribute one global style only if its people and places match the song's culture. A detailed user style takes precedence and needs no style-library lookup. The culture match above still applies.
- `media-workflow` provides draft creation, complete overview/segment writing, focused field patching and `render_validated_music_video`.

If a required capability is unavailable, report that before generation. Do not bypass this workflow with direct video-generator calls.

## Hard stops — do not guess

- Do not invent Skill paths. This package has no `references/import-map.json`. After `resource_not_found`, use only `parent.entries`; do not retry spellings, and do not call this Skill's read tool for another package's files.
- Do not invent a song title. If the filename is untrustworthy or the title is unknown, ask and wait. Do not skip the job because a file in this package is missing.
- Do not invent clip length. Use `clip_duration_seconds` returned by `create_music_video_plan`. Do not assume 15s or 30s before that return.
- Do not invent tool names. Copy exact names from the loader catalog (`schema_loaded`). Do not query to discover names, and do not call `skill.music-video-from-audio.read` except for this Skill's `SKILL.md` once.
- Do not invent image URLs or assign an uploaded still a role the user did not request. For an MV request that says only "参考图片" or "参考图片风格", inspect the image once and use its visual style in the plan; do not pass the still to every generation call. Use `reference_image_attachment_id` only when the user explicitly asks for persistent image conditioning (such as keeping a depicted person or product recognizable throughout), and `first_frame_attachment_id` only for an explicitly requested opening frame. Both IDs must come from `<user_image_attachment>`.
- If a media-workflow tool returns isError, quote that error text. Do not invent causes (expired attachment, skip the still, assume 15s or 30s) and do not bypass `create_music_video_plan`.

## Plan and save

1. Read this Skill once. Do **not** call `skill.music-video-from-audio.read` for `references/import-map.json`. This package's `references/` only has `mv-execution-plan.md`; do not read it. If the user supplied a visual reference, inspect its actual visible content **before style selection** and separate stable subject/material/style cues from transient pose, camera framing and location; record the latter as optional story context unless the user explicitly requires them to persist. An attachment ID or URL is not a visual description. Never infer image contents from the song title or filename; if no authorized vision capability can inspect it, ask for a description and wait rather than inventing one. Inspect the same image once; reuse stable identity/style cues and user-required facts, not its pose or background as a reset frame. Match the global style to the song's culture as required above, and skip `generate-video-prompts` when no library record fits that culture. If the user gave a concrete style (palette, environment, visual treatment, subject, or camera direction sufficient to compose the MV), use that style directly for the ENTIRE MV; do not query or read `generate-video-prompts` for a replacement. If a style is already saved in this work's overview, reuse it. Only when the style remains unspecified or too vague to compose, load `generate-video-prompts` from the catalog and call that Skill's read tool once with `{"resource":"references/import-map.json"}`, and select one actual record whose people and places match this song's culture. Do not load its root instructions or choose another style for each segment. Reuse any successful existing selection; do not perform both paths. If a needed lookup fails, report the error and stop; do not retry missing files in this package.
2. Before `create_music_video_plan`, compare the proposed style and subject against observed image facts and the user's actual request. For a style-only reference, describe transferable palette, lighting, texture and camera language in the brief; treat the depicted pose, station, background and props as optional story material, not required continuity anchors. Do not pass `reference_image_attachment_id` or `first_frame_attachment_id` for style-only use: this prevents the original scene from conditioning every clip. Only explicit persistent subject/product identity calls for `reference_image_attachment_id` when supported by the live generator; if unsupported, report that before video submission rather than substituting a first frame. Pass `first_frame_attachment_id` only when the user explicitly assigns the still as the opening frame. User-specified style and story take precedence over a style-library match. With no reference image, create the narrative from the user's text and song context. Call `create_music_video_plan` with the immutable audio URL and brief (include either the user-specified style summary or the one selected style ID and summary). Do not pass chat `/v1/run-artifacts/` URLs. Set `output_language: "en"` and write creative fields in concise English; preserve the original song title, supplied lyrics and original audio. Set resolution/aspect ratio only here if the user specifies them; otherwise keep the MCP defaults. Leave `planning_batch_size` at its default to write the entire song's creative sections together; only an explicit smaller output budget calls for a smaller window. Do not reduce the batch simply because the song has many segments. This call reads the live video-generator `duration_seconds.default` and returns `clip_duration_seconds` plus the exact segment windows; do not assume 15s or 30s. Remainders at most 40% of that default merge into the last clip; a larger remainder is its own clip. Leave the suggested shot count at the service default unless requested. No separate `probe_media`, manual duration calculations, or audio-energy analysis.
3. Follow the returned next tool. Submit `write_music_video_plan_overview` with a song-wide narrative arc, the single style summary, continuity anchors and truthful provenance. Save the user's style or the selected style ID/revision, palette, materials, lighting, camera language and motif in the compact style summary and corresponding anchors. Outline a distinct story beat for each segment before writing individual scenes; reserve arrival/resolution for the final section. Include every user-required anchor and stable identity/style cue; describe location-specific geometry for a deliberate revisit only, not as a compulsory scene for every segment. For a user-specified style, provenance is `{"planning_mode":"user-specified","model_profile":"not-selected"}` with no `pack_id` or `document_id`. For a real style-index read, use `planning_mode: "read-only-resources"`, the actual selected `pack_id`, `document_id: "references/import-map.json"`, and `model_profile: "not-selected"`. If an executable query actually returned the selection, record that real source instead. Never claim a query script or template document was loaded without evidence.
4. Write the returned current window in one call. Its `input_shape_example` shows the public argument structure; replace the placeholders. For ordinary multi-shot MV segments, compose at least four shots per segment. Acceptance is slightly looser: three complete shots may pass without a retry just to reach four; one or two require supplementing only that segment, not regenerating the whole plan. Do not switch to single-shot mode to evade this requirement; that mode is only for an explicit continuous-shot request. `sections` and `storyboard` are arrays, each section has a `content` object. The window's timing metadata is read-only, not an input template. A single-section full write uses consecutive shot indexes from zero; a later focused patch uses the saved indexes. The first segment needs an opening keyframe. Only when the user explicitly bound an opening frame must Shot 1 start from that exact image; a persistent reference image constrains its declared identity/style role but does not fix Shot 1's frame or require later returns to its original composition. Later openings are copied from preceding endings. Each section advances its own story beat within the one global style.
5. Optional shot weights express creative emphasis. Do not supply timestamps, durations, segment counts, resolution or audio settings inside segment content: the service derives them from its persisted skeleton. Each scene must advance the song-wide narrative, not repeat another segment with different adjectives.
6. Continue only from the latest returned draft ID/digest. Each accepted section advances the checkpoint. Do not resend the overview or earlier accepted segments. The service will return the rendering checkpoint when the entire plan is valid.

Keep fields concise: one concrete phrase or short sentence per shot field, no bilingual duplication
or repeated global wardrobe/style paragraphs. `visual_role` describes this segment,
not the whole MV. Different segments advance the story within the SAME selected
style. Do not reselect on a new segment, partial repair or resumed Run; only an
explicit user request to change the work's style permits a new selection.
The first shot starts from the opening frame's exact state; the
last shot ends at the declared ending frame's exact state. Do not say the subject
leaves a bridge while the ending frame still places them at its center. Plan silent
visuals without subtitles, titles, logos or credits. Do not invent measured music
events or exact lyric positions from a title-only interpretation.

## Whole-song composition checks

- In the overview's narrative arc, assign each advertised segment ID one short story beat. Develop those beats together before writing shots; reserve the final resolution for the final segment rather than repeating several endings.
- Before writing shots, track each segment's starting place, new event, changed emotional state and ending place. An ordinary reference image may keep a person or visual style recognizable, but it is not a recurring scene template. Do not return to its original pose, framing or location at each new segment; revisit a location only for a deliberate story beat that changes what happens there. Keep the one global style while the plot moves forward.
- For a style-only image, do not turn its photographed location into `setting_geometry`, a recurring motif, or the final destination merely because it appears in the photo. Revisit that location only if the user separately requested it. Check the whole arc for an unrequested return to the source composition before submitting the plan; keep the extracted style while later scenes follow the previous segment's actual ending frame.
- Write the adjacent boundary and action together: the next first shot begins with the previous ending's location, subject and pose. If the story moves to another place/time, show that transition during the segment; do not begin after an unexplained jump. Each ending_keyframe describes one static terminal frame, not camera movement or a montage.
- Use each shot field for its own information: framing/lens, visible action, camera motion, environment motion, light, and transition. Avoid two fields contradicting one another. The available shot duration must be plausible for the action. A place change is allowed only when that same shot shows a path the body can actually travel. Do not teleport someone into or out of a vehicle, across a gap, or off an edge; if the story needs that change, write the intermediate state in the shot.
- Check negative instructions against positive content. A no-text plan must not require readable signs, letters or credits; do not forbid the location or characters the story needs.
- For title-informed work, music_description is the intended emotional role, not an invented claim about instruments, beats or lyric timing. The original uploaded audio remains untouched.
- Before submitting, aim for at least four shots per ordinary segment and check the three-shot acceptance floor, usable first/last states and JSON container shapes once. Also check that `subject_identity`, places, wardrobe and every on-screen person stay in the song's culture, and that `negative_prompt` still rejects a different culture. Check that every place change is a path visible inside the shot that performs it. Do not rewrite a usable three-shot segment merely to add a fourth, or repeatedly polish the full plan. This is a quick check, not another complete rewrite or another Skill lookup.

## Small repairs, not full retries

Tool arguments must contain native containers: `sections` is an array of section objects, each `content` is an object, and `storyboard` is an array of shot objects. Do not stringify these fields or put escaped JSON inside a string. Use the live schema and returned `input_shape_example` for the complete fields.

Batch writes use array order: each section contains only `content`; omit `segment_id` and shot indexes. Explicit IDs and `shot_index` belong to single-section or focused patch calls, not batch writes. If a retained batch has extra addressing fields, remove only those fields through local argument repair; keep every creative field unchanged.

Distinguish a Host input rejection (`submitted: false`) from a service validation response. A Host rejection has not saved these sections to MCP. Use the available local failed-call inspection/repair tools on the retained source, inspect the reported error location rather than reading the entire string page by page, and repair only the incorrect fields/delimiters. Do not recreate the draft, regenerate unchanged storyboards, or claim the sections were saved. Only a successful service response advances the draft checkpoint.

A section response may contain validation errors while retaining all other fields and later sections from the same batch. Follow its declared `patch_*` tool and submit only those missing/incorrect fields. For one bad shot field, send that shot_index and the corrected field; do not resend its other shots or any other segment, including saved later sections. Complete `write_*` calls must include all required fields; partial `patch_*` calls are only for reported errors.

Keep the latest checkpoint and its current-section guidance. Do not reconstruct a complete plan from previous messages. If the same correction fails repeatedly or progress stops, report the saved checkpoint and error; do not restart from the audio or submit generation through another tool.

For an existing full-plan draft, follow its returned patch protocol instead of creating a replacement draft. Copy service-issued JSON Pointer paths exactly. Do not change a field absent from its repair targets.

## Evidence and semantics

Song title and artist are sufficient for a title-informed interpretation. Without supplied lyrics, use `song_context_basis: "title-informed-model-knowledge"`; do not claim transcription or verified lyrics. Use `user-lyrics` or `user-timed-lyrics` only when the user supplies that evidence.

The measured timeline does not establish where a particular lyric occurs. Do not invent word-level lyric alignment. The user may provide timed lyrics if exact alignment is required. No audio-energy analysis is needed for an ordinary MV.

## Execute once and finish

Call `render_validated_music_video` using the exact arguments in the final checkpoint. The service owns serial silent video generation, persisted job IDs, last-frame extraction and next first-frame delivery, concatenation, and muxing the original song. Keep the call open; MCP progress goes directly to Chat without model polling or repeated progress narration.

Do not repeat a successful generation or remove a required reference frame to bypass an error. If interrupted, resume with the same persisted workflow arguments rather than recreate completed clips.

Report completion only when the final ToolResult proves the ordered clips were assembled with the original audio and provides a playable Artifact plus duration, dimensions and SHA-256. Do not add redundant download prose when Chat already renders that Artifact.
