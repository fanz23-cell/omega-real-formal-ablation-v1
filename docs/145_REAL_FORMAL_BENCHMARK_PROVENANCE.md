# 145. Fresh Provenance — Real Formal Benchmark (2026-09-28/29)

All facts below are CONFIRMED FACT — directly observed via `docker inspect`/`docker exec`/`git`/`sha256sum`
this session, read-only against the live system, before any isolated container was created.

## Live container state (docker ps, this session)

```
bison_client-omegaclaw-1        mindchildren/omegaclaw-core:fan_omegaclaw_ai_bt   Up 2 days   started 2026-09-26 15:30:01 -0700
bison_client-mc_world_state-1   mindchildren/mc_world_state:fan_omegaclaw_ai_bt   Up 6 days   started 2026-09-13 11:40:30 -0700
bison_client-mc_ai_bt-1         mindchildren/mc_ai_bt:fan_omegaclaw_ai_bt         Up 39 hours started 2026-09-27 04:44:54 -0700
```

- `bison_client-omegaclaw-1` image: `sha256:4b14c13ef5eadda7f0a9ce34676bfe652db675e885175040dd4b21336e8a65e9`,
  RestartCount=0. Matches doc 125's approved deployment digest (per doc 144's independent finding).
- `bison_client-mc_world_state-1` image: `sha256:3c62b81aff7a1d95842a285eb99da405654f2729777fe7b8562872587ce3cb05`,
  RestartCount=0, untouched since 2026-09-13 (predates the Stage-10 canary deploy entirely).
- Live omegaclaw mounts: `./omegaclaw-memory -> /PeTTa/repos/OmegaClaw-Core/memory` (rw, the live Chroma store),
  `./context/ai_bt_missions.jsonl -> /mission_journal_input/ai_bt_missions.jsonl` (ro). **Neither was touched
  this round** — the new benchmark's isolated container (below) never mounts either path.

## Plugin file hashes — local checkout vs live container (byte-identical, confirmed)

```
sha256                                                            file
2f77cf61a764020371d4c2d7b3071698d6a42c82fb05a05a89302eeb0ef2a268  grounded_reason/grounded_reason.py
fa77708dd9c0ae73d4fa3a14ca68debbec37e30fdf8958d687f87ecd44127b0e  grounded_reason/grounded_reason.metta
cc9031f1007fd3376dcd41694e379e55f416188cd3e427d539177e23f8503ce1  grounded_proposition/grounded_proposition.py
7096b1b2d9340b69633ad22742eb5576a52de6d75d95bb72f17afb43389d4d11  observation_memory/observation_memory.py
```

Verified identical both in `/home/mindbot/Workspace/omegaclaw-core-fork/overlay/plugins/...` (local checkout,
files present but **untracked in git** — see below) and inside the live running container at
`/PeTTa/repos/OmegaClaw-Core/plugins/...`. This gives full confidence the local checkout is a valid,
trustworthy source for building the isolated benchmark runtime.

## Git state, `omegaclaw-core-fork` (CONFIRMED FACT)

