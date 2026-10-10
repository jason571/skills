"""Shared, data-only animation contract and deterministic motion evaluator.

The MCP imports this administrator-installed module for its live schema. Each
job snapshots the same module for validation/rendering; no caller code or URLs.
"""
from __future__ import annotations

import copy
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Coordinate = Annotated[float, Field(strict=True, ge=-40, le=40)]
Point = Annotated[list[Coordinate], Field(min_length=2, max_length=2)]
Size = Annotated[list[Annotated[float, Field(strict=True, gt=0, le=12)]], Field(min_length=2, max_length=2)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,47}$")]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Ratio = Annotated[float, Field(strict=True, ge=0, le=1)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SceneObject(Model):
    id: Identifier
    kind: Literal["circle", "ellipse", "rectangle", "triangle", "star", "line", "arrow", "path", "polygon", "text"]
    at: Point = Field(default_factory=lambda: [0., 0.], description="Center in the diagram area: x -5.5..5.5, y -2.2..2.2. Heading/caption stay outside it.")
    size: Size = Field(default_factory=lambda: [1., 1.], description="Width/height. Paths and polygons use their point coordinates instead.")
    color: Color = "#38BDF8"
    fill: Ratio = .35
    label: Annotated[str, Field(max_length=32)] = ""
    text: Annotated[str, Field(max_length=80)] = ""
    visible: bool = True
    points: Annotated[list[Point], Field(max_length=24)] = Field(default_factory=list)

    @model_validator(mode="after")
    def shape_data(self):
        if self.kind == "text" and not self.text.strip():
            raise ValueError(f"object {self.id}: text requires non-empty text")
        minimum = 3 if self.kind == "polygon" else 2
        if self.kind in {"path", "polygon"}:
            if len(self.points) < minimum or len({tuple(p) for p in self.points}) < minimum:
                raise ValueError(f"object {self.id}: {self.kind} needs {minimum} distinct points")
        elif self.points:
            raise ValueError(f"object {self.id}: points are only for path/polygon")
        return self


class SceneGroup(Model):
    id: Identifier
    members: Annotated[list[Identifier], Field(min_length=1, max_length=32)]


class ActionBase(Model):
    target: Annotated[str, Field(min_length=1, max_length=48)] = Field(description="An object/group ID, or * for all diagram objects (not heading/caption).")
    start: Ratio = Field(default=0., description="Fraction of this segment's actual TTS slot; not guessed seconds or word timestamps.")
    end: Ratio = Field(default=1., description="End fraction of this segment, default 1. Also applies to show/hide fades, not instantaneous events. Set explicit non-overlapping intervals for actions affecting the same object and channel.")
    ease: Literal["linear", "smooth"] = "smooth"

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("action requires start < end")
        return self


class Move(ActionBase):
    op: Literal["move"]
    by: Point


class Scale(ActionBase):
    op: Literal["scale"]
    factor: Annotated[float, Field(strict=True, ge=.1, le=8)]
    about: Point | None = None


class Rotate(ActionBase):
    op: Literal["rotate"]
    degrees: Annotated[float, Field(strict=True, ge=-1440, le=1440)]
    about: Point | None = None


class FollowPath(ActionBase):
    op: Literal["follow_path"]
    points: Annotated[list[Point], Field(min_length=2, max_length=24, description="Offsets from the current center, beginning at [0,0]. Piecewise-linear path.")]

    @model_validator(mode="after")
    def origin(self):
        if self.points[0] != [0., 0.] or all(p == self.points[0] for p in self.points):
            raise ValueError("follow_path starts at [0,0] and must contain movement")
        return self


class Visibility(ActionBase):
    op: Literal["show", "hide"]


class Highlight(ActionBase):
    op: Literal["highlight"]
    color: Color = "#FBBF24"


Action = Annotated[Move | Scale | Rotate | FollowPath | Visibility | Highlight, Field(discriminator="op")]


