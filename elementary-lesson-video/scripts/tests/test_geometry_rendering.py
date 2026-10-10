"""Real Manim objects: no mocked dynamic getters, LLM or TTS calls."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
HAS_MANIM = importlib.util.find_spec("manim") is not None
if HAS_MANIM:
    from manim import DOWN, LEFT, RIGHT, UP, tempconfig
    from manim_lesson import LessonScene
    from util import pick_cjk_font


@unittest.skipUnless(HAS_MANIM, "requires the lesson-renderer Manim runtime")
class GeometryRenderingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lesson-geometry-")
        self.addCleanup(self.temp.cleanup)
        self.enterContext(tempconfig({"media_dir": self.temp.name, "disable_caching": True}))
        self.scene = LessonScene()
        self.scene.font = pick_cjk_font(None)
        self.scene.primary = "#38BDF8"
        self.scene.accent = "#FBBF24"
        self.scene.fg = "#F8FAFC"

    def test_all_supported_shapes_with_and_without_labels(self):
        for shape, count in (("circle", 4), ("rectangle", 4), ("triangle", 3)):
            for size in range(count + 1):
                with self.subTest(shape=shape, labels=size):
                    labels = list("ABCD")[:size]
                    group, meta = self.scene.v_geometry({"shape": shape, "labels": labels}, {})
                    labeled = group[0]
                    self.assertEqual(len(labeled), size + 1)
                    self.assertEqual([label.text for label in labeled[1:]], labels)
                    self.assertEqual(meta, {})

    def test_circle_labels_use_four_outward_boundary_positions(self):
        group, _ = self.scene.v_geometry({"shape": "circle", "labels": ["上", "右", "下", "左"]}, {})
        circle, *labels = group[0]
        for label, direction in zip(labels, (UP, RIGHT, DOWN, LEFT)):
            distance = (label.get_center() - circle.get_center()).dot(direction)
            self.assertGreater(distance, circle.radius)
        self.assertGreater(labels[0].get_bottom()[1], circle.get_top()[1])
        self.assertGreater(labels[1].get_left()[0], circle.get_right()[0])
        self.assertLess(labels[2].get_top()[1], circle.get_bottom()[1])
        self.assertLess(labels[3].get_right()[0], circle.get_left()[0])


if __name__ == "__main__":
    unittest.main()
