"""A shared integer sample/frame clock, not estimated MP3 container durations."""
from __future__ import annotations

import wave
from pathlib import Path

from tts import SAMPLE_RATE

SUPPORTED_FPS = (15, 24, 25, 30, 50, 60)


def build_timeline(tts_raw: dict, fps: int = 30) -> dict:
    if type(fps) is not int or fps not in SUPPORTED_FPS:
        raise ValueError(f"fps 必须是 {SUPPORTED_FPS} 之一")
    per_frame = SAMPLE_RATE // fps
    cursor = 0
    segments = []
    for item in tts_raw["segments"]:
        samples = item["samples"]
        if type(samples) is not int or samples <= 0 or item["sample_rate"] != SAMPLE_RATE:
            raise ValueError("时间轴需要真实的正整数采样数及 48000 采样率")
        frames = (samples + per_frame - 1) // per_frame
        slot_samples = frames * per_frame
        segments.append({**item, "start_frame": cursor, "end_frame": cursor + frames,
                         "frame_count": frames, "start_sample": cursor * per_frame,
                         "slot_samples": slot_samples, "silence_samples": slot_samples - samples,
                         "start": cursor / fps, "end": (cursor + frames) / fps,
                         "speech_end": cursor / fps + samples / SAMPLE_RATE,
                         "duration_sec": frames / fps})
        cursor += frames
    if not segments:
        raise ValueError("时间轴不能为空")
    return {"schema_version": 2, "provider": tts_raw.get("provider"), "fps": fps,
            "sample_rate": SAMPLE_RATE, "total_frames": cursor,
            "total_samples": cursor * per_frame, "total_duration_sec": cursor / fps,
            "segments": segments}


def assemble_audio(timeline: dict, out_dir: Path) -> Path:
    target = out_dir / "audio" / "speech.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".partial.wav")
    with wave.open(str(temp), "wb") as output:
        output.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        for seg in timeline["segments"]:
            source_path = (out_dir / seg["audio"]).resolve()
            if not source_path.is_relative_to(out_dir.resolve()):
                raise ValueError("音频缓存路径越界")
            with wave.open(str(source_path), "rb") as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getnframes()) != (1, 2, SAMPLE_RATE, seg["samples"]):
                    raise ValueError(f"{seg['id']}: PCM 缓存与时间轴不匹配")
                while block := source.readframes(65536):
                    output.writeframesraw(block)
            # Only pad the sub-frame boundary gap. Never trim speech or stretch it.
            output.writeframesraw(b"\0\0" * seg["silence_samples"])
        if output.getnframes() != timeline["total_samples"]:
            raise ValueError("合成音频的采样数与时间轴不一致")
    temp.replace(target)
    return target


def write_srt(timeline: dict, path: Path) -> None:
    lines = []
    for i, seg in enumerate(timeline["segments"], 1):
        lines += [str(i), f"{_ts(seg['start'])} --> {_ts(seg['speech_end'])}",
                  seg["narration"].replace("\n", " "), ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _ts(seconds: float) -> str:
    ms = round(seconds * 1000)
    hours, rest = divmod(ms, 3600000)
    minutes, rest = divmod(rest, 60000)
    seconds, milli = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milli:03d}"
