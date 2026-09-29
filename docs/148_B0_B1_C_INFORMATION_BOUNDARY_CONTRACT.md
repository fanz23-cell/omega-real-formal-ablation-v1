# 148. B0/B1/C Information-Boundary (Fairness) Contract

## Invariant

For every paired case: `RAW_WORLD_B0 == RAW_WORLD_B1 == RAW_WORLD_C` (same events, same order,
same rendering); `LLM_MODEL/SYSTEM_PROMPT/TASK_PROMPT (except treatment block)/OUTPUT_SCHEMA/
TEMPERATURE/MAX_TOKENS` identical across all three arms; the B1/C treatment block is
byte-identical except the two numeric lines (`frequency=`/`confidence=`).

## Enforcement mechanism

`harness/fairness_check.py`'s `check_case_fairness()` — an automated, mechanical diff checker,
not a manual/visual check — run on every case before scoring. It verifies, per case:
1. The rendered evidence block (raw events) is character-identical across B0/B1/C.
2. B1's treatment block numeric fields are literally the string `WITHHELD_CONTROL` (never a
   real number, so a scorer or model cannot accidentally leak the real numeric result into B1).
3. C's treatment block numeric fields are real floats (never still `WITHHELD_CONTROL`).
4. Every non-numeric line of the B1/C treatment blocks is identical; any other difference
   fails the case.
5. No brand/placebo cue (`Omega`, `NAL`, `PLN`, `MeTTa`, `baseline`, `control`, `treatment`,
   `formal engine`, `more trustworthy`) appears anywhere in any of the three rendered prompts
   (directive section 12).

A case failing any of these checks is **invalidated and not scored** — never silently repaired.

## Eligibility is reused, not reimplemented

Whether a given case is a "genuine conflict" eligible for the structural/formal advisory is
decided by calling the REAL `grounded_reason._revision_eligible()` gate (via
`real_metta_runner.real_grounded_reason()`), never by a second handwritten copy of that logic.
Section 16's negative controls (doc: `harness/negative_controls.py`, run this round, $0, all 9
cases) independently confirm this real gate correctly rejects same-polarity pairs, subject/
predicate/aspect mismatches, unresolved/unknown values, missing premise refs, non-eligible claim
kinds, and unknown predicate_aspect — each for the exact real, specifically-named error code the
production code itself returns (e.g. `REVISION_SUBJECT_MISMATCH`, not just a generic failure).
This gives confidence that every case the harness treats as "eligible" for B1's structural label
and C's real advisory genuinely is eligible by the real system's own standard, not by this
benchmark's own possibly-diverging judgment.

## What B1 controls for

B1 exists specifically to isolate "the LLM was told, in plain typed language, that there is an
unresolved conflict and to escalate/recheck" from "the LLM was given the real, quantified NAL
numeric output." Both B1 and C reuse the same real eligibility determination; B1 simply never
receives the two numeric fields that determination would otherwise justify computing.

## Randomization / blinding (directive section 29)

Execution order of B0/B1/C is randomized per case (not always B0-then-B1-then-C) using a fixed,
disclosed seed (`random.Random(20260928)`), implemented in the confirmatory run driver. Internal
treatment IDs shown to the LLM are neutral (`ADVISORY A`, never `B1`/`C`/`Omega`/`control`). The
scorer computes metrics from typed answer fields only and does not depend on which arm produced
which answer until after per-case metrics are computed — arm identity is only reattached at the
aggregation step, matching the directive's "anonymize X/Y/Z first" intent in spirit (full literal
X/Y/Z relabeling was judged unnecessary in addition to neutral in-prompt labels + fixed scoring
code that never branches on arm identity, but is noted here as an available strengthening if a
future round wants it).
