"""Offline regression: no model, TTS API, GPU generation or production writes."""
import copy
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import promo_media as media


def prompt(duration=30, mode="t2va"):
    cuts = []
    for index in range(1, 4):
        total_ms = round(duration * 1000 * index / 4)
        minute, rest = divmod(total_ms, 60000)
        second, ms = divmod(rest, 1000)
        cuts.append(f"[Shot {index + 1}] At {minute:02d}:{second:02d}.{ms:03d}, "
                    f"the camera cuts to another side of the fabric as a hand turns fold {index}.")
    body = ("integrated_multimodal_description: [Shot 1] Live-action macro photography, "
            "a hand unfolds blue fabric on a wooden table in soft window light. "
            + " ".join(cuts) + " Silent visuals throughout.\n\n"
            "overall_soundscape: N/A\n\nnon_diegetic_music: N/A")
    return media.I2VA_PREFIX + "\n\n" + body if mode == "i2va" else body


def manifest(duration=120):
    plan = media.plan_timeline(duration)
    for index, part in enumerate(plan["segments"]):
        mode = "i2va" if index else "t2va"
        part.update(input_mode=mode, prompt=prompt(part["duration_seconds"], mode),
                    narration="从一针一线，到衣着之间，近看材质，也看见用心。")
    return plan


