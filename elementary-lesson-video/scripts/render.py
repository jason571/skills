from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from lesson import validate_lesson
from mux import mux
from timeline import SUPPORTED_FPS, assemble_audio, build_timeline, write_srt
from tts import prepare_audio, validate_cached_audio
from util import load_json, run_cmd, save_json, sha256_file, skill_root, render_progress

QUALITY = {"l": "-ql", "m": "-qm", "h": "-qh", "k": "-qk"}


def render_manim(out_dir: Path, quality: str, fps: int) -> Path:
    # Preserve previous attempts for failure investigation; do not rmtree user data.
    media_root = out_dir / "manim"
    media_root.mkdir(parents=True, exist_ok=True)
    media_dir = Path(tempfile.mkdtemp(prefix="attempt-", dir=media_root))
    env = os.environ.copy()
    env["LESSON_DIR"] = str(out_dir)
    proc = run_cmd([sys.executable, "-m", "manim", QUALITY[quality], "--fps", str(fps),
                    "--renderer", "cairo", "--disable_caching", "--media_dir", str(media_dir),
                    "-o", "lesson_silent", str(skill_root() / "scripts" / "manim_lesson.py"),
                    "LessonScene"], capture_output=True, env=env, cwd=skill_root(), timeout=1800)
    (media_dir / "render.log").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"Manim 渲染失败，详见 {media_dir / 'render.log'}\n{proc.stderr[-2000:]}")
    matches = [p for p in media_dir.rglob("lesson_silent.mp4") if "partial_movie_files" not in p.parts]
    if len(matches) != 1:
        raise RuntimeError("Manim 必须产出唯一完整 lesson_silent.mp4，不能使用中间片段")
    return matches[0]


def render_lesson(lesson_path: Path, out_dir: Path, audio_manifest: Path | None,
                  quality: str = "l", fps: int = 30, audio_only: bool = False) -> dict:
    lesson_path, out_dir = lesson_path.resolve(), out_dir.resolve()
    lesson = load_json(lesson_path)
    validate_lesson(lesson)
    out_dir.mkdir(parents=True, exist_ok=True)
    if audio_manifest is not None:
        raw = prepare_audio(lesson, audio_manifest, out_dir)
    else:
        raw = load_json(out_dir / "tts_raw.json")
    validate_cached_audio(lesson, raw, out_dir)
    # Persist a new lesson only after old narration/audio bindings were checked.
    save_json(out_dir / "lesson.json", lesson)
    save_json(out_dir / "tts_raw.json", raw)
    timeline = build_timeline(raw, fps)
    audio = assemble_audio(timeline, out_dir)
    save_json(out_dir / "timeline.json", timeline)
    write_srt(timeline, out_dir / "subtitles.srt")
    render_progress(out_dir, 15, "配音已解码，真实时间轴已建立")
    print(f"音频已准备：{len(raw['segments'])} 段，{timeline['total_duration_sec']:.3f}s；无需再次调用 TTS", file=sys.stderr)
    files = [{"kind": "audio", "local_path": str(audio), "content_type": "audio/wav",
              "sha256": sha256_file(audio), "size_bytes": audio.stat().st_size}]
    report = {"schema_version": 1, "alignment": "segment", "tts_calls_by_renderer": 0,
              "fps": fps, "total_frames": timeline["total_frames"],
              "duration_sec": timeline["total_duration_sec"]}
    if not audio_only:
        silent = render_manim(out_dir, quality, fps)
        render_progress(out_dir, 90, "动画渲染完成，正在合成配音并校验音画同步")
        final = out_dir / "final.mp4"
        report.update(mux(silent, audio, final, timeline))
        files.append({"kind": "video", "local_path": str(final), "content_type": "video/mp4",
                      "sha256": sha256_file(final), "size_bytes": final.stat().st_size})
    report["files"] = files
    save_json(out_dir / "validation.json", report)
    render_progress(out_dir, 97, "最终音视频流与时间轴校验通过")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="使用已配置 TTS 的音频产物，按共同时间轴渲染 Manim")
    parser.add_argument("--lesson", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="本次任务独立的可写目录")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--audio-manifest", type=Path)
    source.add_argument("--skip-tts", action="store_true", help="验证并复用本任务已有音频缓存")
    parser.add_argument("--quality", "-q", choices=list(QUALITY), default="l")
    parser.add_argument("--fps", type=int, choices=SUPPORTED_FPS, default=30)
    parser.add_argument("--audio-only", action="store_true")
    args = parser.parse_args()
    report = render_lesson(args.lesson, args.out, args.audio_manifest, args.quality, args.fps, args.audio_only)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
