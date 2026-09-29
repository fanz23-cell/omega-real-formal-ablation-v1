# 156. Final Product Verdict — Real Omega/MeTTa Formal Math

## Q1: Did the old conflict benefit replicate using real Omega/MeTTa?

**PARTIAL.** The old benchmark's headline claim was "C beats B0/a non-formal baseline by a
huge margin on genuine conflicts." Using the REAL engine: **C does beat B0** by a large,
highly significant margin (+19.05pp, 95% CI [12.17, 26.46]pp, sign-test p=7.3e-7) — but this
entire benefit is now shown to come from the deterministic structural conflict label, not
from the real NAL numeric computation specifically, because **B1 (structural label alone,
zero real math) matches C almost exactly** (+20.11pp over B0, CI [13.23, 27.51]pp,
p=1.4e-7 — statistically indistinguishable from C's own gain over B0). The old benchmark
never had a B1 arm and could not separate these two explanations; this round's B1 arm is what
makes "partial" the accurate answer rather than "yes."

## Q2: Did B1 reproduce most of C's benefit?

**YES.** B1 = 92.6% decision_correct, C = 91.5% — B1 is not merely "close to" C, it is
statistically indistinguishable and numerically very slightly HIGHER. B1 reproduces
essentially all (actually, in this sample, slightly more than all) of C's measured benefit
over B0.

## Q3: Does real NAL numeric revision add statistically and practically meaningful incremental value over B1?

**NOT_SUPPORTED** (pre-registered rule V1, doc 150/`analyze.py`, frozen before this result
was seen). Primary contrast C-vs-B1: **-1.06pp, 95% CI [-4.76, +2.65]pp**, n=189 pairs,
sign-test p=0.774 (12 discordant pairs, 5 favor C / 7 favor B1 — not even directionally
consistent, let alone significant). The CI does not clear the pre-registered
PRACTICALLY_MEANINGFUL_EFFECT threshold (10pp) in either direction. Breakdown by all 9
preregistered confidence geometries (doc 154) shows the same null pattern in every single
cell — including the near-tie geometries (G6, G7) and extreme-asymmetry geometries (G8, G9)
specifically designed to be the cases where quantified numeric input might matter most.
Breakdown by history scale (N=10/100/1000) shows no scale interaction — the gap hovers
within noise of zero at every scale, never growing.

**Additional, more specific and more concerning finding** (doc 155): of the 12 total
discordant B1-vs-C cases, 2 concrete real ones show C's real numeric output being actively
misused — the model treats an extreme frequency value (near 0.0 or 1.0) as license to
collapse an unresolved conflict into a confident physical claim, `reason_class` self-
reporting its own judgment rather than following the advisory's explicit
`ESCALATE_OR_RECHECK` instruction. This is offset by 2 mirror cases where B1 makes the same
kind of mistake with no numeric input at all — so the aggregate safety metric shows no net
difference (both arms: 2.1% wrong-confident-physical-claim rate, 4/189, CI on the C-vs-B1
safety delta exactly [-2.12, +2.12]pp) — but the mechanism-level finding (real numeric output
CAN be misused this way) is real and disclosed regardless of the net-zero aggregate.

## Q4: What exactly should production keep?

**No change is supported by this result.** The currently deployed Stage-10 bounded revision
canary (real, narrow, `revision`-only, `authority=NONE`) is not shown to be harmful by this
study, but this study also does not provide evidence that its real numeric output adds
decision-quality value beyond what a much simpler, deterministic structural-conflict label
(no NAL math, no MeTTa/PeTTa runtime dependency at all) would already provide. This is a
genuinely different, more specific conclusion than the prior (Python-approximated) benchmark
could reach, and it directly answers the open question doc 143 raised: replacing the
approximation with the real engine changed the scientific conclusion, not just its
methodological rigor.

## Q5: Does this justify expanding beyond bounded revision?

**NO** — and more strongly than the prior round's default-NO: this round's own real-engine
evidence provides an affirmative reason for caution (the OVERTRUSTED_FORMAL_OUTPUT pattern,
doc 155) rather than merely "no evidence either way." No deduction/abduction expansion is
supported by this evidence.

## What this benchmark does NOT prove (repeated, disclosure-first, matching directive discipline)

- Does not prove the real engine's math is *wrong* — `Truth_Revision`'s arithmetic was
  independently hand-verified correct (doc 149) for multiple geometries. The finding is about
  *decision value added*, not mathematical correctness.
- Does not test `deduction`/`pln_forward`/`pln_abduction` — only `revision` (matching the
  live production canary's own scope).
- Does not test the real production ingestion path end-to-end (doc 146: PATH_GRADE_B, a
  benchmark-only mechanical adapter was used, since no live caller of `record_world_event()`
  exists in production today).
- Per-geometry-cell breakdowns (n=21 each) are individually underpowered for anything but a
  large within-cell effect — the null found here is a POOLED, well-powered (target 10pp
  effect, achieved power per doc 150) result; a genuinely small (<5pp) true effect cannot be
  fully ruled out by this design, though the pooled point estimate (-1.06pp) is itself in the
  wrong direction to support one.
- Does not evaluate whether a DIFFERENT LLM, DIFFERENT prompt phrasing of the structural
  label, or a DIFFERENT downstream consumption contract would change this picture.

## One-sentence scientific conclusion

Using the real, unmodified Omega/MeTTa NAL revision engine (not an approximation) in a
design that separately controls for structural conflict recognition, this benchmark finds
**no measurable incremental decision-quality benefit from the real numeric formal-revision
output beyond a deterministic typed conflict label alone** (C vs B1: -1.06pp, 95% CI
[-4.76, +2.65]pp, p=0.77, replicated null across all 9 preregistered confidence geometries),
and identifies a real, concrete (though non-significant in aggregate) failure mode in which
the numeric output can itself be misused to justify unsafe overconfidence.
