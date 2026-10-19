# Audio metrics after seglst creation

Four independent command-line scripts, with a shared `common.py`. Python 3.10+
is required. No VAD inference, transcript generation, model downloads, or audio
uploads happen here. Existing seglst timestamps are the inputs.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Only SNR/silence requires numpy and soundfile. The other scripts use Python's
standard library. Run commands from this folder.

## Input

Use files for ONE conversation, on the same synchronized timeline. Supply one
version per speaker; do not combine original and approved copies of the same
annotations. Each speaker must have a unique label across the conversation.
Different files with the same speaker label are combined.

Accepted JSON: a list of rows, or `{"segments": [...]}`. Times must be seconds,
not Silero sample indices. Generate Silero timestamps with `return_seconds=True`
or divide sample indices by the VAD sample rate before creating the seglst.

```json
[
  {"speaker": "alice@example.com", "start_time": "1.20", "end_time": "4.80"},
  {"speaker": "alice@example.com", "start_time": "6.00", "end_time": "6.50", "is_backchannel": true}
]
```

`start`/`end` are also accepted. If `speaker` is absent, the filename identifies
the speaker, with `.seglst.json` and `_approved` removed. Include an empty list
file named for any silent participant so the speaker count remains correct.
Malformed timestamps cause an error. Overlapping intervals within a speaker
are merged; gaps are not filled except for the configured monologue gap.

## 1. Density

```bash
python density.py /path/to/conversation/*.seglst.json --output-csv outputs/density.csv
```

Density (%) = (speaker speech seconds / SUM of all speaker speech seconds) * 100.
Simultaneous speech counts for each speaker. Recording length is not the
denominator. Inclusive ranges are compared after rounding density to two decimal
places (half up), matching the supplied policy table.

| Speakers | Min % | Max % |
| --- | --- | --- |
| 2 | 25.00 | 75.00 |
| 3 | 16.67 | 66.67 |
| 4 | 12.50 | 50.00 |
| 5 | 10.00 | 40.00 |
| 6 | 8.33 | 33.33 |
| 7 | 7.14 | 28.57 |
| 8 | 6.25 | 25.00 |

Conversation PASS requires every participant to pass. Zero total speech is an error.

## 2. SNR and silence floor

```bash
python snr_silence.py --audio /path/to/alice.wav --seglst /path/to/alice.seglst.json --output-csv outputs/alice_audio.csv
```

Use the matching individual speaker WAV and seglst. The script measures original
samples at the native sample rate, with no resampling, gates, or concatenation.
Speech is inside the intervals; non-speech is their complement across the WAV.
Digital samples are normalized to full scale by soundfile.

- Speech level = 10 * log10(mean squared speech samples).
- Silence floor dBFS = 10 * log10(mean squared non-speech samples).
- Estimated SNR dB = speech level dBFS - silence floor dBFS.

Stereo uses mean channel power to avoid phase cancellation. Blocks are processed
to limit memory. Missing speech/non-speech or zero power produces a descriptive
status and null for undefined/non-finite scores, not a fabricated numeric floor.
Out-of-range timestamps are rejected (one sample tolerance).

This is a speech-to-non-speech level estimate, not a clean-reference SNR. Bleed,
unlabelled speech, processing and digital-silence padding can alter the estimate.
No SNR or silence PASS/FAIL policy is assumed. Native-rate/stereo handling and
the timestamp source can cause differences from the older mono/resampled VAD app.

## 3. Overlap ratio

```bash
python overlap.py /path/to/conversation/*.seglst.json --output-csv outputs/overlap.csv
```

Overlap (%) = (wall time with at least two active speakers / SUM of all speaker
speech seconds) * 100. Triple overlap is counted once in the numerator. Also
reports the speech union duration for clarity. Touching segment endpoints do not
create overlap. PASS requires strictly >5% for 2-3 speakers, >10% for 4-8 speakers.
The unrounded ratio is used for the verdict.

## 4. Monologues

```bash
python monologue.py /path/to/conversation/*.seglst.json --bridge-gap 2 --limit 60 --output-csv outputs/monologue.csv
```

This follows the existing interval approach: join a speaker's speech across
pauses up to `--bridge-gap` seconds, then subtract other speakers' non-backchannel
intervals. It flags resulting runs strictly longer than 60 seconds, reports all
runs in CSV and the actual longest run even if no violation exists. Duration is
elapsed run time including bridged pauses. Change `--bridge-gap` to match your
pause policy; the default is 2 seconds.

Only rows explicitly labelled `"is_backchannel": true` are ignored for this
check. Density and overlap still include those rows. VAD alone cannot tell a
backchannel from a meaningful interruption, so unlabelled VAD seglst gives a
timing-only estimate. It cannot fully enforce a semantic word-based monologue
definition. Other speakers' intervals break a run irrespective of how brief
they are. Non-speech events must be removed upstream if they should not count.

## Output and verification

Every script prints JSON and can export an Excel-compatible UTF-8 CSV. Audio
and private annotations are not included in this repository folder.

```bash
python -m unittest discover -s tests -v
```
