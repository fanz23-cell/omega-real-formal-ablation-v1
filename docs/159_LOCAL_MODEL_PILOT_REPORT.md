# 159. Local Model Pilot — Qwen3.5-9B (Q4_K_M, CPU-only)

## Motivation

The confirmatory result (docs 153-156) used one model, `claude-sonnet-4-5-20250929`,
throughout — the governing directive's own "what this does not prove" section explicitly
flagged "whether a DIFFERENT LLM... would change this picture" as untested. The project owner
proposed a specific, well-formed hypothesis: a strong model may already have enough capability
to act correctly on a plain qualitative conflict label alone, making the real NAL numeric
output redundant — and a smaller, weaker model might show a measurable C-vs-B1 difference that
the strong model's own capability was masking.

## Scope (disclosed, not silent)

Only **scale=10** was run (63 cases: 9 preregistered geometries × 7 reps; 189 calls), not the
full 189-case/567-call design. At scale=1000, prompts run ~25-30K input tokens (the same size
that produced the $48.60 cost surprise with the paid API, doc 153); this model, running
CPU-only (the host's NVIDIA driver has a kernel-module/library version mismatch — 580.173.02
loaded vs 580.178 installed — fixable only by a reboot, which was not performed this round),
processes prompt tokens at ~35 tok/s. A single scale=1000 call would take ~12-14 minutes;
189 such calls would take 40+ hours. scale=10 alone gives full 9-geometry coverage at
~15-20s/call (actual: 63 cases in 608s of pure generation time, plus real wall-clock time lost
to the host repeatedly reclaiming the detached background process between conversation turns
— every restart resumed cleanly from the last completed case via `run_local_model.py`'s
case_id-based resume logic, no case was silently skipped or duplicated).

The real Omega/MeTTa advisory numbers for C were **reused verbatim** from the sonnet-4-5
confirmatory run (case_id-matched, doc 146's own point: the advisory is a property of the
case's injected claims, not of which downstream LLM reads it) — no new MeTTa invocations were
needed, and the isolated container was not restarted for this round.

## Model

`qwen3.5:9b` via Ollama (Q4_K_M quantization, 9.7B parameters, 6.6GB), served locally
(`http://localhost:11434`), `think: false` (this model has extended-reasoning/"thinking"
capability; left enabled, its internal reasoning consumed the entire output token budget and
`content` came back empty — disabling it is also required by this benchmark's own "no hidden
chain-of-thought" rule, directive section 34: only the observable final answer is ever used).

## Result — opposite direction from the hypothesis, with a precise, single-mechanism cause

| arm | decision_correct (n=63) | wrong_confident_physical_claim |
|---|---|---|
| B0 | 77.8% (49/63) | 6.3% (4/63) |
| B1 | 69.8% (44/63) | 0.0% (0/63) |
| C  | 65.1% (41/63) | 0.0% (0/63) |

- **B1 − B0**: −7.94pp, 95% CI [−19.05, +3.17]pp (crosses zero, not significant)
- **C − B1 (primary)**: −4.76pp, 95% CI [−11.11, 0.0]pp, sign-test p=0.25 (3 discordant, all
  favor B1)
- **C − B0**: **−12.70pp, 95% CI [−23.81, −3.17]pp** — does NOT cross zero. For this model, C
  is significantly WORSE than the no-advisory baseline.
- `NAL_NUMERIC_INCREMENTAL_VALUE = NOT_SUPPORTED` (rule V5 matched: all three arms within the
  10pp meaningful-effect band of each other pairwise by CI, though the point estimates trend
  monotonically B0 > B1 > C).

This is the opposite ranking from the sonnet-4-5 confirmatory run (B0 << B1 ≈ C there). The
hypothesis being tested — "a weaker model would show real numeric output mattering more" — is
not supported; instead, adding either form of advisory measurably hurt this model.

## The mechanism — not "can't use numbers," but "categorical wording overrides numeric reading"

Every one of the 9 B0-correct/B1-wrong discordant cases (100%, not a subset) has the **exact
same, single-field failure**: `epistemic_status`, `current_physical_claim`, and
`may_treat_as_current_authoritative` all still match gold exactly; only
`relative_historical_support` flips from B0's correct `TRUE_STRONGER`/`FALSE_STRONGER` to B1's
`APPROX_BALANCED`. The most striking verbatim example (case `385955d5c96d1447`, G9, C arm): the
real advisory block it was given reads `frequency: 0.00336, confidence: 0.99` — a claim pair
where one side is almost certainly false with very high confidence, about as far from "balanced"
as this benchmark's geometries get — and the model still answered
`relative_historical_support: APPROX_BALANCED`, self-reporting `reason_class:
FOLLOWED_ADVISORY`. It did not fail to use the advisory; it used the advisory's fixed
categorical phrase — `epistemic_interpretation: UNRESOLVED_CONFLICT_BETWEEN_OPPOSING_GROUNDED_
CLAIMS` — as if "opposing" itself meant "symmetric," while disregarding the two actual numbers
sitting in the same block that should have driven this specific field.

B0 never shows this failure because B0's prompt contains no categorical summary at all — only
the raw evidence lines, forcing the model to read the two source confidences directly to answer
`relative_historical_support`. B1 and C both introduce a fixed, category-labeling sentence
ahead of the question; this model appears to pattern-match that sentence's word choice into a
different field's answer, a form of instruction-following imprecision a stronger model
(sonnet-4-5, tested on the identical prompts and cases at full scale) did not exhibit.

## What this does and doesn't show

**Shows**: a real, mechanistically specific, 100%-consistent-within-sample failure mode where
a smaller model's qualitative pattern-matching on an advisory's fixed wording can override its
own otherwise-correct numeric reading of the same or adjacent evidence — for this specific
model, this specific advisory phrasing, at this one history scale.

**Does not show**: that smaller/local models categorically cannot benefit from real formal
advisories (a differently-worded advisory that doesn't contain a word colloquially suggestive
of "balance" might not trigger this), that this generalizes to scale=100/1000 (not run, per the
disclosed scope limit above), or that this specific model is representative of "small models"
generally (n=1 model, n=63 cases, one quantization).

## Reproducibility

`harness/ollama_client.py` (new), `harness/run_local_model.py` (new, resumable),
`159_local_model_confirmatory_rows.json` (raw rows, 63 cases). Real Omega/MeTTa advisory
numbers reused verbatim from `153_confirmatory_rows.json` by case_id match — fully
reproducible without needing the isolated container running, given that prior file.
