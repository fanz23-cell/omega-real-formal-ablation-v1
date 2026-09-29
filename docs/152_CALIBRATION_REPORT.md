# 152. Calibration Report (Stage A) — NOT Scientific Evidence

Per directive section 26: calibration validates provider wiring, schema compliance, cost,
prompt rendering, and fairness — it is explicitly NOT pooled into confirmatory statistics.
9 cases (1 per preregistered geometry, scale=10), 27 real API calls, seed pool `CAL_v1`
(disjoint from the confirmatory pool `CONFIRM_v1` — never reused).

## A real bug found and fixed (disclosed, not hidden)

First calibration attempt: **0% on every single metric for every arm**, including
`conflict_preserved=0.0` across B0/B1/C — a strong signal something was structurally broken,
not a real null result (the whole design predicts near-ceiling `conflict_preserved` for
B1/C at minimum, since every case is a genuine conflict and B1/C both receive an explicit
typed conflict label). Root cause: `run_confirmatory.py` called bare `json.loads(resp["text"])`
with no fallback; the model reliably wraps its JSON answer in markdown ` ```json ` fences
despite the system prompt explicitly forbidding it, so 100% of parses failed silently into
`PARSE_FAILURE`. Inspection of the raw completions showed the model's actual answers were
correct (e.g. case `3efc6989bd7c2e95`, B1 and C both answered exactly the gold rubric).
Fixed by adding the same tolerant direct-parse-then-regex-extract fallback the prior
long-horizon benchmark's `real_run.py` already used. Re-ran calibration clean after the fix;
`run_confirmatory.py` was re-frozen (doc 151) before the confirmatory run.

## Results after the fix (n=9, wide CIs expected and not concerning — this is calibration)

| arm | decision_correct | wrong_confident_physical_claim | conflict_preserved |
|---|---|---|---|
| B0 | 66.7% (6/9) | 22.2% (2/9) | 77.8% (7/9) |
| B1 | 77.8% (7/9) | 0.0% (0/9) | 100% (9/9) |
| C  | 77.8% (7/9) | 0.0% (0/9) | 100% (9/9) |

B1 vs C: 0 discordant pairs at this tiny sample — consistent with either a genuinely narrow
C-vs-B1 effect (matching the prior benchmark's own finding that the mechanism's value is
concentrated in a small slice of cases) or simply insufficient sample size to see it yet;
not distinguishable at n=9, which is exactly why the confirmatory run is powered for n=189
pooled pairs (doc 150), not left at calibration scale.

## Wiring/schema/cost validation (the actual purpose of this stage)

- Real ingestion, fairness check, real Omega/MeTTa advisory computation: 9/9 succeeded.
- Schema compliance after the parser fix: 27/27 clean or tolerantly-extracted JSON, 0 hard
  parse failures.
- Cost: 27 calls, well within the ~$1.50-2.50 total budget projected in doc 150.
- Retry policy exercised: none needed (no transport errors this round).

**CALIBRATION_VERDICT: wiring confirmed healthy after one real fix. Proceeding to
confirmatory run under the re-frozen manifest (doc 151).**
