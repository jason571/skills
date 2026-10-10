from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from manim import *
from manim.utils.color import ManimColor
import manimpango

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import load_json, pick_cjk_font, render_progress
from lesson import validate_lesson
from scene_visual import Diagram


def _hex(color: str, fallback: str) -> ManimColor:
    try:
        return ManimColor(color)
    except Exception:
        return ManimColor(fallback)


class LessonScene(Scene):
    def construct(self) -> None:
        lesson_dir = os.environ.get("LESSON_DIR")
        if not lesson_dir:
            raise RuntimeError("缺少环境变量 LESSON_DIR")
        self.lesson_dir = lesson_dir
        self.lesson = load_json(os.path.join(lesson_dir, "lesson.json"))
        self.timeline = load_json(os.path.join(lesson_dir, "timeline.json"))
        validate_lesson(self.lesson)
        if self.timeline.get("schema_version") != 2 or float(config.frame_rate) != self.timeline["fps"]:
            raise ValueError("Manim 帧率必须与采样时间轴完全一致")
        if [s["id"] for s in self.lesson["segments"]] != [s["id"] for s in self.timeline["segments"]]:
            raise ValueError("lesson 与 timeline 段落不匹配")
        self.frame_cursor = 0
        self.fps = self.timeline["fps"]
        style = self.lesson.get("style") or {}
        self.bg = _hex(str(style.get("background") or "#0F172A"), "#0F172A")
        self.primary = _hex(str(style.get("primary") or "#38BDF8"), "#38BDF8")
        self.accent = _hex(str(style.get("accent") or "#FBBF24"), "#FBBF24")
        self.fg = _hex(str(style.get("text") or "#F8FAFC"), "#F8FAFC")
        self.muted = _hex(str(style.get("muted") or "#94A3B8"), "#94A3B8")
        self.font = pick_cjk_font(self.lesson.get("font"))
        if self.font not in manimpango.list_fonts():
            raise ValueError(f"缺少指定中文字体: {self.font}")
        self.camera.background_color = self.bg
        self.current = None
        self.diagram_program = None

        visual_by_id = {
            seg["id"]: seg.get("visual") or {"type": "talking_text"}
            for seg in self.lesson["segments"]
        }
        for seg in self.timeline["segments"]:
            visual = visual_by_id.get(seg["id"]) or {"type": "talking_text"}
            self.play_segment(seg, visual)
            render_progress(Path(lesson_dir), 15 + 73 * self.frame_cursor / self.timeline["total_frames"],
                            f"已渲染 {self.frame_cursor}/{self.timeline['total_frames']} 帧（段落 {seg['id']}）")

    def txt(self, text: str, size: int = 36, color: ManimColor | None = None, **kwargs: Any) -> Text:
        return Text(
            text,
            font=self.font,
            font_size=size,
            color=color or self.fg,
            **kwargs,
        )

    def play_segment(self, seg: dict[str, Any], visual: dict[str, Any]) -> None:
        if seg["start_frame"] != self.frame_cursor:
            raise ValueError("分段时间轴不连续")
        if self.current is not None:
            self.remove(self.current)
            self.current = None
        group, meta = self.build_visual(visual, seg)
        self.add(group)
        if visual.get("type") != "scene" and group.width > 12.2:
            group.scale_to_fit_width(12.2)
        if visual.get("type") != "scene" and group.height > 6.6:
            group.scale_to_fit_height(6.6)
        self.current = group
        vtype = str(visual.get("type") or "talking_text")
        if vtype == "scene":
            diagram = meta["diagram"]
            frames = seg["frame_count"]
            if frames >= 2:
                # Manim samples 0..N-1. Map the last actual frame to the final
                # pose, consuming exactly the existing audio slot, no extra hold.
                self.play(UpdateFromAlphaFunc(diagram.nodes, lambda _, alpha: diagram.update(min(1., alpha*frames/(frames-1))),
                                              rate_func=linear), run_time=(frames-.0001)/self.fps)
                self.frame_cursor += frames
            else:
                diagram.update(1.)
                self.wait_to_frame(seg["end_frame"])
            self.diagram_program = diagram.program
        elif vtype == "talking_text" and seg.get("words") and meta.get("karaoke_mobs"):
            self.karaoke(meta["karaoke_mobs"], seg)
        elif vtype == "quiz":
            reveal = round(seg["frame_count"] * float(visual.get("reveal_at", .55)))
            self.wait_to_frame(seg["start_frame"] + min(reveal, seg["frame_count"] - 1))
            if meta.get("answer_mob") is not None:
                meta["answer_mob"].set_opacity(1)
            self.wait_to_frame(seg["end_frame"])
        else:
            # The entrance consumes frames from this segment's actual audio slot,
            # not extra time added before it. Remaining frames hold the explanation.
            frames = min(round(self.fps * .4), seg["frame_count"] // 5)
            if frames >= 2 and seg["start_frame"] > 0:
                self.remove(group)
                self.play(FadeIn(group, shift=UP * .12), run_time=(frames - .0001) / self.fps)
                self.frame_cursor += frames
            self.wait_to_frame(seg["end_frame"])
        if vtype != "scene":
            self.diagram_program = None

    def wait_to_frame(self, target: int) -> None:
        frames = target - self.frame_cursor
        if frames < 0:
            raise ValueError("视觉动作超出段落时间轴")
        if frames:
            # arange(0, duration, 1/fps) must emit exactly `frames` samples;
            # the epsilon avoids an extra frame from floating-point rounding.
            self.wait((frames - .0001) / self.fps, frozen_frame=False)
            self.frame_cursor = target

    def karaoke(self, targets: list[Mobject], seg: dict[str, Any]) -> None:
        for i, word in enumerate(seg["words"]):
            target = min(seg["end_frame"] - 1, seg["start_frame"] + round(word["start"] * self.fps))
            self.wait_to_frame(max(target, self.frame_cursor))
            if i < len(targets):
                targets[i].set_color(self.accent)
        self.wait_to_frame(seg["end_frame"])

    def build_visual(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        vtype = str(visual.get("type") or "talking_text")
        if vtype == "scene":
            diagram = Diagram(self, visual, getattr(self, "diagram_program", None))
            return diagram.group, {"diagram": diagram}
        builder = {
            "title": self.v_title,
            "talking_text": self.v_talking_text,
            "bullets": self.v_bullets,
            "formula": self.v_formula,
            "steps": self.v_steps,
            "fraction_pies": self.v_fraction_pies,
            "number_line": self.v_number_line,
            "compare": self.v_compare,
            "geometry": self.v_geometry,
            "quiz": self.v_quiz,
            "table": self.v_table,
            "bar_model": self.v_bar_model,
        }.get(vtype)
        if builder is None:
            raise ValueError(f"未支持的 visual.type: {vtype}; 未退化为文字页")
        return builder(visual, seg)

    def heading(self, text: str | None) -> Text | None:
        if not text:
            return None
        return self.txt(str(text), size=28, color=self.primary).to_edge(UP, buff=0.45)

    def _with_heading(self, heading: Text | None, body: Mobject, buff: float = 0.7) -> VGroup:
        if heading:
            body.next_to(heading, DOWN, buff=buff)
            return VGroup(heading, body)
        body.move_to(ORIGIN)
        return VGroup(body)

    def v_title(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        title, _ = self._word_paragraph([], str(visual.get("title") or self.lesson.get("title") or "课题"), font_size=48)
        block = VGroup(title)
        if visual.get("subtitle"):
            import re
            # Keep separate sentences readable on the opening page instead of
            # shrinking the entire question into one long subtitle.
            question = re.sub(r"(?<=[。！？])(?=\S)", "\n", str(visual["subtitle"]))
            subtitle, _ = self._word_paragraph([], question, font_size=32)
            subtitle.next_to(title, DOWN, buff=0.45)
            block.add(subtitle)
        block.move_to(ORIGIN)
        return VGroup(block), {}

    def v_talking_text(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        heading = self.heading(visual.get("heading"))
        words = seg.get("words") or []
        narration = str(seg.get("narration") or "")
        body, karaoke_mobs = self._word_paragraph(words, narration, font_size=34)
        group = self._with_heading(heading, body, buff=0.6)
        return group, {"karaoke_mobs": karaoke_mobs}

    def v_bullets(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        heading = self.heading(visual.get("heading"))
        items = [str(x) for x in (visual.get("items") or [])] or ["…"]
        rows = VGroup()
        for i, item in enumerate(items, start=1):
            mark = self.txt(f"{i}.", size=32, color=self.accent)
            text = self.txt(item, size=32)
            text.next_to(mark, RIGHT, buff=0.25)
            rows.add(VGroup(mark, text))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.38)
        if heading:
            rows.next_to(heading, DOWN, buff=0.55).align_to(heading, LEFT)
            group = VGroup(heading, rows).to_edge(LEFT, buff=0.9)
        else:
            rows.move_to(ORIGIN)
            group = VGroup(rows)
        return group, {}

    def v_formula(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        heading = self.heading(visual.get("heading"))
        lines = [str(x) for x in (visual.get("lines") or [seg.get("narration", "")])]
        mobs = VGroup(
            *[
                self.txt(line, size=44, color=self.accent if i == len(lines) - 1 else self.fg)
                for i, line in enumerate(lines)
            ]
        )
        mobs.arrange(DOWN, buff=0.4)
        return self._with_heading(heading, mobs), {}

    def v_steps(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        visual = {**visual, "heading": visual.get("heading") or "步骤"}
        return self.v_bullets(visual, seg)

    def v_fraction_pies(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        heading = self.heading(visual.get("heading"))
        pies = VGroup()
        for item in visual.get("items") or []:
            pies.add(self._pie(int(item.get("n", 1)), int(item.get("d", 2)), str(item.get("label") or "")))
        pies.arrange(RIGHT, buff=0.9)
        return self._with_heading(heading, pies), {}

    def _pie(self, n: int, d: int, label: str) -> VGroup:
        d = max(d, 1)
        n = min(max(n, 0), d)
        radius = 1.15
        pieces = VGroup()
        angle = TAU / d
        for i in range(d):
            filled = i < n
            sector = AnnularSector(
                inner_radius=0,
                outer_radius=radius,
                angle=angle,
                start_angle=PI / 2 - i * angle,
                color=self.primary if filled else self.muted,
                fill_opacity=0.9 if filled else 0.18,
                stroke_color=self.fg,
                stroke_width=2,
            )
            pieces.add(sector)
        caption = self.txt(label or f"{n}/{d}", size=28)
        caption.next_to(pieces, DOWN, buff=0.25)
        return VGroup(pieces, caption)

    def v_number_line(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        heading = self.heading(visual.get("heading"))
        lo = float(visual.get("min", 0))
        hi = float(visual.get("max", 10))
        step = float(visual.get("step", 1))
        line = NumberLine(
            x_range=[lo, hi, step],
            length=10,
            include_numbers=False,
            color=self.fg,
            decimal_number_config={"color": self.fg},
        )
        marks = VGroup()
        # NumberLine's default labels use MathTex. Draw Text labels instead so
        # this lesson runtime does not silently acquire a LaTeX dependency.
        for index in range(int((hi - lo) / step) + 1):
            value = lo + index * step
            label = self.txt(f"{value:g}", size=22)
            label.next_to(line.n2p(value), DOWN, buff=.15)
            marks.add(label)
        for mark in visual.get("marks") or []:
            value = float(mark.get("value", 0))
            dot = Dot(line.n2p(value), color=self.accent, radius=0.12)
            lab = self.txt(str(mark.get("label") or str(value)), size=24, color=self.accent)
            lab.next_to(dot, UP, buff=0.2)
            marks.add(VGroup(dot, lab))
        body = VGroup(line, marks)
        return self._with_heading(heading, body, buff=1.0), {}

    def v_compare(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        heading = self.heading(visual.get("heading"))
        left = self._card(visual.get("left") or {})
        right = self._card(visual.get("right") or {})
        vs = self.txt("VS", size=28, color=self.accent)
        row = VGroup(left, vs, right).arrange(RIGHT, buff=0.5)
        return self._with_heading(heading, row), {}

    def _card(self, data: dict[str, Any]) -> VGroup:
        box = RoundedRectangle(width=4.4, height=3.2, corner_radius=0.15, color=self.primary, fill_opacity=0.12)
        title = self.txt(str(data.get("title") or " "), size=36, color=self.accent)
        body = self.txt(str(data.get("body") or " "), size=24, color=self.fg)
        if body.width > 3.8:
            body.width = 3.8
        col = VGroup(title, body).arrange(DOWN, buff=0.35)
        col.move_to(box)
        return VGroup(box, col)

    def v_geometry(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        heading = self.heading(visual.get("caption") or visual.get("heading"))
        shape = str(visual.get("shape") or "triangle")
        labels = [str(x) for x in (visual.get("labels") or [])]
        if shape == "circle":
            geom = Circle(radius=1.6, color=self.primary, stroke_width=6, fill_opacity=0)
        elif shape == "rectangle":
            geom = Rectangle(width=4.2, height=2.4, color=self.primary, stroke_width=6, fill_opacity=0)
        else:
            geom = Polygon(
                [-2, -1.2, 0],
                [2, -1.2, 0],
                [-2, 1.6, 0],
                color=self.primary,
                stroke_width=6,
                fill_opacity=0,
            )
        labeled = VGroup(geom)
        if labels:
            # Manim synthesizes get_* attributes, so hasattr(get_vertices)
            # incorrectly succeeds for Circle even though it has no vertices.
            # Circles use boundary anchors; polygons keep their real vertices.
            if shape == "circle":
                points = [geom.get_top(), geom.get_right(), geom.get_bottom(), geom.get_left()]
                directions = [UP, RIGHT, DOWN, LEFT]
            else:
                points = geom.get_vertices()
                directions = [UP if i == 2 else DOWN for i in range(len(points))]
            for i, name in enumerate(labels[: len(points)]):
                labeled.add(
                    self.txt(name, size=28, color=self.accent).next_to(
                        points[i], directions[i], buff=0.15
                    )
                )
        return self._with_heading(heading, labeled, buff=0.6), {}

    def v_quiz(self, visual: dict[str, Any], seg: dict[str, Any]) -> tuple[VGroup, dict[str, Any]]:
        q = self.txt(str(visual.get("question") or "想一想？"), size=40)
        hint = self.txt("先自己算一算", size=24, color=self.muted)
        ans = self.txt(str(visual.get("answer") or " "), size=48, color=self.accent)
        ans.set_opacity(0)
        hint.next_to(q, DOWN, buff=0.4)
        ans.next_to(hint, DOWN, buff=0.7)
        return VGroup(q, hint, ans), {"answer_mob": ans}

    def v_table(self, visual, seg):
        heading = self.heading(visual.get("heading"))
        data = [visual["columns"], *visual["rows"]]
        rows = VGroup()
        width = 10.5 / len(visual["columns"])
        for i, row in enumerate(data):
            cells = VGroup()
            for text in row:
                box = Rectangle(width=width, height=.65, color=self.primary,
                                fill_color=self.primary, fill_opacity=.18 if i == 0 else .04)
                label = self.txt(text or " ", size=25, color=self.accent if i == 0 else self.fg)
                if label.width > width - .2:
                    label.scale_to_fit_width(width - .2)
                cells.add(VGroup(box, label.move_to(box)))
            rows.add(cells.arrange(RIGHT, buff=0))
        rows.arrange(DOWN, buff=0)
        return self._with_heading(heading, rows, buff=.45), {}

    def v_bar_model(self, visual, seg):
        heading = self.heading(visual.get("heading"))
        maximum = max(sum(p["value"] for p in row["parts"]) for row in visual["rows"])
        rows = VGroup()
        for row in visual["rows"]:
            parts = VGroup()
            for index, part in enumerate(row["parts"]):
                width = 8 * part["value"] / maximum
                box = Rectangle(width=width, height=.7, color=self.primary if index % 2 == 0 else self.accent,
                                fill_opacity=.2)
                label = self.txt(part["label"] or " ", size=26)
                if label.width > width - .08:
                    label.scale_to_fit_width(max(.03, width - .08))
                parts.add(VGroup(box, label.move_to(box)))
            parts.arrange(RIGHT, buff=0)
            label = self.txt(row["label"] or " ", size=25)
            label.next_to(parts, LEFT, buff=.3)
            rows.add(VGroup(label, parts))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=.6)
        return self._with_heading(heading, rows), {}

    def _word_paragraph(
        self,
        words: list[dict[str, Any]],
        fallback: str,
        font_size: int,
    ) -> tuple[VGroup, list[Mobject]]:
        tokens = [str(w.get("text") or "") for w in words if str(w.get("text") or "").strip()]
        if not tokens:
            # Wrap narration before fitting: a long single line was unreadably small.
            import textwrap
            wrapped = "\n".join(line for paragraph in fallback.splitlines() for line in textwrap.wrap(paragraph, width=23))
            body = self.txt(wrapped, size=font_size)
            body.width = min(body.width, 11.5)
            return VGroup(body), []
        mobs = [self.txt(tok, size=font_size) for tok in tokens]
        left, top = -6.0, 1.6
        x, y = left, top
        max_right = 6.0
        line_h = 0.62
        for mob in mobs:
            if x + mob.width > max_right:
                x = left
                y -= line_h
            mob.move_to([x + mob.width / 2, y, 0])
            x += mob.width + 0.08
        return VGroup(*mobs), mobs