class AnimatedScene(Model):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, json_schema_extra={
        "allOf": [{
            "if": {"properties": {"continue_previous": {"const": True}}, "required": ["continue_previous"]},
            "then": {"properties": {"objects": {"maxItems": 0}, "groups": {"maxItems": 0}}},
            "else": {"required": ["objects"], "properties": {"objects": {"minItems": 1}}},
        }],
    })
    type: Literal["scene"]
    heading: Annotated[str, Field(max_length=80)] = ""
    caption: Annotated[str, Field(max_length=100)] = ""
    continue_previous: bool = Field(default=False, description="Reuse objects/groups and their exact final poses from the immediately preceding scene segment. Omit objects/groups in this case.")
    objects: Annotated[list[SceneObject], Field(max_length=32)] = Field(default_factory=list, description="New scene only. Predeclare later objects with visible=false, then reveal them in a continuation; omit this array when continue_previous=true.")
    groups: Annotated[list[SceneGroup], Field(max_length=12)] = Field(default_factory=list, description="New scene only: define named groups of existing object IDs. Omit when continue_previous=true.")
    actions: Annotated[list[Action], Field(max_length=32)] = Field(default_factory=list)

    @model_validator(mode="after")
    def identities(self):
        if self.continue_previous:
            if self.objects or self.groups:
                raise ValueError("continue_previous reuses existing objects/groups; do not redefine them")
            return self
        if not self.objects:
            raise ValueError("a new scene requires objects")
        ids = [o.id for o in self.objects]
        group_ids = [g.id for g in self.groups]
        if len(set(ids + group_ids)) != len(ids + group_ids):
            raise ValueError("object and group IDs must be unique")
        for group in self.groups:
            if len(set(group.members)) != len(group.members) or not set(group.members) <= set(ids):
                raise ValueError(f"group {group.id}: members must be unique existing object IDs")
        return self


def path_offset(points, progress):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    distance = progress * sum(lengths)
    for a, b, length in zip(points, points[1:], lengths):
        if length and distance <= length:
            ratio = distance / length
            return [a[i] + (b[i] - a[i]) * ratio for i in range(2)]
        distance -= length
    return list(points[-1])


def blend(a, b, fraction):
    values = [round(int(a[i:i+2], 16) * (1-fraction) + int(b[i:i+2], 16) * fraction) for i in (1, 3, 5)]
    return "#" + "".join(f"{value:02x}" for value in values)


class SceneConflict(ValueError):
    """Exact conflict evidence; never choose new timing or mutate authored data."""
    def __init__(self, channel, objects, actions, segment=None):
        self.channel, self.objects, self.actions, self.segment = channel, objects, actions, segment
        intervals = "; ".join(
            f"actions[{a['index']}] {a['op']} target={a['target']} [{a['start']:g}, {a['end']:g}]"
            + (f" (defaulted: {', '.join(a['defaulted'])})" if a['defaulted'] else "")
            for a in actions)
        prefix = f"segments[{segment}].visual: " if segment is not None else ""
        super().__init__(prefix + f"overlapping {channel} actions affect {', '.join(objects)}: {intervals}. "
                         "Sequence these intervals; retain targets and unrelated content. show/hide are fades, not instant events.")


def action_conflicts(visual, objects, groups, segment=None):
    """Enumerate independent interval conflicts without executing scene poses."""
    occupied, conflicts = [], []
    for index, action in sorted(enumerate(visual.actions), key=lambda pair: pair[1].start):
        ids = set(objects) if action.target == "*" else set(groups.get(action.target, [action.target]))
        if not ids <= set(objects):
            continue  # Execution validation reports missing IDs separately.
        channel = "opacity" if action.op in {"show", "hide"} else "color" if action.op == "highlight" else "transform"
        evidence = {"index": index, "op": action.op, "target": action.target,
                    "start": action.start, "end": action.end,
                    "defaulted": [key for key in ("start", "end") if key not in action.model_fields_set]}
        for earlier_ids, earlier_channel, earlier in occupied:
            if channel == earlier_channel and ids & earlier_ids and max(action.start, earlier["start"]) < min(action.end, earlier["end"]):
                conflicts.append(SceneConflict(channel, sorted(ids & earlier_ids), [earlier, evidence], segment))
        occupied.append((ids, channel, evidence))
    return conflicts


