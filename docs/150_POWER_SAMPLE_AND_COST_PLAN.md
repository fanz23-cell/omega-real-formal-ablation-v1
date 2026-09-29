# 150. Power, Sample Size, and Cost Plan

## PRACTICALLY_MEANINGFUL_EFFECT (frozen before any paid call)

A **>=10 percentage point** paired C-vs-B1 decision-accuracy delta. Chosen because it is
comfortably above noise for a binary metric at this scale, while not so large that only an
implausibly huge effect would register — a genuine middle-ground pre-registration, not tuned
to whatever the data later show.

## Method

$0 Monte Carlo simulation (`harness/power_analysis.py`, fixed seed 777, no `Math.random`/
wall-clock dependency) of the exact two-sided sign test's power to detect a given paired
accuracy delta, swept across a plausible range of discordant-pair rates (0.15/0.25/0.35 —
unknown until calibration, so swept rather than assumed) and candidate pooled sample sizes.

## Result

| target effect | discordant rate | pooled N for power>=0.80 |
|---|---|---|
| 10pp | 0.15 | 120 |
| 10pp | 0.25 | ~180 (0.76 at 150, extrapolated ~0.80 at 165-170) |
| 10pp | 0.35 | not reached by 180 (0.60) |
| 15pp | 0.25 | 100 |
| 20pp | 0.25 | 60 |

## Decision

Target pooled confirmatory N = **189 pairs** (9 preregistered confidence geometries x 3
mandatory history scales [10, 100, 1000] x 7 replicates per cell). This gives power >=0.80 for
the 10pp target at the two more-likely discordant-rate regimes (0.15, 0.25) and reduced-but-
real power (~0.60) at the more conservative 0.35 regime — disclosed as a real limitation, not
hidden. This is the smallest pooled N in the simulated grid that clears the 0.80 bar for at
least the two most plausible discordant-rate assumptions, satisfying "smallest scientifically
defensible sample, do not maximize spend."

**Optional scales (N=30, N=300) are NOT run** — the 3 mandatory scales already provide the
target pooled N; adding two more scales would mean either fewer reps per cell (weakening
power) or a proportionally larger, unbudgeted spend for marginal additional insight into
history-scale interaction, which is a secondary question here (the primary question is
mechanism value, not scale interaction — that was already the prior round's finding).

## Cost estimate

189 pairs x 3 arms (B0, B1, C) = 567 real LLM calls for the confirmatory run (same order of
magnitude as the prior long-horizon benchmark's 585 calls). At the same model/pricing tier
(`claude-sonnet-4-5-20250929`, ~$1.72 for 624 calls in the prior round, prompts of similar
length), expected cost is in the same **~$1.50-$2.50** range. Calibration (section 26) uses a
small, separate, non-confirmatory seed pool (~20-30 calls) to validate wiring/schema/cost
before committing to the full confirmatory run.

## What this does NOT claim

This plan is sized for the POOLED, primary C-vs-B1 contrast. Per-geometry-cell breakdowns
(7 reps each) are individually underpowered for anything but a large within-cell effect —
exactly like the prior round's own F5 family (n=15, directionally consistent, not
independently significant) — and will be reported with that same explicit caveat, not
oversold as independently decisive at the per-cell level.
