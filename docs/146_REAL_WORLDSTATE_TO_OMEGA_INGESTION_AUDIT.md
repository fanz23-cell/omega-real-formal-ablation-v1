# 146. Real WorldState-to-Omega Ingestion Path Audit

## Question

How does a real authoritative WorldState/event become a WORLD_EVENT claim consumable by
`grounded_reason`?

## Trace (all CONFIRMED FACT, read from the live running container, not just the local checkout)

```
WorldState Fact (scope/key/value/observed_at/source, mc_world_state/store.py)
   -- NOT directly connected to Omega. Omega is not a ROS2 node, does not subscribe to
      WorldState, and has no topic/service client for it. --
   ↓ (no existing production wire between these two)
observation_memory.record_world_event(event)   <- REAL, COMPLETE, CALLABLE, but 0 production callers
   ↓ (writes to observation_claims_v1, provenance ref "obs:<event_id>")
grounded_reason._find_by_provenance_ref("obs:<event_id>")   <- REAL, confirmed working live
   ↓
grounded_reason._to_claim() -> grounded_proposition.classify_claim()   <- REAL admission gate
   ↓
grounded_reason._revision_eligible()   <- REAL Stage-10 canary gate (doc 115/118)
   ↓
grounded_reason._statement_for() -> "(|- {p1} {p2})" metta code   <- REAL, confirmed working live
   ↓
grounded_reason.metta's sread/eval/swrite, needs lib_nal.metta loaded   <- REAL, confirmed working (doc 149)
   ↓
grounded_reason.materialize_advisory()   <- REAL, confirmed working live
```

## Classification: PATH_GRADE_B

Directly confirmed by grepping the live container's own filesystem (`docker exec ... grep -rn
"record_world_event\|record_observation" /PeTTa/repos/OmegaClaw-Core/`): `record_world_event()` is a
complete, real, typed, production-quality function (full docstring, fail-closed polarity handling, the
same durability/ownership discipline as `record_observation()`) — but **zero callers exist anywhere in
the live deployed code**. The only real caller of anything in this file is
`codey_robot.py:276`'s `observation_memory.record_observation(...)` (the camera-only ROBOT_OBSERVED path,
a different function).

This is exactly PATH_GRADE_B as defined by the governing directive: *"No complete production caller
exists, but real WorldState/event code and the real Omega `record_world_event()` typed intake both
exist. A benchmark-only, mechanical 1:1 adapter can connect them without inventing semantic fields."*

It is explicitly NOT PATH_GRADE_A (no end-to-end production caller exists) and NOT PATH_GRADE_BLOCKED
(no semantic inference is required — `record_world_event()`'s required fields are fully and exactly
specified in its own docstring; a mechanical field-mapping adapter, never guessing a value the source
data doesn't actually provide, is all that's needed).

## The benchmark-only adapter (mechanical, 1:1, no invented fields)

`harness/ingestion_adapter.py` (built this round) maps a benchmark case's synthetic-but-real-schema
claim directly onto `record_world_event()`'s exact required keys:

| Benchmark case field | `record_world_event()` key | Mapping rule |
|---|---|---|
| `event_id` (caller-minted) | `event_id` | passed through unchanged |
| `subject` | `subject` | passed through unchanged |
| `predicate` | `predicate` | passed through unchanged |
| `value` (bool/str/None) | `value` | passed through unchanged (never re-interpreted; `record_world_event`'s own polarity logic decides true/false/unknown) |
| `source_type` | `source_type` | passed through unchanged |
| `source_id` | `source_id` | passed through unchanged |
| `observed_at` (real wall-clock-comparable float) | `observed_at` | passed through unchanged — **required**, never fabricated if the case doesn't supply one (fail-closed: adapter raises rather than defaulting) |
| `confidence` (0.0-1.0) | `confidence` | passed through unchanged |
| `predicate_aspect` ("EVENT"\|"STATE") | `predicate_aspect` | passed through unchanged — fail-closed if a case supplies neither |
| `semantic_entity_id` (optional) | `semantic_entity_id` | passed through, defaults to `""` (the function's own honest-empty convention, not invented) |

No field on this list is inferred, guessed, or derived from anything the case data doesn't already
explicitly state. The adapter performs pure reshaping/renaming, not semantic judgment. Per the
directive's own requirement, this adapter lives only in `harness/` (this research directory), is never
shipped toward production, and is explicitly labeled in the final report as `PRODUCTION_COMPONENT_PATH`
(reuses real production components end-to-end) rather than `FULL_PRODUCTION_INGESTION_PATH` (no such
fully-wired production path exists yet, since there is genuinely no live caller of
`record_world_event()` today).

## What this means for the benchmark's B0/B1/C arms

All three arms' underlying "world" facts are constructed in this real schema and injected via this real
function, in an isolated environment (doc 147). The only difference across arms is what the LLM is
shown in its prompt (raw window / +structural label / +real NAL numeric result) — never a difference in
how the underlying facts were stored or which code recorded them.
