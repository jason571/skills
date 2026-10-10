from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_cmd(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    kwargs.setdefault("timeout", 600)
    return subprocess.run(
        args,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kwargs,
    )


def which(name: str) -> str | None:
    return shutil.which(name)


def load_json(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} 必须是 JSON 对象")
    return data


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8", delete=False) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
        temporary = Path(f.name)
    temporary.replace(path)


def render_progress(out_dir: Path, progress: float, message: str) -> None:
    save_json(out_dir / "render-progress.json", {"progress": progress, "message": message})


def ffprobe_duration(path: Path) -> float:
    ffmpeg = which("ffprobe") or which("ffmpeg")
    if which("ffprobe") is None:
        raise RuntimeError("未找到 ffprobe，请安装 ffmpeg 并加入 PATH")
    proc = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {path}\n{proc.stderr}")
    return float(proc.stdout.strip())


def pick_cjk_font(preferred: str | None = None) -> str:
    if preferred:
        return preferred
    env_font = os.environ.get("LESSON_FONT")
    if env_font:
        return env_font
    if sys.platform == "win32":
        return "Microsoft YaHei"
    if sys.platform == "darwin":
        return "PingFang SC"
    return "Noto Sans CJK SC"


def slugify(text: str) -> str:
    keep = []
    for ch in text.strip().lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in "-_ " and (not keep or keep[-1] != "-"):
            keep.append("-")
    slug = "".join(keep).strip("-")
    return slug[:40] or "lesson"


GRADE_ALIASES = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
}


def parse_grade_num(grade: str) -> int:
    text = str(grade).strip()
    for ch, num in GRADE_ALIASES.items():
        if text in (f"小学{ch}年级", f"{ch}年级", f"小学{num}年级", f"{num}年级"):
            return num
    raise ValueError("grade 必须是小学一至六年级，例如 小学二年级")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def default_speech_rate(grade: str) -> int:
    num = parse_grade_num(grade)
    if num <= 2:
        return -20
    if num <= 4:
        return -10
    return 0