class PlanTests(unittest.TestCase):
    def test_skill_uses_window_budget_and_local_narration_repair(self):
        skill = (Path(__file__).resolve().parents[2] / "SKILL.md").read_text()
        self.assertIn("recommended_max_characters", skill)
        self.assertIn("needs_narration_repair", skill)
        self.assertIn("只为 `required_narration_segment_ids` 各调用一次 TTS", skill)
        self.assertNotIn("每段四句对四镜，70–90 字", skill)

    def test_remote_timeline_uses_exact_urls_without_reading_or_importing_videos(self):
        plan = manifest()
        for i, segment in enumerate(plan["segments"]):
            segment.update(job_id=f"completed-{i}", generation_status="completed",
                video_url=f"https://video.example/{i}.mp4?signature=exact-{i}",
                narration_url=f"https://files.example/{i}.mp3?signature=exact-{i}",
                last_frame_url=f"https://video.example/{i}.png")
            if i: segment["first_frame_url"] = plan["segments"][i - 1]["last_frame_url"]
        audio = {"streams": [{"codec_type": "audio", "duration": "20"}]}
        original = copy.deepcopy(plan)
        with patch.object(media, "probe", return_value=audio) as probe:
            args = media.timeline_arguments(plan, Path("/tmp"))
            self.assertEqual(probe.call_count, 4)
            self.assertTrue(all(str(c.args[0]).endswith(".mp3") for c in probe.call_args_list))
        self.assertEqual(plan, original)
        self.assertEqual(set(args), {"segments"})
        for i, value in enumerate(args["segments"]):
            self.assertEqual(value, {"video_url": plan["segments"][i]["video_url"],
                "audio_url": plan["segments"][i]["narration_url"], "duration_seconds": 30, "audio_offset_seconds": 0})
        for field, bad in [("job_id", "completed-0"), ("generation_status", "failed"),
                           ("first_frame_url", "different"), ("video_url", "/local.mp4"),
                           ("narration_url", "https://user:secret@files.example/audio.mp3")]:
            broken = copy.deepcopy(plan)
            broken["segments"][1][field] = bad
            with patch.object(media, "probe", return_value=audio), self.assertRaises(ValueError):
                media.timeline_arguments(broken, Path("/tmp"))
        plan["voiceover"] = False
        with patch.object(media, "probe") as probe:
            silent = media.timeline_arguments(plan, Path("/tmp"))
            probe.assert_not_called()
            self.assertTrue(all("audio_url" not in s for s in silent["segments"]))

    def test_timeline_predeclares_import_destinations_without_claiming_media_exists(self):
        plan = media.plan_timeline(120)
        self.assertEqual(len(plan["segments"]), 4)
        for segment in plan["segments"]:
            self.assertEqual(segment["narration_path"], f"audio/{segment['id']}.mp3")
            self.assertEqual(segment["video_path"], f"video/{segment['id']}.mp4")
            self.assertNotIn("job_id", segment)
            self.assertNotIn("generation_status", segment)

    def test_missing_binding_is_not_misreported_as_absolute_path_or_probed(self):
        plan = manifest()
        del plan["segments"][0]["narration_path"]
        with patch.object(media, "probe") as probe:
            with self.assertRaisesRegex(ValueError, r"segment-001.narration_path: missing media binding"):
                media.check_manifest(plan, Path("/tmp"), audio_only=True)
            probe.assert_not_called()
        for path, message in [("/tmp/audio.mp3", "relative"), ("../escape.mp3", "leaves")]:
            plan["segments"][0]["narration_path"] = path
            with self.assertRaisesRegex(ValueError, "segment-001.narration_path:.*" + message):
                media.check_manifest(plan, Path("/tmp"), audio_only=True)
            with self.assertRaisesRegex(ValueError, "segment-001.narration_path:.*" + message):
                media.check_manifest(plan, Path("/tmp"), plan_only=True)

    def test_recorded_raw_newlines_recover_losslessly_with_one_prepare_call(self):
        original = (Path(__file__).parent / "fixtures/raw-newline-plan.json").read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), "d1fbce990cfde1e56f05e68a6bed83dc898a3e3ac6045f82dadae39d6d724f8d")
        with self.assertRaisesRegex(json.JSONDecodeError, "Invalid control character"):
            json.loads(original)
        intended = json.loads(original, strict=False)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "promo.json"
            path.write_bytes(original)
            result = media.prepare_plan(path)
            self.assertEqual(result["status"], "plan_ready")
            self.assertTrue(result["json_format_repaired"])
            self.assertEqual(result["normalized_segments"], [])
            self.assertEqual([s["shot_count"] for s in result["measurements"]], [4, 4, 4, 4])
            self.assertEqual(json.loads(path.read_bytes()), intended)
            self.assertEqual((path.parent / result["original_backup"]).read_bytes(), original)
            canonical = path.read_bytes()
            self.assertFalse(media.prepare_plan(path)["json_format_repaired"])
            self.assertEqual(path.read_bytes(), canonical)
            self.assertEqual(len(list(path.parent.glob("*.original-*.json"))), 1)

    def test_json_loader_preserves_exact_strings_without_general_unescaping(self):
        for value in ('中文\nline\r\nnext\tend', '"quote" and literal \\n C:\\new\\path'):
            encoded = json.dumps({"value": value}, ensure_ascii=False)
            self.assertEqual(media.load_plan_json(encoded), ({"value": value}, False))
            raw = encoded.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t") if "\n" in value else encoded
            restored, changed = media.load_plan_json(raw)
            self.assertEqual(restored, {"value": value})
            self.assertEqual(changed, raw != encoded)

    def test_json_loader_does_not_guess_structure_or_accept_ambiguous_values(self):
        inputs = ('{"value":"unclosed}', '{"value": 1 "missing": 2}',
                  '{"value":"raw\nline", "value": "duplicate"}',
                  '{"value":"\\q"}', '{"value":"raw\x00text"}',
                  '{"value":"raw\nline" "missing": 2}', '{"value":NaN}',
                  '{"value": Infinity}', '{"value":"raw\nline", "extra":-Infinity}', '{"value":1e10000}')
        for raw in inputs:
            with self.subTest(raw=repr(raw)), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "promo.json"
                original = raw.encode()
                path.write_bytes(original)
                with self.assertRaises(ValueError): media.prepare_plan(path)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(path.parent.iterdir()), [path])
        with self.assertRaisesRegex(ValueError, "512 KiB"):
            media.load_plan_json(b" " * (512 * 1024 + 1))

    def test_recorded_split_h3_plan_is_prepared_without_rewriting_creative_content(self):
        fixture = Path(__file__).parent / "fixtures/split-h3-plan.json"
        original = fixture.read_bytes()
        plan = json.loads(original)
        with self.assertRaisesRegex(ValueError, "three ordered text sections"):
            media.check_manifest(plan, fixture.parent, plan_only=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "promo.json"
            path.write_bytes(original)
            result = media.prepare_plan(path)
            self.assertEqual(result["status"], "plan_ready")
            self.assertEqual([s["shot_count"] for s in result["measurements"]], [4, 4, 4, 4])
            self.assertEqual((path.parent / result["original_backup"]).read_bytes(), original)
            fixed = json.loads(path.read_bytes())
            for before, after in zip(plan["segments"], fixed["segments"]):
                for key, value in before.items():
                    if key not in ("prompt", "overall_soundscape", "non_diegetic_music"):
                        self.assertEqual(after[key], value)
                visual = before["prompt"].replace("\\n\\nintegrated_multimodal_description:", "\n\nintegrated_multimodal_description:")
                self.assertEqual(after["prompt"], visual + "\n\noverall_soundscape: N/A\n\nnon_diegetic_music: N/A")
            stable = path.read_bytes()
            self.assertEqual(media.prepare_plan(path)["normalized_segments"], [])
            self.assertEqual(path.read_bytes(), stable)
            self.assertEqual(len(list(path.parent.glob("*.original-*.json"))), 1)

    def test_prepare_plan_rejects_conflict_or_missing_content_without_partial_writes(self):
        for change in ("missing", "conflict", "missing_shots", "late_conflict"):
            plan = manifest()
            # Earlier segments could be normalized, but failure anywhere must be atomic.
            plan["segments"][0]["prompt"] = plan["segments"][0]["prompt"].split("\n\noverall_soundscape:")[0]
            plan["segments"][0].update(overall_soundscape="N/A", non_diegetic_music="N/A")
            if change == "missing": del plan["segments"][0]["overall_soundscape"]
            elif change == "conflict": plan["segments"][1]["overall_soundscape"] = "music"
            elif change == "late_conflict": plan["segments"][-1]["non_diegetic_music"] = "music"
            else: plan["segments"][1]["prompt"] = plan["segments"][1]["prompt"].replace("[Shot 4]", "Another view:")
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "promo.json"
                original = json.dumps(plan).encode()
                path.write_bytes(original)
                with self.assertRaises(ValueError): media.prepare_plan(path)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(path.parent.iterdir()), [path])

    def test_prepare_plan_leaves_correct_plan_and_literal_prose_untouched(self):
        plan = manifest()
        plan["segments"][0]["prompt"] = plan["segments"][0]["prompt"].replace("Live-action", r"A sign displays C:\new. Live-action")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "promo.json"
            original = json.dumps(plan).encode()
            path.write_bytes(original)
            self.assertEqual(media.prepare_plan(path)["normalized_segments"], [])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_two_to_three_minutes_have_exact_coverage(self):
        for seconds, count in ((120, 4), (150, 5), (180, 6)):
            with self.subTest(seconds=seconds):
                plan = manifest(seconds)
                self.assertEqual([s["duration_seconds"] for s in plan["segments"]], [30] * count)
                report = media.check_manifest(plan, Path("/tmp"), plan_only=True)
                self.assertEqual(report["segment_count"], count)
                self.assertTrue(all(s["shot_count"] == 4 for s in report["measurements"]))

    def test_small_tail_redistributes_without_shortening(self):
        self.assertEqual([s["duration_seconds"] for s in media.plan_timeline(61)["segments"]],
                         [30, 26, 5])

    def test_impossible_or_invalid_timeline_is_rejected(self):
        for arguments in ((4,), (31, 30, 20), (120, 0, 5), (float("nan"),), (True,)):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                media.plan_timeline(*arguments)

    def test_less_than_four_shots_is_rejected(self):
        text = prompt().replace("[Shot 4]", "Another view:")
        with self.assertRaisesRegex(ValueError, "at least four"):
            media.check_h3_prompt(text, 30000)

    def test_invalid_shots_are_rejected(self):
        for text in (prompt().replace("00:15.000", "00:07.000"),
                     prompt().replace("00:22.500", "00:30.000"),
                     prompt().replace("[Shot 3]", "[Shot 7]"),
                     prompt().replace("[Shot 1] Live-action", "[Shot 1] At 00:00.000, Live-action"),
                     prompt().replace("overall_soundscape: N/A", "overall_soundscape: music"),
                     prompt().replace("non_diegetic_music: N/A", "")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                media.check_h3_prompt(text, 30000)

    def test_reference_mode_matches_official_prefix(self):
        self.assertEqual(media.check_h3_prompt(prompt(mode="i2va"), 30000, "i2va"), 4)
        for text, mode in ((prompt(), "i2va"), (prompt(mode="i2va"), "t2va")):
            with self.assertRaisesRegex(ValueError, "alignment prefix"):
                media.check_h3_prompt(text, 30000, mode)

    def test_invalid_manifest_cannot_pass_preflight(self):
        changes = (("target_duration_seconds", 150), ("segments", ["encoded object"]),
                   ("voiceover", "true"))
        for key, value in changes:
            plan = manifest()
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                media.check_manifest(plan, Path("/tmp"), plan_only=True)

    def test_missing_narration_or_reference_mode_is_rejected(self):
        for key, value in (("narration", ""), ("narration", {"text": "错误嵌套"}), ("input_mode", "t2va")):
            plan = manifest()
            plan["segments"][1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                media.check_manifest(plan, Path("/tmp"), plan_only=True)

    def test_paths_stay_within_workspace(self):
        for path in ("../outside.mp4", "/tmp/outside.mp4", "", None):
            with self.subTest(path=path), self.assertRaises(ValueError):
                media.local_path(Path("/tmp/task"), path)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="yongjia-promo-test-")
        cls.root = Path(cls.directory.name)
        # Synthetic moving video with a deliberately different original soundtrack.
        media.run_program(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                           "testsrc2=size=160x90:rate=24:duration=30", "-f", "lavfi", "-i",
                           "sine=frequency=200:sample_rate=48000:duration=30",
                           "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2",
                           "-c:a", "aac", str(cls.root / "fixture.mp4")])
        media.run_program(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                           "sine=frequency=800:sample_rate=48000:duration=20",
                           str(cls.root / "voice.wav")])
        cls.plan = manifest()
        for index, segment in enumerate(cls.plan["segments"]):
            segment.update(video_path="fixture.mp4", narration_path="voice.wav",
                           job_id=f"synthetic-job-{index}", generation_status="completed",
                           last_frame_url=f"https://fixture.invalid/frame-{index}.png")
            if index:
                segment["first_frame_url"] = cls.plan["segments"][index - 1]["last_frame_url"]

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_120_second_video_with_voiceover_and_originals_preserved(self):
        original = hashlib.sha256((self.root / "fixture.mp4").read_bytes()).hexdigest()
        result = media.assemble(self.plan, self.root, "spoken.mp4")
        self.assertEqual(result["status"], "assembled")
        self.assertAlmostEqual(result["duration_seconds"], 120, delta=0.062)
        self.assertTrue(result["has_narration"])
        info = media.probe(self.root / "spoken.mp4")
        self.assertEqual({s["codec_name"] for s in info["streams"]}, {"h264", "aac"})
        self.assertEqual(original, hashlib.sha256((self.root / "fixture.mp4").read_bytes()).hexdigest())
        # Decode a short interior slice: the 800 Hz narration replaces the original 200 Hz audio.
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "1", "-i",
                              str(self.root / "spoken.mp4"), "-t", "0.1", "-map", "0:a:0",
                              "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1"],
                             capture_output=True, check=True, timeout=30).stdout
        samples = struct.unpack(f"<{len(raw) // 2}h", raw)
        crossings = sum(a < 0 <= b for a, b in zip(samples, samples[1:]))
        self.assertAlmostEqual(crossings / (len(samples) / 48000), 800, delta=25)
        with self.assertRaisesRegex(ValueError, "already exists"):
            media.assemble(self.plan, self.root, "spoken.mp4")

    def test_incomplete_or_mismatched_inputs_stop_before_encoding(self):
        changes = (("generation_status", "failed"), ("job_id", "synthetic-job-0"),
                   ("first_frame_url", "https://fixture.invalid/wrong.png"),
                   ("narration_offset_seconds", 11), ("video_path", "missing.mp4"))
        for key, value in changes:
            plan = copy.deepcopy(self.plan)
            plan["segments"][1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                media.assemble(plan, self.root, "must-not-exist.mp4")
            self.assertFalse((self.root / "must-not-exist.mp4").exists())

    def test_short_clip_cannot_be_looped_to_fill_time(self):
        plan = copy.deepcopy(self.plan)
        plan["segments"][0]["duration_seconds"] = 31
        plan["max_clip_seconds"] = 31
        with self.assertRaisesRegex(ValueError, "no looping or freeze-fill"):
            media.check_manifest(plan, self.root)

    def test_silent_output_does_not_require_narration(self):
        plan = manifest(5)
        plan.update(voiceover=False)
        plan["segments"][0].update(video_path="fixture.mp4", job_id="synthetic-silent",
                                   generation_status="completed")
        result = media.assemble(plan, self.root, "silent.mp4")
        self.assertFalse(result["has_narration"])
        self.assertFalse(any(s["codec_type"] == "audio" for s in media.probe(self.root / "silent.mp4")["streams"]))


if __name__ == "__main__":
    unittest.main()
