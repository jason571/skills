"""Mux only verified aligned media; do not conceal rendering failures by padding."""
from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path

from util import run_cmd


def probe_streams(path: Path) -> list[dict]:
    proc = run_cmd(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)], capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"ffprobe 失败: {proc.stderr[-2000:]}")
    return json.loads(proc.stdout)["streams"]


def stream_duration(stream: dict) -> float:
    value = float(stream["duration"])
    if not math.isfinite(value) or value <= 0:
        raise ValueError("流时长不是有效正数")
    return value


def check_video(stream: dict, timeline: dict) -> None:
    if Fraction(stream["r_frame_rate"]) != timeline["fps"] or int(stream.get("nb_frames", -1)) != timeline["total_frames"]:
        raise ValueError("Manim 视频帧率或总帧数与时间轴不同；请修复渲染，不补长尾掩盖错误")
    if abs(float(stream.get("start_time", 0))) > 1 / timeline["fps"]:
        raise ValueError("视频不是从时间轴零点开始")
    if abs(stream_duration(stream) - timeline["total_duration_sec"]) > 1 / timeline["fps"]:
        raise ValueError("视频流时长与时间轴不符")


def mux(video: Path, audio: Path, out_file: Path, timeline: dict) -> dict:
    videos = [s for s in probe_streams(video) if s["codec_type"] == "video"]
    audios = [s for s in probe_streams(audio) if s["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise ValueError("需要恰好一个视频流和一个音频流")
    check_video(videos[0], timeline)
    expected = timeline["total_duration_sec"]
    if abs(stream_duration(audios[0]) - expected) > 1 / timeline["sample_rate"] + 1e-6:
        raise ValueError("音频采样时间轴不匹配，禁止用 -shortest 截断")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp = out_file.with_suffix(".partial.mp4")
    proc = run_cmd(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video), "-i", str(audio),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", str(temp)], capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"合成失败: {proc.stderr[-2000:]}")
    streams = probe_streams(temp)
    v = next(s for s in streams if s["codec_type"] == "video")
    a = next(s for s in streams if s["codec_type"] == "audio")
    check_video(v, timeline)
    video_sec, audio_sec = stream_duration(v), stream_duration(a)
    # AAC encoder padding is bounded; independently check each stream, not the container.
    tolerance = max(1 / timeline["fps"], 1024 / timeline["sample_rate"]) + .001
    if abs(audio_sec - expected) > tolerance or abs(float(a.get("start_time", 0))) > tolerance or abs(video_sec - audio_sec) > tolerance:
        raise ValueError("最终音视频流不对齐，未发布 final.mp4")
    temp.replace(out_file)
    return {"video_sec": video_sec, "audio_sec": audio_sec,
            "drift_sec": abs(video_sec - audio_sec), "max_allowed_drift_sec": tolerance,
            "total_frames": timeline["total_frames"], "fps": timeline["fps"],
            "alignment": "segment", "verified": True}
