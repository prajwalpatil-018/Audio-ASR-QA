"""Shared seglst loading and interval operations. All timestamps are seconds."""
import csv
import json
import math
from pathlib import Path


def merge(intervals, gap=0.0):
    result = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if result and start <= result[-1][1] + gap:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def seconds(intervals):
    return sum(end - start for start, end in merge(intervals))


def load(paths, ignore_backchannels=False):
    speakers = {}
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate input file.")
    for path in resolved:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("segments") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError(f"{path}: expected a list or an object containing segments.")
        fallback = path.name.split(".seglst", 1)[0].removesuffix("_approved")
        if not rows:
            speakers.setdefault(fallback, [])
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"{path}: row {index} must be an object.")
            speaker = str(row.get("speaker") or fallback)
            spans = speakers.setdefault(speaker, [])
            try:
                start = float(row.get("start_time", row.get("start")))
                end = float(row.get("end_time", row.get("end")))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}: invalid timestamps in row {index}.") from exc
            if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
                raise ValueError(f"{path}: invalid interval in row {index}.")
            if ignore_backchannels and row.get("is_backchannel") is True:
                continue
            spans.append((start, end))
    return {speaker: merge(spans) for speaker, spans in speakers.items()}


def output(result, csv_path=None, rows=None):
    print(json.dumps(result, indent=2, allow_nan=False))
    if csv_path:
        target = Path(csv_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        records = rows if rows is not None else [result]
        if not records:
            raise ValueError("No rows to export.")
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)


def add_inputs(parser):
    parser.add_argument("seglst_files", nargs="+", help="Seglst files for ONE synchronized conversation")
    parser.add_argument("--output-csv")


def run(main):
    try:
        main()
    except (ValueError, OSError) as exc:
        raise SystemExit(f"Error: {exc}") from exc
