"""Real Manim/FFmpeg check with synthetic audio; no TTS API or model charges."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from render import render_lesson
from util import load_json, save_json, run_cmd
from test_pipeline import create_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=True)
    visuals = [
        {"type": "title", "title": "一起学减法", "subtitle": "二年级"},
        {"type": "talking_text", "heading": "看清题目"},
        {"type": "bullets", "items": ["原来八只", "拿走三只"]},
        {"type": "formula", "lines": ["8 − 3 = 5"]},
        {"type": "steps", "items": ["先数原来", "再减拿走", "还剩五只"]},
        {"type": "fraction_pies", "items": [{"n": 1, "d": 2, "label": "一半"}]},
        {"type": "number_line", "min": 0, "max": 8, "marks": [{"value": 5}]},
        {"type": "compare", "left": {"title": "原来", "body": "八只"}, "right": {"title": "剩下", "body": "五只"}},
        {"type": "geometry", "shape": "rectangle", "caption": "长方形", "labels": ["A", "B", "C", "D"]},
        {"type": "geometry", "shape": "triangle", "caption": "三角形", "labels": ["A", "B", "C"]},
        {"type": "geometry", "shape": "circle", "caption": "圆形", "labels": ["上", "右", "下", "左"]},
        {"type": "geometry", "shape": "circle", "caption": "不带标签的圆"},
        {"type": "quiz", "question": "八减三等于几？", "answer": "五", "reveal_at": .5},
    ]
    lesson = {"title": "真实渲染回归", "question": "检查全部视觉与时间轴", "subject": "数学", "grade": "小学二年级",
              "segments": [{"id": f"s{i+1:02}", "narration": "原来八只，拿走三只，还剩五只。", "visual": v} for i, v in enumerate(visuals)]}
    lesson_path = root / "lesson.json"
    save_json(lesson_path, lesson)
    manifest = create_manifest(root, lesson, [26000 + i * 997 for i in range(len(visuals))])
    # Exercise a timestamp starting at exactly 0, plus near-end highlighting.
    data = load_json(manifest)
    data["segments"][1]["words"] = [{"text": "原来", "start_sec": 0, "end_sec": .2},
                                    {"text": "八只", "start_sec": .3, "end_sec": .5}]
    save_json(manifest, data)
    reports = []
    for fps in (15, 30, 60):
        out = root / f"render-{fps}"
        report = render_lesson(lesson_path, out, manifest, fps=fps)
        timeline = load_json(out / "timeline.json")
        # Decode boundary frames to actual image bytes, not just a duration claim.
        for seg in timeline["segments"]:
            frame = seg["start_frame"]
            frames = []
            for target in ([frame - 1, frame] if frame else [0]):
                proc = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(out / "final.mp4"),
                                       "-vf", f"select=eq(n\\,{target})", "-frames:v", "1", "-f", "image2pipe", "-vcodec", "ppm", "-"],
                                      capture_output=True, timeout=30)
                if proc.returncode or not proc.stdout.startswith(b"P6"):
                    raise AssertionError(f"Missing visual boundary frame {target}")
                frames.append(proc.stdout)
            if len(frames) == 2 and frames[0] == frames[1]:
                raise AssertionError(f"Visual did not change at expected segment boundary {frame}")
        reports.append(report)
    save_json(root / "smoke_results.json", reports)
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
