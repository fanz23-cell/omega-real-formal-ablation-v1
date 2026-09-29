# 153. Confirmatory Run Report

189 cases (9 preregistered geometries x 3 scales [10,100,1000] x 7 reps), 567 real
`claude-sonnet-4-5-20250929` calls, seed pool `CONFIRM_v1` (disjoint from calibration's
`CAL_v1`). Wall-clock: 2209.3s (~36.8 min). **0 invalidated cases** (100% passed the
automated fairness check, doc 148). **0 hard parse failures** after the calibration-caught
parser fix (doc 152). Randomized per-case B0/B1/C execution order (seed 20260928).

**Live production health, before and after**: `bison_client-omegaclaw-1` and
`bison_client-mc_world_state-1` — identical image digests, `RestartCount=0`, `state=running`
at both checkpoints. `PRODUCTION_MODIFIED: false` held throughout the entire run.

Raw rows: `153_confirmatory_rows.json` (847KB, one row per case with full `answers`, `raw`
completions, `flags`, `real_advisory`, `execution_order`). Full statistics:
`154_statistical_analysis.json` (see doc 154 for the narrative version).

## Real cost — a disclosed planning error, corrected here

**Actual cost: 15,918,615 input tokens + 56,473 output tokens ≈ $48.60** (at
$3/MTok input, $15/MTok output — current published `claude-sonnet-4-5` API pricing), NOT the
~$1.50-2.50 doc 150 projected before this run. Root cause: doc 150's cost estimate reasoned
correctly about SAMPLE COUNT (189 cases matching the prior benchmark's 585-call scale) but
never accounted for individual PROMPT SIZE at the N=1000 history-scale tier — each such
prompt renders very nearly 1000 distractor event lines in full (by design, doc 13's own
scale-axis requirement), which is ~25-30 tokens/line, i.e. ~25,000-30,000 input tokens per
call at that tier alone, not the few-hundred-token prompts the N=10/N=100 tiers use. This was
not caught before the run because doc 150's projection reasoned by analogy to the prior
benchmark's *total call count* being similar, without separately checking prompt-size scaling
at the largest history tier. Disclosed here in full, not minimized — this is a real planning
gap, corrected for any future round of this design (a future version should either cap
rendered distractor count, summarize/truncate the distractor block at large N, or budget
explicitly for N=1000-tier token cost before launching).

See doc 154 for the full statistical analysis and doc 155 for the qualitative trace/failure
analysis of the discordant B1-vs-C cases.
