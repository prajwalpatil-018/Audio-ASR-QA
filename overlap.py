"""Overlap wall time divided by summed speaker speech time, times 100."""
import argparse
from collections import defaultdict
from common import add_inputs, load, merge, output, run, seconds


def calculate(speakers):
    if not 2 <= len(speakers) <= 8:
        raise ValueError("Overlap thresholds require 2-8 participants.")
    events = defaultdict(int)
    total = 0.0
    for spans in speakers.values():
        total += seconds(spans)
        for start, end in merge(spans):
            events[start] += 1
            events[end] -= 1
    if total <= 0:
        raise ValueError("Total speech is zero; overlap ratio is undefined.")
    active = 0
    previous = 0.0
    overlap = union = 0.0
    for time, delta in sorted(events.items()):
        union += (time - previous) if active >= 1 else 0
        overlap += (time - previous) if active >= 2 else 0
        active += delta
        previous = time
    ratio = overlap / total * 100
    minimum = 5 if len(speakers) <= 3 else 10
    return {"speaker_count": len(speakers), "total_speaker_speech_s": total,
            "speech_union_s": union, "overlap_s": overlap, "overlap_ratio_pct": ratio,
            "minimum_exclusive_pct": minimum, "status": "PASS" if ratio > minimum else "FAIL"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_inputs(parser)
    args = parser.parse_args()
    output(calculate(load(args.seglst_files)), args.output_csv)


if __name__ == "__main__":
    run(main)