- Branch: `fan_omegaclaw_ai_bt`. HEAD: `0875242421fb5e2bbb5dceb49cf3a870d5d3dc6b` (2026-09-08, "codey_robot:
  default look() question to empty string").
- **The entire Stage 8-10 plugin set (`grounded_reason/`, `grounded_proposition/`, `observation_memory/`,
  `mission_memory/`, `persistent_goals/`, `event_attention/`, `routine_definitions/`,
  `robot_capability_profile/`) exists only as untracked (`??`) working-tree files, not in git history.**
  `Dockerfile`, `overlay/config/config.yaml`, `overlay/config/plugins.yaml` are locally modified (`M`) vs
  HEAD. No remotes configured (`git remote -v` empty).
- Bottom line (matches doc 143's independent finding): this checkout's tracked git history is stale;
  its working tree is the actual source of truth and matches the live deployed image exactly (hash-verified
  above).
- `bison_client` itself is not a git repository at all (`fatal: not a git repository`).

## `bison_client-mc_world_state-1` real Fact schema (CONFIRMED FACT, source-read)

`mc_world_state/mc_world_state/store.py`:
```python
@dataclass(frozen=True)
class Fact:
    scope: str
    key: str
    value: JsonValue        # arbitrary JSON
    observed_at: float
    source: str = ""
```
Write surface: ROS2 `mc_one/srv/UpdateWorldFacts.srv` (`scope, key, value_json, observed_at, source, merge,
include_snapshot`) → `WorldStateNode._handle_update_facts()` (`node.py:377`). A second real shape,
`mc_one/msg/RelationFact.msg`, exists separately for relations. Neither schema is used by this new
benchmark's fact-injection path (see doc 146) — the benchmark targets Omega's own real `record_world_event()`
intake directly, which has its own separately-real schema (below), not WorldState's.

## Real `record_world_event()` schema (CONFIRMED FACT, source-read from the live container)

`observation_memory.py`, function `record_world_event(event)` / `_record_world_event(event)`. Required
keys: `event_id, subject, predicate, value, source_type, source_id, observed_at (float, required),
confidence (0.0-1.0), predicate_aspect ("EVENT"|"STATE", fails closed to "UNKNOWN" if absent)`. Optional:
`semantic_entity_id`. Writes to Chroma collection `observation_claims_v1` with provenance ref
`obs:<event_id>`, `claim_kind="WORLD_EVENT"`. Full docstring and fail-closed polarity logic (`None`→
`"unknown"`, explicit falsy→`"false"`, else→`"true"`) captured verbatim in doc 146.

**Confirmed live**: this tracked checkout's `codey_robot.py` does not call `record_world_event()` anywhere
(0 live callers found via `grep -rn` inside the running container itself, not just the local checkout) —
matches doc 144's finding: the Stage-10 canary has real, working, callable intake and reasoning code, but
has never processed real production traffic since going live.

## Real Omega reasoning chain (CONFIRMED FACT, source-read + directly executed — see doc 149)

`grounded_reason.py`'s `grounded_reason_resolve_json()` → `_resolve_premise_claim()` (real Chroma lookup +
`grounded_proposition.classify_claim()` admission gate) → `_revision_eligible()` (Stage-10 canary gate: same
subject/predicate/predicate_aspect, opposing values) → constructs `(|- {p1} {p2})` MeTTa code → evaluated by
`grounded_reason.metta`'s `sread/eval/swrite` equation, which requires `lib_nal.metta`'s
`Truth_Revision`/`|-nal`/`|-` definitions to actually be loaded (this was NOT obvious from a first read and
cost real debugging time — see doc 149) → `materialize_advisory()` parses the resulting `(stv f c)` into the
final typed advisory JSON.

## Provider / model config (no secrets printed)

Prior long-horizon benchmark (docs 126-143) used `claude-sonnet-4-5-20250929` directly via a bespoke
`llm_client.py` (raw Anthropic API, not through Omega's own provider plumbing). Omega's own live `.env`
(read for var *names* only) shows `MC_AI_BT_PLANNER_MODEL=gpt-5.6-terra` for the **separate** mc_ai_bt
planner (not used by this benchmark) and `provider=Anthropic` as the omegaclaw container's own launch arg
(also not exercised by this benchmark's harness, which calls `grounded_reason`'s real Python/MeTTa code
directly in-process rather than through the container's own conversational LLM loop — see doc 147 §"why
the isolated container's normal CMD is overridden to an inert `sleep infinity`").

## Host resource state (CONFIRMED FACT — checked before creating any new container)

`df -h /`: 937G total, 872G used, **18G available (99% used)**. `free -h`: 15Gi total, ~731Mi free at
check time, swap 3.8/4.0Gi used. `docker stats --no-stream` showed every one of this project's own running
containers using well under 100MiB each (`bison_client-omegaclaw-1` itself: 56.81MiB) — the host's memory
pressure is from other tenants/processes outside this project's visibility, not this stack. Given the
per-container footprint observed, one additional lightweight, `--network none`, non-agent-loop container
(confirmed 568KiB at idle after creation) was judged an acceptable, bounded addition — not a crash risk —
consistent with this project's standing "never crash the shared host" constraint. Disk usage was not
meaningfully affected (no new image layers pulled; scratch Chroma data is KB-scale).

`PRODUCTION_MODIFIED: false` as of this document. Both live containers' `RestartCount` remain 0 and their
images/mounts are exactly as found at the start of this investigation.
