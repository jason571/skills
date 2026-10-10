#!/usr/bin/env python3
"""Plan and assemble promotional clips inside an existing task sandbox.

Standard library plus ffmpeg/ffprobe. No network, model calls or installation.
Input paths are relative to the manifest directory. Nothing runs on import.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

from plan_json import load_plan_json

I2VA_PREFIX = ("For the target video, at 0.00 seconds into the target video, "
               "<Picture 1> (from [Shot 1]) is fully referenced.")
H3_LABELS = ("integrated_multimodal_description", "overall_soundscape", "non_diegetic_music")


def milliseconds(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{field}: expected a number of seconds")
    try:
        result = Decimal(str(value)) * 1000
        if not result.is_finite() or result < 0 or result != result.to_integral_value():
            raise ValueError(f"{field}: use non-negative seconds with millisecond precision")
        return int(result)
    except InvalidOperation as exc:
        raise ValueError(f"{field}: invalid seconds") from exc


def plan_timeline(duration, maximum=30, minimum=5):
    target = milliseconds(duration, "duration")
    maximum_ms = milliseconds(maximum, "max_clip")
    minimum_ms = milliseconds(minimum, "min_clip")
    if not 0 < minimum_ms <= maximum_ms or target < minimum_ms:
        raise ValueError("duration and clip limits cannot form a valid timeline")
    count = (target + maximum_ms - 1) // maximum_ms
    if target < count * minimum_ms:
        raise ValueError("requested duration cannot fit the live minimum/maximum clip limits")
    remaining, start, segments = target, 0, []
    for index in range(count):
        length = min(maximum_ms, remaining - (count - index - 1) * minimum_ms)
        identity = f"segment-{index + 1:03d}"
        segments.append({"id": identity,
                         "start_seconds": start / 1000, "duration_seconds": length / 1000,
                         "narration_path": f"audio/{identity}.mp3",
                         "video_path": f"video/{identity}.mp4"})
        start += length
        remaining -= length
    return {"target_duration_seconds": target / 1000,
            "max_clip_seconds": maximum_ms / 1000, "fps": 24,
            "voiceover": True, "continuity": True, "segments": segments}


def local_path(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("media paths must be relative to the manifest directory")
    result = (root / value).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("media path leaves the task workspace")
    return result


def segment_media_path(root, segment, field):
    value = segment.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{segment['id']}.{field}: missing media binding; set this field to the relative "
                         "path of the file already imported into this workspace. Keep existing media; do not regenerate it")
    try:
        return local_path(root, value)
    except ValueError as exc:
        raise ValueError(f"{segment['id']}.{field}: {exc}") from exc


def run_program(arguments, timeout=900):
    result = subprocess.run(arguments, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError(f"{Path(arguments[0]).name} failed: {result.stderr[-2000:]}")
    return result.stdout


def probe(path):
    if not path.is_file():
        raise ValueError(f"missing media file: {path.name}")
    return json.loads(run_program(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                  "-of", "json", str(path)], timeout=60))


def media_duration(metadata, kind):
    stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == kind), None)
    if stream is None:
        raise ValueError(f"missing {kind} stream")
    value = stream.get("duration") or metadata.get("format", {}).get("duration")
    try:
        seconds = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"missing measured {kind} duration") from exc
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError(f"invalid measured {kind} duration")
    return seconds


def check_h3_prompt(prompt, duration, input_mode="t2va"):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("missing MiniMax H3 prompt")
    labels = H3_LABELS
    fields = re.split(r"(?m)^\s*(integrated_multimodal_description|overall_soundscape|non_diegetic_music):\s*", prompt)
    if len(fields) != 7 or tuple(fields[1::2]) != labels:
        raise ValueError("prompt must contain integrated_multimodal_description, overall_soundscape and non_diegetic_music as three ordered text sections. If the sound fields were saved beside prompt, run prepare-plan on this saved manifest; do not regenerate the shots")
    if input_mode not in ("t2va", "i2va"):
        raise ValueError("this workflow supports t2va or i2va; do not mislabel other reference modes")
    if fields[0].strip() != (I2VA_PREFIX if input_mode == "i2va" else ""):
        raise ValueError("H3 alignment prefix must match the t2va/i2va input mode")
    if fields[4].strip() != "N/A" or fields[6].strip() != "N/A":
        raise ValueError("separate voiceover requires silent H3 soundscape/music sections (N/A)")
    matches = list(re.finditer(r"\[Shot (\d+)\]", fields[2]))
    if len(matches) < 4 or [int(m[1]) for m in matches] != list(range(1, len(matches) + 1)):
        raise ValueError("each clip needs at least four consecutive MiniMax H3 shots starting at 1")
    last_time = 0
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(fields[2])
        text = fields[2][match.end():end].strip()
        if not text:
            raise ValueError("every H3 shot requires a concrete visual description")
        if not index and re.match(r"At \d{2}:\d{2}", text):
            raise ValueError("H3 Shot 1 begins with its visual description, not a cut time")
        if index:
            stamp = re.match(r"At (\d{2}):([0-5]\d)(?:\.(\d{1,3}))?,\s*(\S.+)", text, re.S)
            if not stamp:
                raise ValueError("H3 cuts need At MM:SS.mmm, followed by a visual description")
            instant = int(stamp[1]) * 60000 + int(stamp[2]) * 1000 + int((stamp[3] or "0").ljust(3, "0"))
            if not last_time < instant < duration:
                raise ValueError("H3 shot times must increase within the clip duration")
            last_time = instant
    return len(matches)


def prepare_plan(manifest_path):
    """Canonicalize unambiguous saved fields, validate, then atomically commit.

    No invented shots, timing, narration, reference prefix or sound defaults.
    The exact original is retained once by digest, and repeat calls are no-ops.
    """
    original = manifest_path.read_bytes()
    manifest, json_format_repaired = load_plan_json(original)
    candidate = copy.deepcopy(manifest)
    changes = []
    if not isinstance(candidate, dict) or not isinstance(candidate.get("segments"), list):
        raise ValueError("manifest must contain a segments array")
    for index, segment in enumerate(candidate["segments"]):
        if not isinstance(segment, dict) or not isinstance(segment.get("prompt"), str):
            raise ValueError(f"segments[{index}].prompt must be text; preserve the saved plan and correct only this field")
        before = segment["prompt"]
        # Only format delimiters are decoded, never arbitrary prose or source.
        prompt = re.sub(r"(?:\\r\\n|\\n)+(?=(?:integrated_multimodal_description|overall_soundscape|non_diegetic_music):)", "\n\n", before)
        normalized_delimiters = prompt != before
        fields = re.split(r"(?m)^\s*(integrated_multimodal_description|overall_soundscape|non_diegetic_music):\s*", prompt)
        labels = fields[1::2]
        if not labels or labels[0] != H3_LABELS[0] or len(set(labels)) != len(labels):
            raise ValueError(f"segments[{index}].prompt has missing/duplicate visual sections; correct that field only")
        existing = dict(zip(labels, fields[2::2]))
        moved = []
        for name in H3_LABELS[1:]:
            if name not in segment:
                continue
            value = segment[name]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"segments[{index}].{name} must be nonempty text")
            if name in existing:
                if existing[name].strip() != value.strip():
                    raise ValueError(f"segments[{index}].{name} conflicts with prompt; choose the intended value explicitly")
            else:
                prompt += "\n\n" + name + ": " + value
            moved.append(name)
        segment["prompt"] = prompt
        for name in moved:
            del segment[name]
        if before != prompt or moved:
            changes.append({"segment_id": segment.get("id"), "field": "prompt", "moved_fields": moved,
                            "format_delimiters_normalized": normalized_delimiters})
    report = check_manifest(candidate, manifest_path.parent, plan_only=True)
    report.update(manifest=manifest_path.name, normalized_segments=changes,
                  json_format_repaired=json_format_repaired)
    if not changes and not json_format_repaired:
        return report
    # Validate every segment before writing anything. Never partially repair a plan.
    if manifest_path.read_bytes() != original:
        raise ValueError("manifest changed during preparation; read the current revision")
    digest = hashlib.sha256(original).hexdigest()
    backup = manifest_path.with_name(manifest_path.name + ".original-" + digest + ".json")
    if backup.exists():
        if backup.read_bytes() != original:
            raise ValueError("original plan backup integrity mismatch")
    else:
        with backup.open("xb") as stream:
            stream.write(original)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=manifest_path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(candidate, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if manifest_path.read_bytes() != original:
            raise ValueError("manifest changed during preparation; original was not replaced")
        os.replace(temporary, manifest_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    report.update(original_backup=backup.name, manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())
    return report


def check_manifest(manifest, root, audio_only=False, plan_only=False, references_only=False):
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    target = milliseconds(manifest["target_duration_seconds"], "target_duration_seconds")
    maximum = milliseconds(manifest.get("max_clip_seconds", 30), "max_clip_seconds")
    fps = manifest.get("fps", 24)
    if type(fps) is not int or not 1 <= fps <= 60 or not target or not maximum:
        raise ValueError("invalid duration, maximum clip duration or fps")
    for flag in ("voiceover", "continuity"):
        if flag in manifest and type(manifest[flag]) is not bool:
            raise ValueError(f"{flag}: expected a JSON boolean")
    segments = manifest.get("segments")
    if not isinstance(segments, list) or not 1 <= len(segments) <= 64:
        raise ValueError("segments must be a nonempty array, at most 64 entries")
    cursor, ids, jobs, measurements = 0, set(), set(), []
    dimensions = None
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f"segments[{index}] must be a JSON object")
        identity = segment.get("id")
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError("segment IDs must be nonempty and unique")
        ids.add(identity)
        # Destination syntax can be checked before any TTS/GPU work. Old
        # plans may omit not-yet-bound media, but supplied paths must be valid.
        for field in ("narration_path", "video_path"):
            if field in segment:
                segment_media_path(root, segment, field)
        start = milliseconds(segment["start_seconds"], identity + ".start_seconds")
        duration = milliseconds(segment["duration_seconds"], identity + ".duration_seconds")
        if start != cursor or not 0 < duration <= maximum:
            raise ValueError(f"{identity}: gap, overlap or unsupported segment duration")
        if duration * fps % 1000:
            raise ValueError(f"{identity}: duration must align to output video frames")
        cursor += duration
        try:
            mode = segment.get("input_mode", "i2va" if index and manifest.get("continuity", True) else "t2va")
            if index and manifest.get("continuity", True) and mode != "i2va":
                raise ValueError("continuation clips require i2va, not unreferenced text-to-video")
            shots = check_h3_prompt(segment.get("prompt"), duration, mode)
        except ValueError as exc:
            raise ValueError(f"{identity}: {exc}") from exc
        measured = {"id": identity, "duration_seconds": duration / 1000, "shot_count": shots}
        narration = segment.get("narration")
        if manifest.get("voiceover", True) and (not isinstance(narration, str) or not narration.strip()):
            raise ValueError(f"{identity}: missing narration text")
        if not plan_only and manifest.get("voiceover", True):
            audio = probe(segment_media_path(root, segment, "narration_path"))
            actual = media_duration(audio, "audio")
            offset = milliseconds(segment.get("narration_offset_seconds", 0), identity + ".narration_offset_seconds")
            if actual * 1000 + offset > duration:
                raise ValueError(f"{identity}: narration is {actual:.3f}s plus {offset / 1000:.3f}s offset, "
                                 f"longer than {duration / 1000:.3f}s; revise only this narration")
            measured["narration_seconds"] = actual
        if not plan_only and not audio_only:
            if segment.get("generation_status") != "completed":
                raise ValueError(f"{identity}: generation has not completed")
            job = segment.get("job_id")
            if not isinstance(job, str) or not job or job in jobs:
                raise ValueError(f"{identity}: missing or duplicated generation job ID")
            jobs.add(job)
            if mode == "i2va" and not segment.get("first_frame_url"):
                raise ValueError(f"{identity}: i2va requires an actual first-frame reference")
            if index and manifest.get("continuity", True):
                previous = segments[index - 1].get("last_frame_url")
                if not isinstance(previous, str) or not previous.strip() or segment.get("first_frame_url") != previous:
                    raise ValueError(f"{identity}: missing exact previous-last-frame to next-first-frame handoff")
            if references_only:
                for field in ("video_url", "narration_url") if manifest.get("voiceover", True) else ("video_url",):
                    url = segment.get(field)
                    parsed = urlsplit(url) if isinstance(url, str) else None
                    if not parsed or parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                        raise ValueError(f"{identity}.{field}: save the exact returned downloadable URL; do not regenerate media")
                measurements.append(measured)
                continue
            video = probe(segment_media_path(root, segment, "video_path"))
            actual = media_duration(video, "video")
            if actual + 0.001 < duration / 1000:
                raise ValueError(f"{identity}: video is only {actual:.3f}s, needs {duration / 1000:.3f}s; no looping or freeze-fill")
            stream = next(s for s in video["streams"] if s.get("codec_type") == "video")
            shape = (stream["width"], stream["height"])
            if dimensions is not None and shape != dimensions:
                raise ValueError(f"{identity}: clip dimensions differ; correct this media input")
            dimensions = shape
            measured["video_seconds"] = actual
        measurements.append(measured)
    if cursor != target:
        raise ValueError(f"timeline covers {cursor / 1000:.3f}s, requested {target / 1000:.3f}s")
    return {"status": "plan_ready" if plan_only else "audio_ready" if audio_only else "inputs_ready", "target_duration_seconds": target / 1000,
            "segment_count": len(segments), "measurements": measurements}


def timeline_arguments(manifest, root):
    """Validate receipts locally; pass references, never large video files.

    The media service independently probes every actual input before encoding.
    This script verifies the Skill's continuity and narration obligations.
    """
    check_manifest(manifest, root, references_only=True)
    if manifest.get("fps", 24) != 24:
        raise ValueError("the current timeline service outputs 24 fps; use its live schema for other frame rates")
    return {"segments": [dict(video_url=s["video_url"], duration_seconds=s["duration_seconds"],
        **({"audio_url": s["narration_url"], "audio_offset_seconds": s.get("narration_offset_seconds", 0)}
           if manifest.get("voiceover", True) else {})) for s in manifest["segments"]]}


def assemble(manifest, root, output_name):
    report = check_manifest(manifest, root)
    output = local_path(root, output_name)
    if output.exists():
        raise ValueError("output already exists; verify/publish it or use a new filename for an explicit edit")
    output.parent.mkdir(parents=True, exist_ok=True)
    fps = manifest.get("fps", 24)
    spoken = manifest.get("voiceover", True)
    # Temporary intermediates are task-local; saved inputs survive any failure.
    with tempfile.TemporaryDirectory(prefix=".promo-", dir=root) as temporary:
        stage = Path(temporary)
        names = []
        for index, segment in enumerate(manifest["segments"]):
            duration = milliseconds(segment["duration_seconds"], "duration") / 1000
            clip = stage / f"part-{index:03d}.mkv"
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                       "-i", str(local_path(root, segment["video_path"]))]
            filters = f"[0:v:0]trim=duration={duration},setpts=PTS-STARTPTS,fps={fps},format=yuv420p[v]"
            if spoken:
                command += ["-i", str(local_path(root, segment["narration_path"]))]
                offset = milliseconds(segment.get("narration_offset_seconds", 0), "narration_offset")
                filters += (f";[1:a:0]aresample=48000,asetpts=PTS-STARTPTS,adelay={offset}:all=1,"
                            f"apad,atrim=duration={duration}[a]")
            command += ["-filter_complex", filters, "-map", "[v]"]
            if spoken:
                command += ["-map", "[a]", "-ac", "2", "-c:a", "pcm_s16le"]
            else:
                command += ["-an"]
            command += ["-c:v", "libx264", "-preset", "fast", "-threads", "2", "-b:v", "1800k",
                        "-maxrate", "2200k", "-bufsize", "4400k", str(clip)]
            run_program(command)
            names.append(f"file '{clip.name}'\n")
        concat = stage / "concat.txt"
        concat.write_text("".join(names), encoding="utf-8")
        combined = stage / "combined.mp4"
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "concat",
                   "-safe", "1", "-i", str(concat), "-map", "0:v:0", "-c:v", "copy"]
        command += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k"] if spoken else ["-an"]
        command += ["-movflags", "+faststart", str(combined)]
        run_program(command)
        metadata = probe(combined)
        duration = media_duration(metadata, "video")
        if abs(duration - report["target_duration_seconds"]) > 1 / fps + 0.02:
            raise ValueError("assembled video duration differs from the requested target")
        if spoken and abs(media_duration(metadata, "audio") - duration) > 1 / fps + 0.05:
            raise ValueError("assembled narration track does not match the video timeline")
        with combined.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        # The verified file is exposed only after every input and final check passes.
        combined.rename(output)
    return {"status": "assembled", "output": output_name, "duration_seconds": duration,
            "segment_count": report["segment_count"], "has_narration": spoken,
            "sha256": digest, "size_bytes": output.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--duration", type=float, required=True)
    plan.add_argument("--max-clip", type=float, default=30)
    plan.add_argument("--min-clip", type=float, default=5)
    for name in ("prepare-plan", "check-plan", "check-audio", "check", "assemble", "timeline-arguments"):
        sub = commands.add_parser(name)
        sub.add_argument("--manifest", required=True)
        if name == "assemble":
            sub.add_argument("--output", default="final-promo.mp4")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            result = plan_timeline(args.duration, args.max_clip, args.min_clip)
        elif args.command == "prepare-plan":
            result = prepare_plan(Path(args.manifest).resolve())
        else:
            manifest_path = Path(args.manifest).resolve()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            root = manifest_path.parent
            result = (assemble(manifest, root, args.output) if args.command == "assemble" else
                      timeline_arguments(manifest, root) if args.command == "timeline-arguments" else
                      check_manifest(manifest, root, audio_only=args.command == "check-audio",
                                     plan_only=args.command == "check-plan"))
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
