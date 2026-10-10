"""Actual Manim vector objects, no rendering/model stubs."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manim import tempconfig
from manim_lesson import LessonScene
from scene_visual import Diagram
from util import pick_cjk_font
from scene_fixtures import lesson_fixture
from test_scene_motion import visual_fixture


class SceneRenderingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.enterContext(tempconfig({"media_dir":self.temp.name,"disable_caching":True}))
        self.scene = LessonScene()
        self.scene.font = pick_cjk_font(None)
        self.scene.fg,self.scene.primary,self.scene.accent,self.scene.muted = "#F8FAFC","#38BDF8","#FBBF24","#94A3B8"

    def test_all_illustrations_fit_and_change_geometry(self):
        previous = None
        for segment in lesson_fixture()["segments"]:
            visual = segment["visual"]
            diagram = Diagram(self.scene,visual,previous)
            original = {key:body.get_center().copy() for key,body in diagram.bodies.items()}
            diagram.update(.55)
            self.assertTrue(any((diagram.bodies[key].get_center()!=point).any() for key,point in original.items()))
            self.assertLessEqual(diagram.group.width,14)
            self.assertLessEqual(diagram.group.height,8)
            previous = diagram.program

    def test_hidden_objects_and_labels_reappear_and_fills_are_preserved(self):
        visual = visual_fixture()
        visual["objects"][0]["fill"] = .25
        diagram = Diagram(self.scene,visual)
        self.assertAlmostEqual(diagram.bodies["left"].get_fill_opacity(),.25)
        self.assertTrue(all(p.get_fill_opacity()==0 for p in diagram.bodies["answer"].family_members_with_points()))
        diagram.update(1)
        self.assertTrue(any(p.get_fill_opacity()>0 for p in diagram.bodies["answer"].family_members_with_points()))
        self.assertAlmostEqual(diagram.bodies["left"].get_fill_opacity(),.25)
        self.assertAlmostEqual(diagram.bodies["left"].get_center()[0],0)
        self.assertLess(diagram.labels["left"].get_top()[1],diagram.bodies["left"].get_bottom()[1])

    def test_unsupported_visual_never_falls_back_to_narration(self):
        with self.assertRaises(ValueError): self.scene.build_visual({"type":"unsupported"},{"narration":"not a fallback"})


if __name__=="__main__": unittest.main()
