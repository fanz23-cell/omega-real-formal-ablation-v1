# 144. Real-Formal-Benchmark Re-Anchor and Current Status (2026-09-28)

**Purpose**: mandatory re-anchor before a new benchmark round begins — an A/B/C-arm comparison
(B0/B1 = LLM-prompting strategies without the real formal engine, C = the same stack *plus the real
Omega MeTTa/NAL revision engine*, replacing the prior round's Python reimplementation). This document
is read-only: no code was written, no container was restarted, no file outside this new doc was
modified, no production data was touched. All findings below come from directly reading canonical
docs, reading research-thread docs 106–143, and live read-only commands (`docker ps`, `docker
inspect`, `docker logs`, `git status`, file reads) run during this session on 2026-09-28.

Evidence labels used throughout, per `ENGINEERING_GUARDRAILS.md` §2:
**CONFIRMED FACT** (I directly read/ran something that proves this right now) · **STRONG
HYPOTHESIS** (well-supported but not independently re-verified by me this pass) · **UNKNOWN**
(genuinely unclear, flagged, not guessed) · **PROPOSED CHANGE** (a document proposes this; not yet
approved/implemented).

---

## 1. Executive summary

**CONFIRMED FACT.** Per `CURRENT_STATE_DELTA.md`'s 2026-09-21 override (unchanged by the 2026-09-26
override, both read in full from
`mc_dashboard/CLAUDE_REVIEW_PACKAGE_2026-09-28/canonical_docs/`), the project sits at "OVERALL SYSTEM
PROGRESS ≈92%/100%, CURRENT MAJOR STAGE 11/11 — Full Cognitive Autonomy / Omega-value qualification."
Stage 10 (NAL/PLN Advisory Integration) is *generally* "NOT APPROVED FOR PRODUCTION," but a narrow,
explicitly-scoped exception — **CANONICAL STAGE 10: BOUNDED_GROUNDED_CONFLICT_REVISION_ADVISORY_
CANARY** — was human-authorized and deployed live on 2026-09-26 (doc 125,
`omega_incremental_value_v1_20260924/`). I independently re-verified via `docker inspect` that this
exact deployment (image `sha256:4b14c13ef5ea...`) is still the running container as of this session,
unchanged, 0 restarts (§3).

**CONFIRMED FACT.** The prior long-horizon benchmark round (docs 126–142,
`omega_long_horizon_belief_scaling_v1_20260926/`) found a large, real, statistically significant
benefit for a "Contestant C" that used the formal-revision mechanism — but doc 143 (dated
2026-09-28T18:33, the newest file in that directory, nothing supersedes it) establishes that this
Contestant C was **not the real Omega/MeTTa engine**. It was `contestants.compute_formal_advisory()`,
a hand-written Python function reproducing the *shape* of the real NAL revision-confidence formula,
never calling the real MeTTa interpreter or the real `grounded_reason` plugin. The user directly
challenged this (doc 143 §2, verbatim Chinese quote) and the investigation confirmed the objection was
correct.

**This is why the new benchmark round exists**: to rebuild Contestant C so it invokes the real Omega
MeTTa/NAL revision engine (the same code path as the live Stage-10 canary) rather than a
reimplementation, while still respecting the standing constraint that the live, robot-facing instance
at `192.168.0.5:8910` (backed by `bison_client-omegaclaw-1` / `bison_client-mc_world_state-1`) must
never be written to or put at risk. Doc 143 is an **open, unactioned decision request** to an external
reviewer choosing between three isolation designs (Option A/B/C, §6 below) — as of this session, no
response or decision has been recorded (no file in the research directory is newer than doc 143).
This document's job is to hand the next construction/benchmark step an accurate, current, verified
floor to build on, not to make that design decision itself.

---

## 2. Current Stage-10 production status

**CONFIRMED FACT** (cross-checked: doc 125 deployment record vs. my own live `docker inspect` run
this session): the bounded canary is still live, unchanged, since deployment:

