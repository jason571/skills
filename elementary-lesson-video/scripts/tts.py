"""Bind configured-model ToolResults to narration; never call a provider.

The Agent invokes the enabled speech-synthesis capability using its live schema.
An authorized artifact transfer stages the results locally. This module validates
those bindings and decodes the files, without credentials, network or TTS retries.
"""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

from lesson import speech_requests, validate_lesson
from util import load_json, run_cmd, save_json, sha256_file, text_digest

SAMPLE_RATE = 48000
MAX_AUDIO_BYTES = 128 * 1024 * 1024
MAX_SEGMENT_SECONDS = 600


def wav_info(path: Path) -> dict:
    with wave.open(str(path), "rb") as stream:
        if (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError("中间音频必须是 48kHz/mono/PCM16 WAV")
        samples = stream.getnframes()
    if not 0 < samples <= SAMPLE_RATE * MAX_SEGMENT_SECONDS:
        raise ValueError("音频为空或单段超过 600 秒")
    return {"sample_rate": SAMPLE_RATE, "samples": samples,
            "duration_sec": samples / SAMPLE_RATE, "pcm_sha256": sha256_file(path)}


def validate_words(words: list, samples: int) -> list:
    # Explicit seconds only. No guessing milliseconds from numeric magnitude.
    import math
    if not isinstance(words, list):
        raise ValueError("words 必须是数组")
    previous = 0.0
    result = []
    for word in words:
        if not isinstance(word, dict) or not isinstance(word.get("text"), str) or not word["text"].strip():
            raise ValueError("word 缺少 text")
        start, end = word.get("start_sec"), word.get("end_sec")
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in (start, end)):
            raise ValueError("word 必须声明 start_sec/end_sec，不能猜测时间单位")
        if not 0 <= previous <= start < end <= samples / SAMPLE_RATE:
            raise ValueError("word 时间戳乱序或超出真实音频范围")
        result.append({"text": word["text"], "start": start, "duration": end - start})
        previous = start
    return result


def prepare_audio(lesson: dict, manifest_path: Path, out_dir: Path) -> dict:
    validate_lesson(lesson)
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("segments"), list):
        raise ValueError("audio_manifest 需要 schema_version=1 和 segments")
    records = {}
    for entry in manifest["segments"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or entry["id"] in records:
            raise ValueError("音频绑定 id 缺失或重复")
        records[entry["id"]] = entry
    if set(records) != {seg["id"] for seg in lesson["segments"]}:
        raise ValueError("音频绑定必须与 lesson 的段落一一对应，不能漏段或多段")
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    result = []
    inputs = []
    for seg in lesson["segments"]:
        record = records[seg["id"]]
        digest = text_digest(seg["narration"])
        if record.get("narration_sha256") != digest:
            raise ValueError(f"{seg['id']}: narration 已变更；仅重新合成这一段并更新绑定")
        artifact = record.get("artifact", {})
        if not isinstance(artifact, dict) or not isinstance(artifact.get("local_path"), str) or not artifact["local_path"]:
            raise ValueError(f"{seg['id']}: 先通过已授权的 Artifact 下载/挂载工具取得 local_path")
        if "://" in artifact["local_path"]:
            raise ValueError("local_path 不能是 URL；本脚本不读取登录凭据或下载外部地址")
        path = (manifest_path.parent / artifact["local_path"]).resolve(strict=True)
        if not path.is_file() or not 0 < path.stat().st_size <= MAX_AUDIO_BYTES:
            raise ValueError(f"{seg['id']}: 音频不是有效普通文件或超过 128MB")
        source_hash = sha256_file(path)
        if artifact.get("sha256") != source_hash:
            raise ValueError(f"{seg['id']}: 音频 SHA-256 与 ToolResult 不一致")
        inputs.append((seg, record, path, digest, source_hash))
    for seg, record, path, digest, source_hash in inputs:
        decoded = audio_dir / f"{source_hash}.wav"
        cache_record = decoded.with_suffix(".json")
        if decoded.exists():
            if not cache_record.is_file() or load_json(cache_record) != wav_info(decoded):
                raise ValueError(f"{seg['id']}: 解码缓存已损坏；隔离该缓存后从原音频重建，无需重做 TTS")
        if not decoded.exists():
            temp = decoded.with_suffix(".partial.wav")
            proc = run_cmd(["ffmpeg", "-nostdin", "-v", "error", "-y",
                            "-protocol_whitelist", "file,pipe", "-i", str(path),
                            "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
                            "-c:a", "pcm_s16le", "-t", str(MAX_SEGMENT_SECONDS + 1), str(temp)],
                           capture_output=True)
            if proc.returncode:
                raise RuntimeError(f"{seg['id']}: 音频解码失败: {proc.stderr[-2000:]}")
            info = wav_info(temp)
            temp.replace(decoded)
            save_json(cache_record, info)
        info = wav_info(decoded)
        words = validate_words(record.get("words", []), info["samples"])
        result.append({"id": seg["id"], "narration": seg["narration"],
                       "narration_sha256": digest, "audio": str(decoded.relative_to(out_dir)),
                       "source_sha256": source_hash, "artifact_id": record["artifact"].get("id"),
                       "invocation_id": record.get("invocation_id"), "words": words, **info})
    return {"schema_version": 1, "provider": "configured-model-capability",
            "sample_rate": SAMPLE_RATE, "segments": result}


def validate_cached_audio(lesson: dict, raw: dict, out_dir: Path) -> None:
    validate_lesson(lesson)
    if raw.get("schema_version") != 1 or [s["id"] for s in raw["segments"]] != [s["id"] for s in lesson["segments"]]:
        raise ValueError("音频缓存版本或段落顺序不匹配，请提供 --audio-manifest")
    for seg, item in zip(lesson["segments"], raw["segments"]):
        if item["narration_sha256"] != text_digest(seg["narration"]):
            raise ValueError(f"{seg['id']}: 讲解稿已改变，禁止 --skip-tts 使用旧音频")
        path = (out_dir / item["audio"]).resolve()
        if not path.is_relative_to(out_dir.resolve()):
            raise ValueError("缓存音频路径越界")
        actual = wav_info(path)
        if any(actual[k] != item[k] for k in ("samples", "pcm_sha256", "sample_rate")):
            raise ValueError(f"{seg['id']}: 缓存音频已损坏或被替换")
        validate_words([{"text": w["text"], "start_sec": w["start"],
                         "end_sec": w["start"] + w["duration"]}
                        for w in item.get("words", [])], item["samples"])


def main() -> int:
    parser = argparse.ArgumentParser(description="生成已配置 TTS 的分段调用参数；或绑定其真实音频产物")
    parser.add_argument("--lesson", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--audio-manifest", type=Path)
    args = parser.parse_args()
    lesson = load_json(args.lesson)
    if args.audio_manifest:
        out_dir = (args.out or args.lesson.parent).resolve()
        raw = prepare_audio(lesson, args.audio_manifest, out_dir)
        save_json(out_dir / "tts_raw.json", raw)
        print(json.dumps({"prepared_segments": len(raw["segments"]), "tts_calls": 0}))
    else:
        requests = speech_requests(lesson)
        if args.out:
            save_json(args.out, requests)
        else:
            print(json.dumps(requests, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
