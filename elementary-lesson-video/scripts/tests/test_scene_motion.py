"""Contract, motion and continuity checks independent of a specific subject."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scene_contract import AnimatedScene, SceneConflict, SceneProgram, validate_scene_chain


def visual_fixture():
    return {"type":"scene", "objects":[
        {"id":"left", "kind":"circle", "at":[-2,0], "label":"甲"},
        {"id":"right", "kind":"rectangle", "at":[2,0], "label":"乙"},
        {"id":"answer", "kind":"text", "text":"观察变化", "at":[0,-2], "size":[4,.6], "visible":False}],
        "groups":[{"id":"pair", "members":["left","right"]}],
        "actions":[{"op":"move", "target":"left", "by":[2,0], "start":0, "end":.5, "ease":"linear"},
                   {"op":"show", "target":"answer", "start":.5, "end":1}]}


class SceneMotionTests(unittest.TestCase):
    def test_conflict_reports_original_indices_defaults_and_effective_objects(self):
        for earlier_target, later_target, affected in (("answer", "answer", ["answer"]),
                ("pair", "left", ["left"]), ("*", "right", ["right"])):
            value = visual_fixture()
            # Input order intentionally differs from execution order.
            value["actions"] = [{"op":"hide", "target":later_target, "start":.45},
                                {"op":"show", "target":earlier_target, "start":.2}]
            original = copy.deepcopy(value)
            with self.assertRaises(SceneConflict) as caught:
                validate_scene_chain([{"type":"title"}, value])
            error = caught.exception
            self.assertEqual(error.segment, 1)
            self.assertEqual(error.objects, affected)
            self.assertEqual([a["index"] for a in error.actions], [1, 0])
            self.assertEqual(error.actions[0]["defaulted"], ["end"])
            self.assertEqual(error.actions[0]["end"], 1)
            self.assertEqual(value, original)

    def test_adjacent_fades_and_independent_channels_remain_valid(self):
        value = visual_fixture()
        value["actions"] = [{"op":"show", "target":"answer", "start":.2, "end":.45},
            {"op":"hide", "target":"answer", "start":.45, "end":1},
            {"op":"move", "target":"answer", "by":[1,0]},
            {"op":"highlight", "target":"answer"},
            {"op":"hide", "target":"left"}]
        program = SceneProgram(AnimatedScene.model_validate(value))
        self.assertEqual(program.pose(.2)["answer"]["opacity"], 0)
        self.assertEqual(program.pose(.45)["answer"]["opacity"], 1)
        self.assertEqual(program.pose(1)["answer"]["opacity"], 0)
        self.assertEqual(program.pose(1)["answer"]["at"], [1,-2])

    def test_motion_is_deterministic_and_continuation_starts_at_exact_final_pose(self):
        first = SceneProgram(AnimatedScene.model_validate(visual_fixture()))
        self.assertEqual(first.pose(0)["left"]["at"], [-2,0])
        self.assertEqual(first.pose(.25)["left"]["at"], [-1,0])
        self.assertEqual(first.pose(1)["left"]["at"], [0,0])
        self.assertEqual(first.pose(1)["answer"]["opacity"], 1)
        before = first.pose(.7)
        first.pose(.1)
        self.assertEqual(first.pose(.7), before)
        second = SceneProgram(AnimatedScene.model_validate({"type":"scene", "continue_previous":True,
            "actions":[{"op":"scale", "target":"pair", "factor":2, "about":[0,0]}]}), first)
        self.assertEqual(first.pose(1), second.pose(0))
        self.assertEqual(second.pose(1)["right"]["at"], [4,0])
        self.assertEqual(second.pose(1)["left"]["scale"], 2)

    def test_rotation_path_highlight_and_visibility_have_real_intermediate_states(self):
        value = visual_fixture()
        value["actions"] = [{"op":"rotate", "target":"right", "degrees":180, "about":[0,0], "ease":"linear"},
            {"op":"follow_path", "target":"left", "points":[[0,0],[0,1],[2,1]], "ease":"linear"},
            {"op":"highlight", "target":"right", "color":"#FF0000"},
            {"op":"hide", "target":"left"}]
        program = SceneProgram(AnimatedScene.model_validate(value))
        self.assertAlmostEqual(program.pose(.5)["right"]["at"][0], 0)
        self.assertAlmostEqual(program.pose(.5)["right"]["at"][1], 2)
        self.assertEqual(program.pose(.5)["right"]["color"], "#ff0000")
        self.assertEqual(program.pose(1)["right"]["color"], "#38bdf8")
        self.assertEqual(program.pose(1)["left"]["at"], [0,1])
        self.assertEqual(program.pose(1)["left"]["opacity"], 0)

    def test_every_shape_is_schema_native(self):
        for kind in ("circle","ellipse","rectangle","triangle","star","line","arrow","path","polygon","text"):
            obj = {"id":"item", "kind":kind}
            if kind in {"path","polygon"}: obj["points"] = [[-1,0],[1,0],[0,1]]
            if kind == "text": obj["text"] = "变化"
            SceneProgram(AnimatedScene.model_validate({"type":"scene","objects":[obj]}))

    def test_invalid_data_is_rejected_before_any_audio_request(self):
        mutations = [
            lambda v: v["objects"][0].update(code="import os"),
            lambda v: v["objects"][0].update(url="http://example/image.png"),
            lambda v: v["objects"][0].update(kind="invented"),
            lambda v: v["objects"][0].update(at=[float("nan"),0]),
            lambda v: v["objects"][1].update(id="left"),
            lambda v: v["groups"][0].update(members=["not_found"]),
            lambda v: v["actions"][0].update(target="not_found"),
            lambda v: v["actions"][0].update(by="[2,0]"),
            lambda v: v["actions"][0].update(start=.6, end=.5),
            lambda v: v["actions"].append({"op":"scale","target":"pair","factor":2}),
            lambda v: v.update(continue_previous=True),
        ]
        for mutate in mutations:
            value = visual_fixture()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                SceneProgram(AnimatedScene.model_validate(value))

    def test_continuation_cannot_cross_a_static_page_or_start_a_lesson(self):
        following = {"type":"scene", "continue_previous":True, "actions":[{"op":"move", "target":"left", "by":[1,0]}]}
        validate_scene_chain([visual_fixture(), following])
        for sequence in ([following], [visual_fixture(), {"type":"title"}, following]):
            with self.assertRaises(ValueError): validate_scene_chain(sequence)

    def test_large_intermediate_scale_is_rejected_even_if_later_reversed(self):
        value = visual_fixture()
        value["actions"] = [{"op":"scale", "target":"pair", "factor":8, "start":0,"end":.2},
            {"op":"scale", "target":"pair", "factor":8, "start":.2,"end":.4},
            {"op":"scale", "target":"pair", "factor":.125, "start":.4,"end":.6}]
        with self.assertRaises(ValueError): SceneProgram(AnimatedScene.model_validate(value))


if __name__ == "__main__":
    unittest.main()