```
Container:      bison_client-omegaclaw-1
Image ID:       sha256:4b14c13ef5eadda7f0a9ce34676bfe652db675e885175040dd4b21336e8a65e9
                (exact match to doc 125's approved "Candidate V5" digest)
Live tag:       mindchildren/omegaclaw-core:fan_omegaclaw_ai_bt
StartedAt:      2026-09-26T22:30:03.136295073Z
RestartCount:   0   (still 0 as of this session — no crash/restart since deploy)
Status:         running
```

**Exact authorized scope** (doc 124/125, hash-verified live by the deploying agent against the
running container's own `grounded_reason.py`/`.metta`, §9 of doc 125):
- Operator: **`revision` only** — `deduction`, `pln_forward`, `pln_abduction` are rejected before
  premise lookup in the LLM-facing wrapper (the internal/dev `grounded_reason()` engine itself
  remains unrestricted for non-production callers).
- Both premises must be `WORLD_EVENT` claims sharing the same `subject`, `predicate`, and
  `predicate_aspect`.
- Values must be **genuinely opposing** (same-value pairs were deliberately narrowed out in Candidate
  V4/doc 118 — a documentation-example-only case, not evidence-backed).
- Fails closed on `UNKNOWN predicate_aspect` (doc 119's `WORLD_EVENT_UNKNOWN_PREDICATE_ASPECT_
  COLLAPSED_TO_STATE` fix).
- Result is wrapped by `materialize_advisory()`: `frequency`/`confidence` always correctly labeled
  (never swappable), `epistemic_interpretation`/`recommended_cognitive_action` derived from the
  already-computed eligibility class (not from re-interpreting raw STV numbers), `authority` hardcoded
  `"NONE"`.
- No code path from this canary reaches WorldState, PolicyGuard, mc_ai_bt, or Bridge. It is
  advisory-only, LLM-consumed text.

**No incidents or repairs since deployment.** Doc 125's own monitoring plan (§11) lists rollback
triggers; none have fired per the doc, and my own read this session (RestartCount=0, zero tracebacks
across the full container log — see §3) is consistent with "no incident since 2026-09-26."

**CONFIRMED FACT, newly established this session (not previously in doc 125's own honest-gap
list, but directly consistent with it)**: the production mission journal
(`mc_one_codey/bison_client/context/ai_bt_missions.jsonl`) has a filesystem mtime of
**2026-09-21 04:21:58**, i.e. it has **not been appended to since before the canary was deployed**
(2026-09-26T22:30). The observation-memory log
(`mc_one_codey/bison_client/omegaclaw-memory/observation_memory.log`) is still exactly 14 lines, all
dated 2026-09-07/08 — unchanged from doc 125's own count. Together with a `docker logs` grep showing
the container's one-and-only "no robot connected" drop message occurred at 2026-09-26T22:30:06 (3
seconds after boot) and never recurred, this means: **the two deferred post-deploy smoke items from
doc 125 (a live mission-submission smoke; a real conflicting-observation smoke) are still undone as of
this session** — not because of any new defect, but because no real robot mission and no fresh
conflicting WORLD_EVENT data have reached production at all since before the deploy. This is an
environment-precondition gap, not a canary defect, exactly as doc 125 itself characterized it — but it
means the canary has, to date, **never processed a real production mission or a real conflict end to
end**; all evidence for it working correctly is from isolated dry-run/harness testing (docs 106–124)
plus one mechanical hash-verification at deploy time, not from live production traffic since going
live.

**UNKNOWN**: whether `grounded_reason`/`query_observation_claims` have been invoked at all in
production since 2026-09-26 in a non-mission context (e.g. a chat-only conversational turn touching
memory). A `docker logs` keyword count for these skill names returns high numbers (600+), but manual
inspection shows these are dominated by the skill's own description text being reprinted in every
loop-cycle prompt dump, not distinguishable actual invocations, without a more careful log-format-aware
parse that this read-only pass did not attempt.

---

## 3. Current live container/deployment state

**CONFIRMED FACT** (`docker ps` / `docker inspect`, run this session):

```
NAME                                              IMAGE                                              STATUS        CREATED
bison_client-omegaclaw-1                          mindchildren/omegaclaw-core:fan_omegaclaw_ai_bt    Up 2 days     2026-09-26 15:30:01 -0700 PDT
bison_client-mc_ai_bt-1                           mindchildren/mc_ai_bt:fan_omegaclaw_ai_bt          Up 39 hours   2026-09-27 04:44:54 -0700 PDT
bison_client-mc_ai_bt_confirmation-1               mindchildren/mc_ai_bt:fan_omegaclaw_ai_bt          Up 39 hours   2026-09-27 04:44:54 -0700 PDT
bison_client-mc_world_state-1                      mindchildren/mc_world_state:fan_omegaclaw_ai_bt    Up 6 days     2026-09-13 11:40:30 -0700 PDT
bison_client-mc_embodied_skills-1                  mindchildren/seattle_lab:fan_omega                 Up 6 days     2026-09-13 01:27:35 -0700 PDT
bison_client-mc_resource_authority-1               mindchildren/mc_resource_authority:fan_omegaclaw_ai_bt  Up 6 days  2026-09-12 11:02:08 -0700 PDT
bison_client-mc_voice_pipeline_legacy_pipeline-1   mindchildren/mc_voice_pipeline_legacy:fan_omegaclaw_ai_bt  Up 6 days  2026-09-08 15:21:51 -0700 PDT
bison_client-fluent-bit-1 / mc_media / mc_multimodal / rhubarb   (supporting services, all "Up 6 days")
animation_edit-animation_edit-1                   mindchildren/animation_edit:latest                 Up 3 hours    2026-09-28 16:28:32 -0700 PDT (unrelated side project)
```

`mc_world_state-1`: image `sha256:3c62b81aff7a1d95842a285eb99da405654f2729777fe7b8562872587ce3cb05`,
RestartCount=0, StartedAt 2026-09-23T00:38:37Z — i.e. **older than the omegaclaw canary redeploy**;
WorldState itself was not touched by the 2026-09-26 change, consistent with the canary's own
"no code path reaches WorldState" claim.

Nothing here contradicts the docs: the currently-running `omegaclaw` container is exactly the
Stage-10 bounded-canary candidate the handoff docs describe, not a stale or drifted image.

**Config/env, non-secret values only** (`.env` var names + values that are tags/models/timeouts, no
API keys read or printed):

```
MC_DOMAIN=43
MC_VOICE_PIPELINE_LEGACY_TAG=fan_omegaclaw_ai_bt
SEATTLE_LAB_TAG=fan_omega
MC_AI_BT_PLANNER_BACKEND=langchain_openai
MC_AI_BT_PLANNER_MODEL=gpt-5.6-terra
MC_AI_BT_PLANNER_TIMEOUT_SEC=25.0
MC_MULTIMODAL_MODEL=gpt-4o-mini
ROBOT_GATEWAY_BRIDGE_CALL_TIMEOUT_SEC=30
```

Other env vars present (names only, values not printed/needed): `ANTHROPIC_API_KEY`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AZURE_REGION`, `AZURE_SPEECH_KEY`, `DEBIAN_FRONTEND`,
`DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`, `GITHUB_TOKEN`, `GITHUB_USER`, `HF_HOME`,
`IMPORT_KB_ON_START`, `LANG`, `MEMORY_DIR`, `OMEGACLAW_DIR`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
`PATH`, `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, `SENTENCE_TRANSFORMERS_HOME` — this is the same
set doc 111/125 recorded; no drift.

`MC_AI_BT_PLANNER_MODEL=gpt-5.6-terra` **confirms live** the model provenance that
`SESSION_DELTA_2026-09-21.md` flagged as needing fresh verification ("a later live bob task ran under
a reported gpt-5.6-terra configuration... fresh runtime provenance is still mandatory"). That
provenance check is now done: this is genuinely the configured planner model for `mc_ai_bt`, not
merely a historical claim.

**CONFIRMED FACT, repo-provenance gap worth flagging**: the tracked git checkout at
`/home/mindbot/Workspace/omegaclaw-core-fork` is on branch `fan_omegaclaw_ai_bt`, HEAD
`0875242421fb...` dated **2026-09-08**. `git status` shows the entire `grounded_reason`,
`observation_memory`, `mission_memory`, `persistent_goals`, `event_attention`,
`robot_capability_profile`, `routine_definitions`, and `providers` plugin directories as **untracked**
(`??`), plus modified `Dockerfile`/`config.yaml`/`plugins.yaml`. In other words: essentially all of the
Stage-8/9/10 cognitive-substrate work (docs 87–125) exists only as uncommitted local files, not as git
history, on top of a HEAD that predates almost this entire research arc. This matches doc 143 §4.2's
independent finding that "the tracked checkout is a commit or two behind the live container's actual
code." A new benchmark that wants to invoke "the real Omega/MeTTa engine" must use the **live
container's own files** (or this same uncommitted working tree) as its source of truth, not `git show`
against HEAD.

---

## 4. Open items / known bugs / repair threads relevant to Omega/MeTTa/WorldState

From `ENGINEERING_GUARDRAILS.md` and `CURRENT_STATE_DELTA.md` (both CONFIRMED FACT as documents that
exist and say this; the underlying engineering claims are STRONG HYPOTHESIS unless otherwise
re-verified this session):

- **Conditional human-language reporting remains architecturally OPEN** — no deterministic
  raw-utterance↔mission_id binding exists in `submit_mission`; do not assume any new benchmark can
  lean on this for its own plumbing.
- **Grounded Proposition canonicalization is production-unsafe outside the narrow Stage-10 scope**:
  proposition identity/subject canonicalization is incomplete; `ROBOT_OBSERVED` lacks a safe
  producer-side `semantic_entity_id` link on the current `robot_observe` path; mission semantic ids
  fail to persist for alias missions (`mission.py` wiring bug); `grounded_reason._to_claim()` drops a
  persistent goal's semantic id; negative-observation truth state can be lost in `_to_claim()`/
  `_statement_for()` — flagged as a **P0 latent truth-corruption risk** if subject linkage were fixed
  without fixing truth-state preservation at the same time. These are read-only-audit findings from
  the 2026-09-21 session, not yet repaired; the Stage-10 canary's own narrow scope was deliberately
  designed to not depend on the broken parts.
- **Exact numeric-tie STV interpretation remains a genuinely open research question** for any operator
  other than the Stage-10-shipped `revision`/opposing-values case. `ENGINEERING_GUARDRAILS.md`: "raw
  STV must not be production decision authority without a validated consumption contract."
- From `CURRENT_AUTONOMOUS_REPAIR_STATE.md` (the detailed engineering log behind docs 95–125), two
  narrow, explicitly-NOT-fixed findings are tracked (not blockers, not silently dropped):
  - **Q1 epistemic-status labeling**: model correctly understands a one-time historical event but
    labels it `STALE`/`RECHECK_WORLD` instead of the more precise `HISTORICAL`/`NONE` (seed 966001,
    doc-era finding, one instance).
  - **`GROUNDED_REASON_CALL_FINAL_ANSWER_BUNDLING_SLIP`**: observed once (seed 965001) — a real
    completion embedded a stray newline plus intended final-answer text inside the `grounded_reason`
    JSON string argument, producing malformed JSON; the ABI wrapper correctly failed closed, but the
    model's retry then wrapped its answer in an `(Error ...)` block instead of a real `(send ...)`,
    so no reply reached the channel. 1/4 in that continuation, 5/9 combined across continuations —
    tracked as possible rare stochastic noise, explicitly not yet promoted to a systemic fix per this
    project's own "fix systemic bugs only" rule.
- From doc 136 (long-horizon benchmark verdict, itself now partly discredited by doc 143's fabricated-C
  finding — see §5): a **real, disclosed, NOT-yet-addressed finding, F6_EXCEPTION_HANDLING**, showed
  ~57% failure for *both* B and C equally on time-bounded-exception queries — unrelated to and not
  fixed by the formal-revision mechanism. This is real product-relevant information flagged for future
  work, not authorized by any existing CHANGE APPROVAL.
- The Stage-10 canary's own two honestly-reported gaps (§2 above): no real production mission and no
  real conflicting-observation data have reached it since deploy, so its live-traffic correctness
  remains unproven beyond the mechanical/dry-run verification already done.

None of these are Stage-10-scope blockers per se, but a new benchmark that claims to exercise "the
real Omega MeTTa/NAL revision engine" should not assume the surrounding production pipeline (premise
construction, subject linkage, truth-state preservation) is safe or complete outside that one narrow,
already-shipped path — the guardrails are explicit that it is not.

---

## 5. What changed between the last long-horizon benchmark round (docs 126–143) and now

**CONFIRMED FACT.** The single material change is doc 143 itself (2026-09-28T18:33), which
retroactively invalidates how "Contestant C" in docs 126–142 should be described:

- Docs 126–136 (spec, freeze manifest, calibration, reduced/full run, product-thesis verdict) present
  a real, statistically-analyzed B-vs-C comparison (paired seeds, pre-registered decision rules per
  doc 130 §8, 624 real LLM calls) and conclude **R2 — narrow conflict-only benefit — SUPPORTED**: C's
  entire measured advantage concentrates in the 2/12 case families where the formal-revision gate
  structurally applies; zero difference elsewhere; scale-invariant, not scale-growing; no harm
  detected. This numerical result is not retracted by doc 143 and remains real *evidence about the
  formula's behavior*.
- What doc 143 retracts is the **causal attribution**: doc 129 §2 (contestant spec) explicitly says C
  is given "the harness computes the advisory deterministically (same NAL `Truth_Revision` math the
  production canary uses)" and injects a `materialize_advisory()`-shaped object — this was, per doc
  143's own investigation, a **hand-written Python function** (`contestants.compute_formal_advisory()`
  in `harness/contestants.py`), never the real MeTTa interpreter or the real `grounded_reason` plugin.
  The synthetic world generator (`world_generator.py`) also used field names (`subject_scope`,
  `predicate_aspect` as a top-level synthetic construct, `sim_time`, top-level `confidence`) that do
  not match WorldState's real `Fact` schema (`scope, key, value, observed_at, source`) or the real
  `RelationFact.msg` shape.
- Docs 137–142 (visualization/storyboard/technical-note series) were built to explain this same
  (now-partially-discredited) result to a non-technical audience; they inherit the same fidelity gap
  and should not be cited as independent confirmation.
- Between doc 143 and this document, **nothing else changed**: no file in the research directory is
  newer than doc 143; no code was written; the production containers are unchanged (confirmed §3); no
  decision on doc 143's own Option A/B/C question has been recorded anywhere I could find.

**Net effect for the upcoming benchmark round**: the prior round's headline number (+8.2pp overall,
+86.7pp on the conflict family, p<0.001) should be treated as **evidence about the formula's isolated
behavior when correctly triggered**, not yet as evidence that the *real* MeTTa/PeTTa runtime, invoked
through the real ingestion and reasoning code paths, reproduces the same result. That is precisely
the open question the new B0/B1/C round exists to close.

---

## 6. Constraints that must inform how the new real-Omega-MeTTa benchmark is built

From doc 143 §4/§5/§6 (investigation + explicit constraints) and the canonical guardrails:

1. **Never write to the live instance.** `192.168.0.5:8910` is confirmed (doc 143 §4.3, and this
   session's own `docker ps`/log read) to be backed by the real `bison_client-mc_world_state-1` /
   `bison_client-omegaclaw-1` containers. No fabricated benchmark fact may be written into that live
   WorldState/Chroma instance — risk of a real robot acting on fake facts. This is a hard constraint,
   not a preference (doc 143 §6, echoing the project's own standing "never crash / never risk the
   shared host" rules).
2. **Real schema, not invented field names.** WorldState's real `Fact` dataclass
   (`mc_world_state/mc_world_state/store.py`) is `{scope, key, value, observed_at, source}`; the real
   write surface is the ROS2 service `mc_one/srv/UpdateWorldFacts.srv`. A second real shape,
   `mc_one/msg/RelationFact.msg`, covers `subject_id/predicate/object_id/certainty/confidence/
   observed_at/ttl_sec/source/evidence_json`. Any new benchmark's synthetic facts must be constructed
   in one of these real shapes, not a bespoke format.
3. **Real reasoning engine, not a formula reimplementation.** The real, callable entry point is
   `overlay/plugins/grounded_reason/grounded_reason.py`'s `grounded_reason(premise_ref_1, premise_ref_2,
   operator)`, which resolves premises from real Chroma collections, runs
   `grounded_proposition.classify_claim()` (the real admission/epistemic gate), builds MeTTa code via
   `OPERATOR_TEMPLATES["revision"] = "(|- {p1} {p2})"`, and evaluates it through the real PeTTa/MeTTa
   interpreter (pinned commit `642c53676cf795cb7a0030823b36018c029b1416`), which only exists inside an
   OmegaClaw-Core container. This is already known to be invocable standalone — a precedent exists
   (`OVERNIGHT_GROUNDED_FORMAL_20260921_0334/harness/abc_harness.py`'s `run_mode_c_formal_step()`)
   that imports and calls the real, unmodified function in-process from inside the omegaclaw
   container.
4. **Real ingestion path, not prompt-string assembly.** Fabricated facts must be fed in via the real
   ingestion functions (`observation_memory.py`'s `record_world_event()` / the real WorldState update
   handler), not hand-assembled directly into an LLM prompt string, per the user's own explicit
   requirement (doc 143 §3, verbatim Chinese quote translated: synthetic *values* are fine, a
   standalone reimplementation is not).
5. **A safe isolation precedent already exists and does not require inventing a new mechanism**:
   WorldState side — `mc_world_state/tests/test_update_facts_scope_guard.py` already instantiates a
   fresh in-process `WorldStateStore()` and calls the real, unbound `_handle_update_facts()` with zero
   ROS2/Docker/shared state. Omega side — `observation_memory.py`, `mission_memory.py`,
   `persistent_goals.py`, `grounded_reason.py` all read `CHROMA_PATH` from an overridable env var
   specifically so tests can redirect it. The **remaining open gap** (unresolved by doc 143, this is
   the actual decision GPT was asked to make) is how to get a real MeTTa `(eval ...)` step running
   against that isolated data without touching the live container's process/state — the three options
   doc 143 lays out (A: stop short of real MeTTa eval, verify constructed code numerically instead; B:
   stand up a second, fully isolated omegaclaw container with a new `MC_DOMAIN`/port; C: reuse the
   live container's interpreter process via `docker exec` with a temporarily monkeypatched
   `CHROMA_PATH`, judged by doc 143 itself as needing careful thread-safety review before being judged
   safe).
6. **CHANGE APPROVAL discipline still applies.** Per `ENGINEERING_GUARDRAILS.md` §9, any actual
   construction (not just benchmark harness code, but especially anything that touches a second
   container, a new compose project, or a monkeypatch against the live process) needs its own CHANGE
   APPROVAL with confirmed root cause / owning layer / rollback condition before implementation, not
   just an internal research decision.
7. **Mature-solution-first / no scope creep**: doc 136 already independently found (via the
   *fabricated* C, so this specific number should be treated as unconfirmed pending the real-engine
   rebuild, not re-litigated) that the correct product scope is narrow — revision-only, WORLD_EVENT-
   only, opposing-value-only. The new benchmark's job is to verify this holds with the *real* engine,
   not to expand scope to other operators while doing so (`ENGINEERING_GUARDRAILS.md` §3/§6: new
   mechanisms need their own gate; multi-layer changes are a danger signal).

---

## 7. Explicit list of what could NOT be verified this session (UNKNOWN)

- **Whether `grounded_reason`/`query_observation_claims` have been genuinely invoked (not just
  mentioned in a reprinted skill description) in production since the 2026-09-26 deploy.** Log
  keyword counts are dominated by repeated prompt-dump text; a proper log-format-aware parse was not
  attempted this session.
- **Whether a robot is currently connected to the live channel right now, at the moment this document
  is being written.** The only direct evidence (one "dropped, no robot connected" message at boot,
  never repeated) is consistent with either "a robot connected later and no further drops occurred" or
  "no further connection attempts were logged" — I could not distinguish these from the logs
  available, and did not query the robot-channel port directly (out of scope for a read-only
  documentation pass, and doing so risks interacting with a live system unexpectedly).
- **Exact current dollar/call budget remaining for further real-provider benchmark work.** Several
  historical docs (e.g. `CURRENT_AUTONOMOUS_REPAIR_STATE.md`'s "20/30 HARD_MAX") describe budget
  ledgers as session-scoped and non-additive; no single current authoritative "remaining budget for
  the next round" figure was found.
- **Whether GPT (or any other external reviewer) has actually responded to doc 143's decision request**
  outside this workspace (e.g. in a chat thread not saved to disk). No file newer than doc 143 exists
  in the research directory, but a verbal/external decision could exist that simply hasn't been written
  back yet — I cannot rule this out from local files alone.
- **Whether the untracked/uncommitted plugin directories in `/home/mindbot/Workspace/omegaclaw-core-
  fork` (§3) are byte-identical to what's actually running inside `bison_client-omegaclaw-1` right
  now**, versus merely being the source that was *once* built into it. Doc 125 did verify this
  byte-for-byte for `grounded_reason.py`/`.metta` specifically at deploy time; I did not re-run that
  same hash comparison this session (it would require `docker exec` into the running container, which
  I judged unnecessary read-only risk beyond what this re-anchor task required, given doc 125 already
  did it rigorously 2 days ago and RestartCount=0 since).
- **The exact current relationship between this research thread's local `harness/` directory
  (`omega_long_horizon_belief_scaling_v1_20260926/harness/`) and any newer/different harness that a
  next session might build for the real-engine version.** No such new harness exists yet (confirmed:
  the only harness present is the one that produced the now-partially-discredited docs 132/133
  results).
- **Full current $ / token cost of the eventual real-MeTTa-engine benchmark**, since its design
  (Option A vs B vs C from doc 143) is not yet chosen — cost depends entirely on which option is
  chosen, which is itself the open decision.

---

## Sources read this session

`mc_dashboard/CLAUDE_REVIEW_PACKAGE_2026-09-28/canonical_docs/{MASTER_HANDOFF_FINAL,
ENGINEERING_GUARDRAILS,CURRENT_STATE_DELTA,ARCHITECTURE_AMENDMENT_2026-09-06,SESSION_DELTA_2026-09-21,
MASTER_CONSTRUCTION_ROADMAP_TO_IDEAL_2026-09-08,NEW_CHAT_EXHAUSTIVE_HANDOFF,
READING_MAP_AND_MATERIALS,TECH_ROUTE_TURNING_POINT_2026-09-06,
LATEST_CODE_PROVENANCE_AND_DRIVE_LINK}.md` (all present, all dated 2026-09-28 in that directory, no
fallback to `z——doc/` or `CANONICAL_DOCS_2026-09-06 (2)/` needed — every file the task asked for
existed in the primary location); `research/omega_incremental_value_v1_20260924/{125_STAGE10_
BOUNDED_CANARY_LIVE_DEPLOYMENT,CURRENT_AUTONOMOUS_REPAIR_STATE}.md` (no doc numbered above 125 exists
in that directory — confirmed by directory listing); `research/omega_long_horizon_belief_scaling_v1_
20260926/{129_LONG_HORIZON_EXPERIMENT_SPEC,130_LONG_HORIZON_SCORING_CONTRACT,
136_OMEGA_PRODUCT_THESIS_VERDICT,143_REAL_SYSTEM_GROUNDING_DECISION_REQUEST}.md` plus a directory
listing of the other docs 126–142; live commands: `docker ps`, `docker inspect` (omegaclaw-1,
mc_world_state-1), `docker logs` (full + targeted greps), `git status`/`git log` in
`omegaclaw-core-fork`, and direct reads of `compose.yaml`, `.env`, `context/ai_bt_missions.jsonl`,
`omegaclaw-memory/observation_memory.log`.
