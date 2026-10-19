"""Timing-based monologue runs; explicit is_backchannel=true rows are ignored."""
import argparse
import math
from common import add_inputs, load, merge, output, run


def subtract(spans, interruptions):
    result = []
    for start, end in spans:
        cursor = start
        for left, right in interruptions:
            if right <= cursor:
                continue
            if left >= end:
                break
            if left > cursor:
                result.append((cursor, left))
            cursor = max(cursor, right)
            if cursor >= end:
                break
        if cursor < end:
            result.append((cursor, end))
    return result


def calculate(speakers, bridge_gap=2.0, limit=60.0):
    if not speakers:
        raise ValueError("No speakers supplied.")
    if not all(math.isfinite(v) and v >= 0 for v in (bridge_gap, limit)):
        raise ValueError("Gap and limit must be finite and non-negative.")
    runs = []
    for speaker, spans in speakers.items():
        interruptions = merge([span for other, values in speakers.items() if other != speaker for span in values])
        for start, end in subtract(merge(spans, bridge_gap), interruptions):
            runs.append({"speaker": speaker, "start_s": start, "end_s": end,
                         "duration_s": end - start, "over_limit": end - start > limit})
    runs.sort(key=lambda row: (row["start_s"], row["speaker"]))
    violations = [row for row in runs if row["over_limit"]]
    return {"method": "timing_only_with_explicit_backchannel_labels", "bridge_gap_s": bridge_gap,
            "limit_s": limit, "longest_monologue_s": max((r["duration_s"] for r in runs), default=0),
            "over_limit_count": len(violations), "status": "FAIL" if violations else "PASS",
            "violations": violations, "runs": runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_inputs(parser)
    parser.add_argument("--bridge-gap", type=float, default=2.0)
    parser.add_argument("--limit", type=float, default=60.0)
    args = parser.parse_args()
    result = calculate(load(args.seglst_files, ignore_backchannels=True), args.bridge_gap, args.limit)
    output(result, args.output_csv, result["runs"] or [{"speaker": "", "start_s": None,
           "end_s": None, "duration_s": 0, "over_limit": False}])


if __name__ == "__main__":
    run(main)
