"""Density = speaker speech / sum of all speaker speech * 100."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
from common import add_inputs, load, output, run, seconds

RANGES = {2: (25, 75), 3: (16.67, 66.67), 4: (12.5, 50),
          5: (10, 40), 6: (8.33, 33.33), 7: (7.14, 28.57), 8: (6.25, 25)}


def calculate(speakers):
    if len(speakers) not in RANGES:
        raise ValueError("Density requires 2-8 participants, including silent speakers.")
    times = {speaker: seconds(spans) for speaker, spans in speakers.items()}
    total = sum(times.values())
    if total <= 0:
        raise ValueError("Total speech is zero; density is undefined.")
    low, high = RANGES[len(speakers)]
    rows = []
    for speaker, duration in sorted(times.items()):
        share = float((Decimal(str(duration)) / Decimal(str(total)) * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP))
        rows.append({"Speaker": speaker, "Density PASS/FAIL": "PASS" if low <= share <= high else "FAIL",
                     "Speech Minutes": duration / 60, "Speech Seconds": duration,
                     "Density %": share, "Min Density %": low, "Max Density %": high})
    return {"speaker_count": len(times), "total_speech_s": total,
            "status": "PASS" if all(r["Density PASS/FAIL"] == "PASS" for r in rows) else "FAIL",
            "speakers": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_inputs(parser)
    args = parser.parse_args()
    result = calculate(load(args.seglst_files))
    output(result, args.output_csv, result["speakers"])


if __name__ == "__main__":
    run(main)