def collect_scene_conflicts(visuals):
    """Keep identity continuity for diagnostics even when another segment is invalid."""
    objects, groups = None, {}
    conflicts = []
    for index, raw in enumerate(visuals):
        if not isinstance(raw, dict) or raw.get("type") != "scene":
            objects, groups = None, {}
            continue
        try:
            visual = AnimatedScene.model_validate(raw)
        except ValueError:
            objects, groups = None, {}
            continue
        if not visual.continue_previous:
            objects = {obj.id for obj in visual.objects}
            groups = {group.id: group.members for group in visual.groups}
        if objects is not None:
            conflicts.extend(action_conflicts(visual, objects, groups, index))
    return conflicts


class SceneProgram:
    """All poses derive from data + normalized time, never incremental dt drift."""
    def __init__(self, visual: AnimatedScene, previous: SceneProgram | None = None):
        self.visual = visual
        if visual.continue_previous:
            if previous is None:
                raise ValueError("continue_previous requires an immediately preceding scene")
            self.objects = previous.objects
            self.groups = previous.groups
            self.initial = previous.pose(1.)
        else:
            self.objects = {obj.id: obj.model_dump() for obj in visual.objects}
            self.groups = {g.id: g.members for g in visual.groups}
            self.initial = {key: {"at": list(obj["at"]), "scale": 1., "angle": 0., "opacity": float(obj["visible"]), "color": obj["color"]} for key, obj in self.objects.items()}
        self.compiled = []
        conflicts = action_conflicts(visual, self.objects, self.groups)
        if conflicts:
            raise conflicts[0]
        for action in sorted(visual.actions, key=lambda action: action.start):
            value = action.model_dump()
            ids = list(self.objects) if action.target == "*" else self.groups.get(action.target, [action.target])
            if not set(ids) <= self.objects.keys():
                raise ValueError(f"action target {action.target!r} not found; use an existing object/group ID")
            base = self.pose(action.start)
            center = [(min(base[key]["at"][i] for key in ids) + max(base[key]["at"][i] for key in ids)) / 2 for i in range(2)]
            self.compiled.append((value, ids, base, value.get("about") or center))
            if any(not .025 <= p["scale"] <= 32 or any(abs(x) > 1000 for x in p["at"]) for p in self.pose(action.end).values()):
                raise ValueError("cumulative scene transforms exceed safe coordinate/scale limits")

    def pose(self, fraction):
        state = copy.deepcopy(self.initial)
        for action, ids, base, center in self.compiled:
            if fraction < action["start"]:
                continue
            t = min(1., max(0., (fraction-action["start"])/(action["end"]-action["start"])))
            if action["ease"] == "smooth":
                t = t*t*(3-2*t)
            op = action["op"]
            for key in ids:
                original, current = base[key], state[key]
                if op in {"move", "follow_path"}:
                    offset = [v*t for v in action["by"]] if op == "move" else path_offset(action["points"], t)
                    current["at"] = [original["at"][i] + offset[i] for i in range(2)]
                elif op == "scale":
                    factor = 1 + (action["factor"]-1)*t
                    current["at"] = [center[i]+(original["at"][i]-center[i])*factor for i in range(2)]
                    current["scale"] = original["scale"] * factor
                elif op == "rotate":
                    angle = math.radians(action["degrees"]*t)
                    x, y = (original["at"][i]-center[i] for i in range(2))
                    current["at"] = [center[0]+x*math.cos(angle)-y*math.sin(angle), center[1]+x*math.sin(angle)+y*math.cos(angle)]
                    current["angle"] = original["angle"] + angle
                elif op in {"show", "hide"}:
                    current["opacity"] = original["opacity"] + (float(op == "show")-original["opacity"])*t
                elif op == "highlight":
                    current["color"] = blend(original["color"], action["color"], math.sin(math.pi*t)**2)
        return state


def validate_scene_chain(visuals):
    previous = None
    for index, value in enumerate(visuals):
        if isinstance(value, AnimatedScene):
            scene = value
        elif isinstance(value, dict) and value.get("type") == "scene":
            scene = AnimatedScene.model_validate(value)
        else:
            previous = None
            continue
        try:
            previous = SceneProgram(scene, previous)
        except SceneConflict as error:
            raise SceneConflict(error.channel, error.objects, error.actions, index) from error
        except ValueError as error:
            raise ValueError(f"segments[{index}].visual: {error}") from error
