import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import load
from density import calculate as density
from overlap import calculate as overlap
from monologue import calculate as monologue


class MetricsTests(unittest.TestCase):
    def test_density_merges_and_preserves_cross_speaker_speech(self):
        result = density({"a": [(0, 10), (5, 15)], "b": [(0, 5)]})
        self.assertEqual(result["total_speech_s"], 20)
        self.assertEqual([r["Density %"] for r in result["speakers"]], [75, 25])
        self.assertEqual(result["status"], "PASS")

    def test_density_rounded_three_speaker_boundary_and_silent_speaker(self):
        self.assertEqual(density({"a": [(0, 1)], "b": [(0, 1)], "c": [(0, 4)]})["status"], "PASS")
        self.assertEqual(density({"a": [(0, 1)], "b": []})["status"], "FAIL")

    def test_overlap_triple_counted_once(self):
        result = overlap({"a": [(0, 10)], "b": [(5, 15)], "c": [(5, 10)]})
        self.assertEqual(result["overlap_s"], 5)
        self.assertEqual(result["overlap_ratio_pct"], 20)
        self.assertEqual(overlap({"a": [(0, 5)], "b": [(5, 10)]})["overlap_s"], 0)

    def test_monologue_real_longest_and_strict_limit(self):
        result = monologue({"a": [(0, 60)], "b": []})
        self.assertEqual(result["longest_monologue_s"], 60)
        self.assertEqual(result["over_limit_count"], 0)
        result = monologue({"a": [(0, 70)], "b": [(30, 31)]})
        self.assertEqual(result["longest_monologue_s"], 39)
        self.assertEqual(monologue({"a": [(0, 61)], "b": []})["over_limit_count"], 1)

    def test_explicit_backchannel_ignored_only_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "speaker.seglst.json"
            path.write_text(json.dumps([{"speaker": "b", "start": 30, "end": 31, "is_backchannel": True}]))
            self.assertEqual(load([path]), {"b": [(30, 31)]})
            self.assertEqual(load([path], ignore_backchannels=True), {"b": []})

    def test_snr_known_levels_and_no_noise(self):
        import numpy as np
        import soundfile as sf
        from snr_silence import calculate
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "test.wav"
            seglst = Path(directory) / "test.seglst.json"
            seglst.write_text(json.dumps([{"start": 0, "end": 1}]))
            sf.write(audio, np.r_[np.full(8000, .1), np.full(8000, .01)], 8000, subtype="FLOAT")
            result = calculate(audio, seglst)
            self.assertAlmostEqual(result["snr_db"], 20, places=5)
            self.assertAlmostEqual(result["silence_floor_dbfs"], -40, places=5)
            sf.write(audio, np.r_[np.full(8000, .1), np.zeros(8000)], 8000, subtype="FLOAT")
            result = calculate(audio, seglst)
            self.assertEqual(result["status"], "ZERO_NOISE_ENERGY")
            self.assertIsNone(result["snr_db"])


if __name__ == "__main__":
    unittest.main()
