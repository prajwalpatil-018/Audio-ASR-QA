"""Measure speech/non-speech RMS on a WAV using an existing seglst mask."""
import argparse
import math
import numpy as np
import soundfile as sf
from common import load, merge, output, run


def calculate(audio_path, seglst_path):
    spans = merge([span for group in load([seglst_path]).values() for span in group])
    speech_energy = silence_energy = 0.0
    speech_samples = silence_samples = 0
    with sf.SoundFile(audio_path) as audio:
        sr, frames = audio.samplerate, len(audio)
        if any(end > frames / sr + 1 / sr for _, end in spans):
            raise ValueError("Seglst extends past the audio. Check alignment and timestamps.")
        sample_spans = [(min(frames, round(a * sr)), min(frames, round(b * sr))) for a, b in spans]
        offset = 0
        index = 0
        for block in audio.blocks(blocksize=sr * 10, dtype="float64", always_2d=True):
            # Average channel powers rather than waveforms to avoid phase cancellation.
            power = np.mean(block * block, axis=1)
            if not np.isfinite(power).all():
                raise ValueError("Audio contains non-finite samples.")
            mask = np.zeros(len(block), dtype=bool)
            while index < len(sample_spans) and sample_spans[index][1] <= offset:
                index += 1
            cursor = index
            while cursor < len(sample_spans) and sample_spans[cursor][0] < offset + len(block):
                start, end = sample_spans[cursor]
                mask[max(0, start - offset):min(len(block), end - offset)] = True
                cursor += 1
            speech_energy += float(power[mask].sum())
            silence_energy += float(power[~mask].sum())
            speech_samples += int(mask.sum())
            silence_samples += int((~mask).sum())
            offset += len(block)
    def level(energy, count):
        return 10 * math.log10(energy / count) if count and energy > 0 else None
    speech_db = level(speech_energy, speech_samples)
    silence_db = level(silence_energy, silence_samples)
    status = ("NO_SPEECH" if not speech_samples else "NO_NON_SPEECH" if not silence_samples
              else "ZERO_SPEECH_ENERGY" if speech_energy == 0 else
              "ZERO_NOISE_ENERGY" if silence_energy == 0 else "OK")
    return {"audio": str(audio_path), "sample_rate": sr, "speech_s": speech_samples / sr,
            "non_speech_s": silence_samples / sr, "speech_level_dbfs": speech_db,
            "silence_floor_dbfs": silence_db,
            "snr_db": speech_db - silence_db if speech_db is not None and silence_db is not None else None,
            "status": status}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--seglst", required=True)
    parser.add_argument("--output-csv")
    args = parser.parse_args()
    output(calculate(args.audio, args.seglst), args.output_csv)


if __name__ == "__main__":
    run(main)
