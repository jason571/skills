---
name: yue2-song-production
description: 生成带演唱和伴奏的原创歌曲、宣传歌曲或音乐，并交付 MP3。Create an original sung song with YuE2 from a theme, style or lyrics. Use for actual song recordings, not lyrics-only requests or spoken TTS. An authorized image generator may add a matching cover after the song; cover art is optional and must never block it.
---

# Original songs with optional cover art

The deliverable is a composed recording with vocals and accompaniment. Text-to-speech or a reading of the lyrics is not a song and must never be presented as the requested recording.

## Optional capabilities

- `z-image` — generate a cover after the song is complete, if this image MCP is authorized and ready. Its absence must not block music generation.

## Decide what to make

- Default to **one song**. Make two versions only when the user explicitly requests two songs, alternatives or different arrangements. Two versions need meaningfully different musical directions; changing only the filename, codec or cover does not create a second song.
- Respect the requested singer, language, mood, genre and subject. Write original, singable lyrics with section labels, or use user-supplied lyrics as directed. If the optional lyrics service is unavailable, write the lyrics directly and continue with music generation; do not substitute TTS.
- For two versions, plan distinct arrangements before submitting either call. Supply each version's own concrete `style` and a different supported seed when useful. Call `yue2.generate_music` once per planned version. A retry or a `get_music_result` call is not a new version.

## Generate and deliver

1. Discover and activate the authorized YuE2 music tools using the actual catalog names and live schemas. The assistant's persona and the currently loaded tool table are not the full inventory. Query the catalog before claiming music generation is unavailable. If no authorized music tool is actually available, explain that boundary; do not make a spoken MP3 instead.
2. Supply the complete lyrics and musical direction to `yue2.generate_music`. Keep the call open for progress. If using the asynchronous submit interface, reuse the returned job ID and wait for its completion before retrieving the result. If transport disconnects after a job ID is known, query `get_music_job` and `get_music_result` instead of submitting a duplicate generation.
3. Treat MP3 and FLAC from one YuE2 job as **two encodings of the same song**, never two songs. Present one playable MP3 result per song by default. Request `get_music_result(audio_format="flac")` only when the user asks for the original-quality file. Do not invent public URLs or expose localhost links.
4. If an image-generation MCP such as `z-image` is authorized and ready, and the user has not declined artwork, optionally create one square cover per finished song. Use a visually distinct concept for each genuinely different version. Call the image generator after the music result so artwork does not compete with music generation for GPU memory. A failed or unavailable cover must not delay or invalidate the song.
5. Report the actual number of completed songs and durations from tool results. Show the lyrics and final audio artifact cards; if cover art succeeded, show its image card. Do not label a preview, a FLAC master, or a retry as an additional song. Do not stop at lyrics or a suggestion to use a third-party site when an authorized music executor is available.
