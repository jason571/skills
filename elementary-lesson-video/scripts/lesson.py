"""Validate before synthesis; invalid plans must not spend TTS calls."""
from __future__ import annotations

import math
import re

from util import parse_grade_num, text_digest
from scene_contract import validate_scene_chain

VISUAL_TYPES = {"title", "talking_text", "bullets", "formula", "steps",
                "fraction_pies", "number_line", "compare", "geometry", "quiz", "table", "bar_model", "scene"}


def validate_lesson(lesson: dict) -> None:
    if not isinstance(lesson, dict):
        raise ValueError("lesson 必须是对象")
    for key in ("title", "question", "subject", "grade"):
        if not isinstance(lesson.get(key), str) or not lesson[key].strip():
            raise ValueError(f"{key} 必须是非空文字")
    parse_grade_num(lesson["grade"])
    segments = lesson.get("segments")
    if not isinstance(segments, list) or not 1 <= len(segments) <= 100:
        raise ValueError("segments 必须有 1–100 段")
    seen = set()
    for seg in segments:
        if not isinstance(seg, dict):
            raise ValueError("segment 必须是对象")
        key = seg.get("id")
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", key):
            raise ValueError("segment id 必须是安全的字母数字短名，不能包含路径")
        if key in seen:
            raise ValueError(f"重复 segment id: {key}")
        seen.add(key)
        text = seg.get("narration")
        if not isinstance(text, str) or not text.strip() or len(text) > 20000:
            raise ValueError(f"{key}: narration 必须是非空、至多 20000 字的文字")
        visual = seg.get("visual", {"type": "talking_text"})
        if not isinstance(visual, dict) or visual.get("type") not in VISUAL_TYPES:
            raise ValueError(f"{key}: 未支持的 visual.type")
        kind = visual["type"]
        if kind == "table":
            columns, rows = visual.get("columns"), visual.get("rows")
            if not isinstance(columns, list) or not 1 <= len(columns) <= 5 or not isinstance(rows, list) or not 1 <= len(rows) <= 6:
                raise ValueError(f"{key}: 表格需要 1–5 列、1–6 行")
            if any(not isinstance(row, list) or len(row) != len(columns) for row in rows) or any(not isinstance(cell, str) for row in [columns, *rows] for cell in row):
                raise ValueError(f"{key}: 表格行列必须对齐，单元格必须为文字")
        if kind == "bar_model":
            rows = visual.get("rows")
            if not isinstance(rows, list) or not 1 <= len(rows) <= 4:
                raise ValueError(f"{key}: 线段图需要 1–4 行")
            for row in rows:
                parts = row.get("parts") if isinstance(row, dict) else None
                if not isinstance(parts, list) or not 1 <= len(parts) <= 8:
                    raise ValueError(f"{key}: 每条线段需要 1–8 部分")
                for part in parts:
                    value = part.get("value") if isinstance(part, dict) else None
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= 1000000:
                        raise ValueError(f"{key}: 线段长度必须为正数且不超过 1000000")
        if kind in {"steps", "bullets", "formula"}:
            rows = visual.get("lines" if kind == "formula" else "items")
            if not isinstance(rows, list) or not 1 <= len(rows) <= 12 or any(not isinstance(x, str) or not x.strip() for x in rows):
                raise ValueError(f"{key}: 视觉条目必须是 1–12 条非空文字")
        if kind == "number_line":
            lo, hi, step = (visual.get(k, v) for k, v in (("min", 0), ("max", 10), ("step", 1)))
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lo, hi, step)) or hi <= lo or step <= 0 or (hi - lo) / step > 100:
                raise ValueError(f"{key}: 数轴范围/步长不合法或刻度过多")
        if kind == "fraction_pies":
            items = visual.get("items")
            if not isinstance(items, list) or not 1 <= len(items) <= 6:
                raise ValueError(f"{key}: 分数图需要 1–6 项")
            for item in items:
                if not isinstance(item, dict) or type(item.get("n")) is not int or type(item.get("d")) is not int or not 0 <= item["n"] <= item["d"] <= 48 or item["d"] == 0:
                    raise ValueError(f"{key}: 分数必须满足 0 <= n <= d <= 48, d > 0")
        if kind == "quiz":
            if not all(isinstance(visual.get(k), str) and visual[k].strip() for k in ("question", "answer")):
                raise ValueError(f"{key}: quiz 缺少 question/answer")
            ratio = visual.get("reveal_at", .55)
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or not 0 <= ratio <= 1:
                raise ValueError(f"{key}: reveal_at 必须在 0–1")
    validate_scene_chain([seg.get("visual") for seg in segments])


def speech_requests(lesson: dict) -> dict:
    validate_lesson(lesson)
    return {"schema_version": 1, "segments": [
        {"id": seg["id"], "narration_sha256": text_digest(seg["narration"]),
         "arguments": {"text": seg["narration"], "filename": f"{seg['id']}.mp3"}}
        for seg in lesson["segments"]]}
