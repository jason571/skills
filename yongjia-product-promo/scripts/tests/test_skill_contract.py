"""Regression checks for the narrated-video Skill's callable-tool contract."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SkillContractTests(unittest.TestCase):
    def test_only_narrated_chain_is_executable(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        start = skill.index("## 制作")
        workflow = skill[start:]
        for name in (
            "media-workflow-prepare_narrated_video",
            "model-synthesize_speech",
            "media-workflow-render_narrated_video",
        ):
            self.assertIn(name, workflow)
        self.assertIn("不要调用 `minimax-h3-mcp-generate_video`", workflow)
        self.assertIn("mode=replace", workflow)
        self.assertIn("只读 `minimax-h3-mcp-list_video_models`", skill)
        self.assertNotIn('"duration_seconds": 30', skill)

    def test_machine_workflow_excludes_direct_paid_generation(self):
        workflow = json.loads((ROOT / "tool-workflow.json").read_text(encoding="utf-8"))
        self.assertEqual(workflow["version"], 1)
        stages = workflow["stages"]
        self.assertEqual(stages[0]["advance_on_success"], "media-workflow-prepare_narrated_video")
        self.assertIn("model-synthesize_speech", stages[1]["tools"])
        self.assertIn("media-workflow-render_narrated_video", stages[1]["tools"])
        self.assertTrue(all("generate_video" not in tool for stage in stages for tool in stage["tools"]))


if __name__ == "__main__":
    unittest.main()
