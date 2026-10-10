"""Trusted vector illustration rendering. No eval, files, downloads or models."""
import numpy as np
from manim import (Arrow, Circle, DOWN, Ellipse, Line, ORIGIN, Polygon, Rectangle,
                   Star, Triangle, VGroup, VMobject)

from scene_contract import AnimatedScene, SceneProgram


def wrapped(text, columns):
    return "\n".join(line[i:i+columns] for line in text.splitlines() for i in range(0, len(line), columns))


class Diagram:
    def __init__(self, scene, visual, previous=None):
        self.program = SceneProgram(AnimatedScene.model_validate(visual), previous)
        self.bodies = {}
        self.labels = {}
        self.templates = {}
        self.nodes = VGroup()
        for key, definition in self.program.objects.items():
            body = self.shape(scene, definition)
            self.templates[key] = body.copy()
            self.bodies[key] = body
            self.nodes.add(body)
            if definition["label"]:
                label = scene.txt(wrapped(definition["label"], 10), size=22, color=scene.fg)
                self.labels[key] = label
                self.nodes.add(label)
        heading = scene.heading(wrapped(visual.get("heading", ""), 30))
        caption = scene.txt(wrapped(visual.get("caption", ""), 40), size=22, color=scene.muted) if visual.get("caption") else None
        if caption is not None:
            caption.to_edge(DOWN, buff=.3)
        self.group = VGroup(self.nodes, *([heading] if heading is not None else []), *([caption] if caption is not None else []))
        self.update(0.)

    @staticmethod
    def shape(scene, definition):
        kind = definition["kind"]
        width, height = definition["size"]
        if kind == "text":
            body = scene.txt(definition["text"], size=32)
            if body.width > width:
                body.scale_to_fit_width(width)
            if body.height > height:
                body.scale_to_fit_height(height)
        elif kind in {"line", "arrow"}:
            endpoints = [np.array([-width/2, 0., 0.]), np.array([width/2, 0., 0.])]
            body = Arrow(*endpoints, buff=0, stroke_width=4, max_tip_length_to_length_ratio=.15) if kind == "arrow" else Line(*endpoints, stroke_width=4)
        elif kind in {"path", "polygon"}:
            points = [np.array([*point, 0.]) for point in definition["points"]]
            body = Polygon(*points) if kind == "polygon" else VMobject().set_points_as_corners(points)
        else:
            body = {"circle": Circle, "ellipse": Ellipse, "rectangle": Rectangle,
                    "triangle": Triangle, "star": Star}[kind]()
            body.stretch_to_fit_width(width).stretch_to_fit_height(height)
        body.move_to(ORIGIN).set_color(definition["color"])
        if kind not in {"text", "line", "arrow", "path"}:
            body.set_fill(definition["color"], opacity=definition["fill"]).set_stroke(width=3)
        return body

    def update(self, fraction):
        poses = self.program.pose(fraction)
        for key, pose in poses.items():
            body = self.bodies[key]
            body.become(self.templates[key])
            body.scale(pose["scale"]).rotate(pose["angle"]).move_to([*pose["at"], 0.])
            body.set_color(pose["color"])
            # set_opacity would destroy the shape's chosen fill/stroke ratio.
            for part in body.family_members_with_points():
                part.set_fill(opacity=part.get_fill_opacity()*pose["opacity"])
                part.set_stroke(opacity=part.get_stroke_opacity()*pose["opacity"])
            if key in self.labels:
                label = self.labels[key]
                label.next_to(body, DOWN, buff=.12).set_opacity(pose["opacity"])
        return poses
