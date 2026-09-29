# 149. Real MeTTa End-to-End Witness ($0, No Handwritten Revision Math)

## Acceptance criteria (from the governing directive) and result

- NO handwritten revision math: **PASS** — the numeric result was computed by evaluating real,
  unmodified `lib_nal.metta` code (`Truth_Revision`), not by any Python formula written for this
  benchmark.
- NO hard-coded STV: **PASS**.
- NO live DB touch: **PASS** — isolated scratch Chroma path only (doc 147).
- NO production mutation: **PASS** — `bison_client-omegaclaw-1` RestartCount and image unchanged
  before/after (re-verified after this witness ran).

## The witness case

`door_1 / locked / STATE`: claim 1 = TRUE, confidence 0.80; claim 2 = FALSE, confidence 0.80 (the
exact geometry the directive's own section 23 specifies).

## Step-by-step, all real code, all captured verbatim

**1. Real ingestion** (`observation_memory.record_world_event()`, run via plain `python3` inside the
isolated container):
```python
record_world_event({"event_id": "witness_claim_true_001", "subject": "door_1", "predicate": "locked",
  "value": True, "source_type": "SENSOR_OBSERVATION", "source_id": "witness_sensor_a",
  "observed_at": 1000.0, "confidence": 0.80, "predicate_aspect": "STATE", "semantic_entity_id": ""})
# -> True
record_world_event({"event_id": "witness_claim_false_001", ..., "value": False, ..., "observed_at": 1001.0,
  "confidence": 0.80, ...})
# -> True
```
Both calls returned `True`. A real `chroma.sqlite3` (188KB) was created in the scratch directory.

**2. Real premise resolution + admission + eligibility** (direct Python call, same process family,
before invoking MeTTa at all — confirms the earlier stages independently):
```
_find_by_provenance_ref("obs:witness_claim_true_001")  -> found, real metadata round-tripped correctly
_resolve_premise_claim(...)                             -> admitted, err=None (both claims)
_revision_eligible(claim1, claim2)                      -> (True, None)
grounded_reason_resolve_json({...operator:"revision"})  ->
  "(|- ((--> door_1 state_locked) (stv 1.0 0.8)) ((--> door_1 state_locked) (stv 0.0 0.8)))"
```

**3. Real MeTTa evaluation** — this is the step the PRIOR long-horizon benchmark (docs 126-143) never
performed; its own "C" used a Python function reproducing the formula's shape instead. Invoked via:
```
swipl --stack_limit=8g -q -s /PeTTa/src/main.pl -- /PeTTa/witness_eval.metta
```
which loads (in order) `lib_nal` (defines `Truth_Revision`/`|-nal`/`|-`), `src/skills.metta` (defines
the `first_char` Prolog helper `grounded_reason.metta`'s own equation depends on), `observation_memory.py`,
`grounded_proposition.py`, then `grounded_reason.metta` itself (real, unmodified), then evaluates:
```
!(grounded_reason "{\"premise_ref_1\":\"obs:witness_claim_true_001\",\"premise_ref_2\":\"obs:witness_claim_false_001\",\"operator\":\"revision\"}")
```

**Real result**:
```
(GroundedReasonResult
  "(swrite (((--> door_1 state_locked) (stv 0.5 0.888888888888889)) ...6 other inference-rule matches...))"
  (advisory {"authority": "NONE", "confidence": 0.888888888888889,
             "epistemic_interpretation": "UNRESOLVED_CONFLICT_BETWEEN_OPPOSING_GROUNDED_CLAIMS",
             "frequency": 0.5, "recommended_cognitive_action": "ESCALATE_OR_RECHECK"})
  (input "{...}") (authority NONE))
```

## Independent arithmetic verification (this is really NAL's `Truth_Revision`, not a fluke)

`lib_nal.metta`'s real formula: `w1 = c2w(c1)`, `w2 = c2w(c2)`, `w = w1+w2`,
`f = (w1*f1 + w2*f2)/w`, `c = w2c(w)`, output `stv(min(1,f), min(0.99, max(max(c,c1),c2)))`. Standard
NAL constants (`c2w(c) = c/(1-c)`, `w2c(w) = w/(w+1)`, i.e. `k=1`): `w1 = w2 = 0.8/0.2 = 4.0`,
`w = 8.0`, `f = (4*1.0 + 4*0.0)/8.0 = 0.5`, `c = 8.0/9.0 = 0.888...`. **Matches the engine's real output
exactly** — independent confirmation this is genuine NAL arithmetic, not a coincidental regex match.

## Real, disclosed discrepancy vs. the prior benchmark's Python approximation

The prior benchmark's `contestants.compute_formal_advisory()` used
`confidence = (c1+c2)/(1+c1*c2)`. For this exact geometry (c1=c2=0.8): `(0.8+0.8)/(1+0.64) = 1.6/1.64 =
0.9756`. **The real engine gives 0.8889, not 0.9756** — a genuinely different number, ~9pp off, for the
symmetric-0.8 geometry specifically. (The approximation's own docstring cited a 0.95/0.95 case giving
~0.974, which the real formula would also compute differently: `w1=w2=19.0, w=38.0, c=38/39=0.974` — that
specific high-confidence case does match closely, but the approximation does not generalize correctly to
other confidence levels, as this exact 0.8/0.8 counter-example shows.) This is disclosed here, not
smoothed over: it is real evidence for *why* this replication round matters — the prior "C" was closer
to right at one specific confidence level and measurably wrong at another.

## Two real bugs found and fixed during this witness (root-caused, not papered over)

1. **`ModuleNotFoundError: No module named 'grounded_proposition'`** on the first attempt: `py-call`
   only auto-adds the directly-imported `.py` file's own directory to `sys.path`, not its sibling
   plugins' directories. Production works because its full boot sequence (`lib_omegaclaw.metta`)
   imports every plugin in `plugins.yaml`'s declared order (`observation_memory` → `grounded_proposition`
   → `grounded_reason`), so each plugin's directory is already on `sys.path` by the time a later plugin
   needs it. Fix: explicitly import `observation_memory.py` and `grounded_proposition.py` first, in
   that same real declared order (confirmed from the live container's own
   `config/plugins.yaml`), before importing `grounded_reason.metta`.
2. **`eval` silently no-op'd, `materialize_advisory` parsed the wrong (input, not output) STV**: the
   first successful-looking run returned `frequency:1.0, confidence:0.8` — literally just claim 1's own
   raw input values, because `(eval $code)` had nothing to evaluate against: `lib_nal.metta` (which
   defines what the `|-` revision operator actually *means*) was never imported, so `eval` passed the
   unrecognized term through unchanged, and the regex-based `materialize_advisory()` happened to
   pattern-match the first `(stv ...)` substring in the *un-evaluated* code string. Fix: explicitly
   import `(library OmegaClaw-Core lib_nal)` before evaluating. Caught by the independent arithmetic
   check above (the "result" didn't match what Truth_Revision should produce for a symmetric 0.8/0.8
   pair), not assumed correct because the wrapper returned a well-formed JSON object.

Both fixes are additive imports only (no modification to any real plugin file); both are disclosed here
precisely because a benchmark that silently produced a subtly-wrong-but-well-formed advisory would have
been a much worse failure mode than a `ModuleNotFoundError`.

## What this witness proves

The complete chain — real ingestion function → real Chroma storage → real premise lookup → real
admission gate → real Stage-10 eligibility gate → real MeTTa code construction → real PeTTa/SWI-Prolog
`sread/eval/swrite` → real `Truth_Revision` NAL arithmetic → real `materialize_advisory` — is now proven
executable, in full, in an isolated environment, with zero production contact, for $0. The confirmatory
benchmark's Arm C (doc 148 onward) will invoke exactly this same chain, varying only the injected claims
per case.
