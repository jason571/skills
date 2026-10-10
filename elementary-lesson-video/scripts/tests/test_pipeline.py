from __future__ import annotations

import copy
import json
import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lesson import speech_requests, validate_lesson
from mux import check_video
from timeline import SUPPORTED_FPS, assemble_audio, build_timeline, write_srt
from tts import prepare_audio, validate_cached_audio, validate_words
from util import save_json, sha256_file, text_digest
from util import run_cmd


def lesson_fixture():
    return {"title": "减法", "question": "八减三是多少？", "grade": "小学二年级", "subject": "数学",
            "segments": [{"id": "s01", "narration": "原来有八只。", "visual": {"type": "title", "title": "8"}},
                         {"id": "s02", "narration": "拿走三只，还剩五只。", "visual": {"type": "formula", "lines": ["8 - 3 = 5"]}}]}


def create_audio(path, samples=48123, rate=48000, frequency=440):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(b"".join(struct.pack("<h", round(3000 * math.sin(2 * math.pi * frequency * i / rate))) for i in range(samples)))


def create_manifest(root, lesson, counts=None):
    records = []
    counts = counts or [48123 + i * 73 for i in range(len(lesson["segments"]))]
    for i, (seg, count) in enumerate(zip(lesson["segments"], counts)):
        path = root / "inputs" / f"{seg['id']}.wav"
        create_audio(path, count, frequency=440 + i * 110)
        records.append({"id": seg["id"], "narration_sha256": text_digest(seg["narration"]),
                        "artifact": {"local_path": str(path), "sha256": sha256_file(path)}})
    target = root / "audio_manifest.json"
    save_json(target, {"schema_version": 1, "segments": records})
    return target


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="study-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lesson = lesson_fixture()
        self.out = self.root / "out"

    def prepare(self):
        return prepare_audio(self.lesson, create_manifest(self.root, self.lesson), self.out)

    def test_requests_follow_current_tts_schema_without_second_provider(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("No provider calls")):
            requests = speech_requests(self.lesson)
        self.assertEqual(len(requests["segments"]), 2)
        self.assertEqual(set(requests["segments"][0]["arguments"]), {"text", "filename"})
        self.assertEqual(requests["segments"][0]["arguments"]["text"], self.lesson["segments"][0]["narration"])
        self.assertEqual(requests["segments"][0]["narration_sha256"], text_digest(self.lesson["segments"][0]["narration"]))

    def test_all_six_grades_and_existing_examples(self):
        for grade in "一二三四五六":
            self.lesson["grade"] = f"小学{grade}年级"
            validate_lesson(self.lesson)
        for path in Path(__file__).resolve().parents[2].joinpath("examples").glob("*.json"):
            validate_lesson(json.loads(path.read_text()))

    def test_grade_does_not_accept_unrelated_substrings(self):
        self.lesson["grade"] = "初中一年级"
        with self.assertRaises(ValueError):
            validate_lesson(self.lesson)

    def test_unsafe_or_duplicate_segment_ids_rejected(self):
        for bad in ("../x", "/tmp/x", "s01"):
            altered = copy.deepcopy(self.lesson)
            altered["segments"][1]["id"] = bad
            with self.assertRaises(ValueError):
                validate_lesson(altered)

    def test_unknown_visual_fails_before_tts(self):
        self.lesson["segments"][0]["visual"]["type"] = "invented_scene"
        with self.assertRaises(ValueError):
            speech_requests(self.lesson)

    def test_bad_number_line_and_fraction_rejected(self):
        for visual in ({"type": "number_line", "step": 0}, {"type": "fraction_pies", "items": [{"n": 1, "d": 0}]}):
            self.lesson["segments"][0]["visual"] = visual
            with self.assertRaises(ValueError):
                validate_lesson(self.lesson)

    def test_real_decoding_has_exact_sample_counts(self):
        raw = self.prepare()
        self.assertEqual([s["samples"] for s in raw["segments"]], [48123, 48196])

    def test_real_mp3_input_is_decoded_instead_of_concatenating_container_duration(self):
        manifest_path = create_manifest(self.root, self.lesson)
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest["segments"]:
            source = Path(entry["artifact"]["local_path"])
            mp3 = source.with_suffix(".mp3")
            proc = run_cmd(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(source),
                            "-ar", "24000", "-c:a", "libmp3lame", str(mp3)], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            entry["artifact"] = {"local_path": str(mp3), "sha256": sha256_file(mp3)}
        save_json(manifest_path, manifest)
        raw = prepare_audio(self.lesson, manifest_path, self.out)
        for seg, expected in zip(raw["segments"], [48123, 48196]):
            self.assertLessEqual(abs(seg["samples"] - expected), 2)
        assemble_audio(build_timeline(raw), self.out)

    def test_preparation_rejects_damaged_decoded_cache_without_tts(self):
        manifest = create_manifest(self.root, self.lesson)
        raw = prepare_audio(self.lesson, manifest, self.out)
        create_audio(self.out / raw["segments"][0]["audio"], 48123, frequency=1000)
        with self.assertRaisesRegex(ValueError, "缓存已损坏"):
            prepare_audio(self.lesson, manifest, self.out)

    def test_no_accumulated_drift_at_all_supported_fps(self):
        for fps in SUPPORTED_FPS:
            raw = {"segments": [{"id": str(i), "samples": 48001 + i, "sample_rate": 48000} for i in range(1000)]}
            timeline = build_timeline(raw, fps)
            for previous, seg in zip([None] + timeline["segments"], timeline["segments"]):
                self.assertEqual(seg["start_sample"] * fps, seg["start_frame"] * 48000)
                self.assertLess(seg["silence_samples"], 48000 // fps)
                self.assertEqual(seg["slot_samples"], seg["samples"] + seg["silence_samples"])
                if previous:
                    self.assertEqual(seg["start_frame"], previous["end_frame"])
            self.assertEqual(timeline["total_samples"] * fps, timeline["total_frames"] * 48000)

    def test_assembled_audio_contains_exact_pcm_then_subframe_silence(self):
        raw = self.prepare()
        timeline = build_timeline(raw)
        output = assemble_audio(timeline, self.out)
        with wave.open(str(output), "rb") as stream:
            self.assertEqual(stream.getnframes(), timeline["total_samples"])
            for seg in timeline["segments"]:
                with wave.open(str(self.out / seg["audio"]), "rb") as source:
                    self.assertEqual(stream.readframes(seg["samples"]), source.readframes(seg["samples"]))
                self.assertEqual(stream.readframes(seg["silence_samples"]), b"\0\0" * seg["silence_samples"])

    def test_partial_audio_does_not_silently_skip_a_segment(self):
        path = create_manifest(self.root, self.lesson)
        manifest = json.loads(path.read_text())
        manifest["segments"].pop()
        save_json(path, manifest)
        with self.assertRaises(ValueError):
            prepare_audio(self.lesson, path, self.out)

    def test_manifest_wrong_text_and_wrong_file_hash_rejected(self):
        path = create_manifest(self.root, self.lesson)
        manifest = json.loads(path.read_text())
        for field in ("narration_sha256", "sha256"):
            bad = copy.deepcopy(manifest)
            obj = bad["segments"][0] if field == "narration_sha256" else bad["segments"][0]["artifact"]
            obj[field] = "0" * 64
            save_json(path, bad)
            with self.assertRaises(ValueError):
                prepare_audio(self.lesson, path, self.out)

    def test_changed_narration_rejects_skip_tts(self):
        raw = self.prepare()
        self.lesson["segments"][0]["narration"] += "修改后的话。"
        with self.assertRaisesRegex(ValueError, "讲解稿已改变"):
            validate_cached_audio(self.lesson, raw, self.out)

    def test_visual_only_change_reuses_audio(self):
        raw = self.prepare()
        self.lesson["segments"][0]["visual"]["title"] = "改画面"
        validate_cached_audio(self.lesson, raw, self.out)

    def test_corrupt_cached_audio_is_not_used(self):
        raw = self.prepare()
        create_audio(self.out / raw["segments"][0]["audio"], 48123, frequency=1000)
        with self.assertRaisesRegex(ValueError, "损坏"):
            validate_cached_audio(self.lesson, raw, self.out)

    def test_reordered_segments_reject_cached_order(self):
        raw = self.prepare()
        self.lesson["segments"].reverse()
        with self.assertRaises(ValueError):
            validate_cached_audio(self.lesson, raw, self.out)

    def test_word_zero_is_valid_and_units_are_never_guessed(self):
        self.assertEqual(validate_words([{"text": "你好", "start_sec": 0, "end_sec": .2}], 48000)[0]["start"], 0)
        for word in ({"text": "x", "start": 0, "end": 200},
                     {"text": "x", "start_sec": float("nan"), "end_sec": .2},
                     {"text": "x", "start_sec": 0, "end_sec": 2}):
            with self.assertRaises(ValueError):
                validate_words([word], 48000)

    def test_absent_words_are_not_fabricated(self):
        self.assertTrue(all(not s["words"] for s in self.prepare()["segments"]))

    def test_render_cache_validates_word_timestamps(self):
        raw = self.prepare()
        raw["segments"][0]["words"] = [{"text": "bad", "start": -1, "duration": 1}]
        with self.assertRaises(ValueError):
            validate_cached_audio(self.lesson, raw, self.out)

    def test_subtitle_stops_at_speech_end_before_padding(self):
        timeline = build_timeline(self.prepare())
        output = self.out / "subtitles.srt"
        write_srt(timeline, output)
        self.assertIn("00:00:00,000 --> 00:00:01,003", output.read_text())

    def test_wrong_render_frame_count_is_not_hidden_by_padding(self):
        timeline = build_timeline(self.prepare())
        stream = {"r_frame_rate": "30/1", "nb_frames": str(timeline["total_frames"] + 1), "duration": timeline["total_duration_sec"]}
        with self.assertRaisesRegex(ValueError, "帧数"):
            check_video(stream, timeline)


if __name__ == "__main__":
    unittest.main()
