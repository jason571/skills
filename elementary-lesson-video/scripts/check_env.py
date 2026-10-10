"""Read-only local dependency check; it does not claim a remote TTS is configured."""
import argparse
import json
import sys

from util import pick_cjk_font, which


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-only", action="store_true")
    parser.add_argument("--font")
    args = parser.parse_args()
    missing = [name for name in ("ffmpeg", "ffprobe") if not which(name)]
    report = {"python": sys.version.split()[0], "ffmpeg": bool(which("ffmpeg")),
              "ffprobe": bool(which("ffprobe")),
              "tts": "Agent 必须检查当前可调用的已启用语音合成能力；本地无需 TTS Key 或 ENV"}
    if not args.audio_only:
        try:
            import manim
            import manimpango
            report["manim"] = manim.__version__
            font = pick_cjk_font(args.font)
            report["font"] = font
            if font not in manimpango.list_fonts():
                missing.append(f"中文字体 {font}")
        except ImportError as exc:
            missing.append(f"Manim 运行库: {exc.name}")
    report["missing"] = missing
    report["local_runtime_ready"] = not missing
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return bool(missing)


if __name__ == "__main__":
    raise SystemExit(main())
