"""grounded_reason: the Stage 10 LLM-facing formal-reasoning skill
(Cognitive Run V18, Change Approval -- activation conditions met, see
V18_GENERIC_EXECUTION_TRUST_BOUNDARY.md).

Replaces the generic `metta` skill (now blocked from the robot LLM
capability profile by robot_capability_profile.metta) as the ONLY
LLM-reachable path to NAL/PLN formal reasoning. The LLM never supplies a
raw MeTTa expression or a raw (stv f c) truth value -- it may only name
which two already-admitted machine claims to reason over and which
operator to apply.

Input: premise_ref_1 (str), premise_ref_2 (str), operator (str, one of
the Stage-9-qualified operators: revision, deduction, pln_forward,
pln_abduction).

Premise resolution (server-side, never LLM-authored):
1. Each premise_ref is looked up against the real Chroma collections
   this deployment actually has (mission_claims_v1, persistent_goals_v1,
   observation_claims_v1) by matching provenance_ref.
2. The resolved record is classified via grounded_proposition.classify_claim().
3. Only a claim with reasoning_eligible=True may become a premise --
   this is the same Stage 8 admission gate everything else in this
   arc already goes through, reused rather than duplicated.
4. The claim's own type-specific fields (never an LLM-supplied number)
   determine its NAL statement + stv:
     ROBOT_OBSERVED: (--> <subject> observed_state_true) (stv <0|1 from actual
       recorded state> <confidence>) -- frequency now genuinely reflects the
       claim's own recorded polarity (Grounded Proposition contract repair,
       this round); a FALSE finding renders as frequency 0.0, never silently
       upgraded to a positive atom.
     WORLD_EVENT: (--> <subject> event_occurred_<predicate>|state_<predicate>)
       (stv <0|1 from polarity> <confidence>) -- the generic non-camera
       counterpart admitted via observation_memory.record_world_event();
       predicate_aspect (EVENT vs STATE) selects the relation shape.
     MISSION_RESULT: (--> <subject> mission_<terminal_state>) (stv 1.0 0.9)
     PERSISTENT_GOAL_STATE: (--> <subject> goal_status_<status>) (stv 1.0 0.9)
   (0.9 is a fixed, disclosed default confidence-in-the-record-itself for
   MISSION_RESULT/PERSISTENT_GOAL_STATE, which carry no native continuous
   confidence of their own; ROBOT_OBSERVED/WORLD_EVENT instead use their own
   recorded confidence field. An UNKNOWN/unrepresented state resolves to no
   statement at all -- fail closed, never an invented polarity.)

The actual metta code string is constructed entirely here, server-side,
from these resolved values -- never from LLM text. It is evaluated via
grounded_reason.metta's own direct sread/eval/swrite equation (NOT the
blocked `metta` skill -- confirmed this round that blocking `metta`'s
own equation does not affect the underlying native sread/eval/swrite
primitives grounded_reason.metta calls directly).

Output always carries authority="NONE" -- a hardcoded constant, never
derived from engine output (same invariant the V14 TEMP prototype and
this arc's whole Stage 9 adapter already established).
"""
import fcntl
import json
import os
import re
import threading

try:
    import chromadb
except Exception:  # pragma: no cover - exercised only inside the real container
    chromadb = None

import grounded_proposition

CHROMA_PATH = "/PeTTa/repos/OmegaClaw-Core/memory/chroma_db"
COLLECTIONS = ["mission_claims_v1", "persistent_goals_v1", "observation_claims_v1"]

OPERATOR_TEMPLATES = {
    "revision": "(|- {p1} {p2})",
    "deduction": "(|- {p1} {p2})",
    "pln_forward": "(|~ {p1} {p2})",
    "pln_abduction": "(|~ {p1} {p2})",
}

STV_RE = re.compile(r"\(stv\s+([\d.eE+-]+)\s+([\d.eE+-]+)\)")

_client = None
# See persistent_goals.py's own module-level comment for the full
# reproduction/rationale (chromadb's Rust client is not thread-safe for
# concurrent access to the same collection object) -- applied defensively
# here, not from a reproduced failure in this specific plugin.
_chroma_lock = threading.RLock()

def _new_chroma_client():
    """See persistent_goals.py's own _new_chroma_client() for the full
    rationale: a flock on a path shared by every plugin pointed at this
    same CHROMA_PATH, closing the cross-plugin chromadb tenant-init race
    (confirmed live) that a per-module _chroma_lock cannot reach. Reads
    CHROMA_PATH fresh on every call (not a frozen constant) so tests that
    reassign it for isolation still lock a matching path."""
    lock_path = CHROMA_PATH.rstrip("/") + ".init.lock"
    lock_dir = os.path.dirname(lock_path) or "."
    os.makedirs(lock_dir, exist_ok=True)
    with open(lock_path, "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            return chromadb.PersistentClient(path=CHROMA_PATH)
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _get_client():
    global _client
    with _chroma_lock:
        if _client is None and chromadb is not None:
            _client = _new_chroma_client()
        return _client


def _find_by_provenance_ref(ref):
    """Look up a single record across the real collections whose own
    provenance identity matches `ref`. Returns (collection_name, claim)
    or None. Never invents a match."""
    client = _get_client()
    if client is None:
        return None
    for cname in COLLECTIONS:
        try:
            with _chroma_lock:
                col = client.get_collection(cname)
        except Exception:
            continue
        with _chroma_lock:
            r = col.get(include=["metadatas", "documents"])
        for i, rid in enumerate(r["ids"]):
            meta = r["metadatas"][i] or {}
            doc = json.loads(r["documents"][i]) if r.get("documents") and r["documents"][i] else {}
            candidate_refs = []
            if cname == "mission_claims_v1":
                candidate_refs.append(f"journal_offset:{meta.get('journal_offset')}")
                candidate_refs.append(f"mission_id:{meta.get('mission_id')}")
            elif cname == "persistent_goals_v1":
                candidate_refs.append(f"goal_id:{meta.get('goal_id')}")
            elif cname == "observation_claims_v1":
                candidate_refs.append(f"obs:{meta.get('observation_id')}")
            if ref in candidate_refs:
                return cname, meta, doc
    return None


def _to_claim(cname, meta, doc):
    if cname == "mission_claims_v1":
        return {
            "input_claim_type": "MISSION_RESULT", "record_provenance_kind": "DURABLE_MACHINE_CLAIM",
            "raw_claim": {"terminal_state": meta.get("terminal_state") or doc.get("terminal_state")},
            "source_ref": "mission_claims_v1", "provenance_ref": [f"journal_offset:{meta.get('journal_offset')}"],
            "observed_at": None, "semantic_entity_id": meta.get("semantic_entity_id") or None,
            "subject_scope": meta.get("mission_id") or "mission_x",
        }
    if cname == "persistent_goals_v1":
        return {
            "input_claim_type": "PERSISTENT_GOAL_STATE", "record_provenance_kind": "DURABLE_MACHINE_CLAIM",
            "raw_claim": {"status": meta.get("status") or doc.get("status")},
            "source_ref": "persistent_goals_v1", "provenance_ref": [f"goal_id:{meta.get('goal_id')}"],
            "observed_at": None, "semantic_entity_id": None,
            "subject_scope": meta.get("goal_id") or "goal_x",
        }
    if cname == "observation_claims_v1":
        claim_kind = meta.get("claim_kind") or "ROBOT_OBSERVED"
        if claim_kind == "WORLD_EVENT":
            # Grounded Proposition contract completion (Change Approval, this round): the
            # generic WORLD_EVENT counterpart to ROBOT_OBSERVED, sharing the SAME collection
            # and provenance-ref scheme -- see observation_memory.record_world_event().
            return {
                "input_claim_type": "WORLD_EVENT", "record_provenance_kind": "DURABLE_MACHINE_CLAIM",
                "raw_claim": {
                    "confidence": meta.get("confidence"),
                    # actual recorded polarity ("true"/"false") -- never hardcoded
                    "state": meta.get("polarity"),
                    # TRUTH-SAFETY FIX (doc 119): preserve a genuinely absent predicate_aspect as
                    # "UNKNOWN", never fabricate "STATE" -- _resolve_premise_claim() below fails
                    # closed on this value; this is the SECOND of two independent fallback points
                    # doc 119 found and fixed together (observation_memory.py's own write-time
                    # fallback is the first -- fixing only one alone would leave the other
                    # independently reintroducing the same collapse).
                    "predicate_aspect": meta.get("predicate_aspect") or "UNKNOWN",
                    "event_kind": meta.get("predicate") or None,
                },
                "source_ref": "observation_claims_v1", "provenance_ref": [f"obs:{meta.get('observation_id')}"],
                "observed_at": meta.get("observed_at"), "semantic_entity_id": meta.get("semantic_entity_id") or None,
                "subject_scope": meta.get("subject") or "event_x",
                "claim_kind": "WORLD_EVENT", "predicate": meta.get("predicate") or "",
            }
        return {
            "input_claim_type": "ROBOT_OBSERVED", "record_provenance_kind": "DURABLE_MACHINE_CLAIM",
            "raw_claim": {
                "confidence": meta.get("confidence"),
                # P0 truth-safety fix: this field was always present in observation_memory's
                # own metadata (record_observation() has always written it) but was never
                # read here -- _statement_for() below hardcoded state="true" regardless of
                # what was actually observed, silently turning a FALSE finding into a
                # positive atom.
                "state": meta.get("state"),
            },
            "source_ref": "observation_claims_v1", "provenance_ref": [f"obs:{meta.get('observation_id')}"],
            "observed_at": meta.get("observed_at"), "semantic_entity_id": meta.get("semantic_entity_id") or None,
            "subject_scope": meta.get("observation_id") or "obs_x",
            "claim_kind": "ROBOT_OBSERVED",
        }
    return None


def _truth_frequency(state_value):
    """Shared polarity resolution -- one place both claim kinds go through so TRUE/
    FALSE/UNKNOWN handling can't silently diverge between them again. Returns
    (frequency, resolved); resolved=False means the state is genuinely unrepresented
    and must fail closed, never default to true."""
    if state_value is None:
        return None, False
    s = str(state_value).strip().lower()
    if s in ("true", "1", "yes"):
        return 1.0, True
    if s in ("false", "0", "no"):
        return 0.0, True
    return None, False


def _statement_for(cname, claim):
    subject = claim["subject_scope"]
    if cname == "mission_claims_v1":
        ts = (claim["raw_claim"].get("terminal_state") or "unknown").lower()
        return f"(--> {subject} mission_{ts}) (stv 1.0 0.9)"
    if cname == "persistent_goals_v1":
        st = (claim["raw_claim"].get("status") or "unknown").lower()
        return f"(--> {subject} goal_status_{st}) (stv 1.0 0.9)"
    if cname == "observation_claims_v1":
        conf = claim["raw_claim"].get("confidence")
        conf = conf if isinstance(conf, (int, float)) else 0.5
        freq, resolved = _truth_frequency(claim["raw_claim"].get("state"))
        if not resolved:
            # Fail closed: an UNKNOWN/unrepresented state must never silently become a
            # positive (or negative) atom -- no statement is safer than an invented one.
            return None
        if claim.get("claim_kind") == "WORLD_EVENT":
            aspect = claim["raw_claim"].get("predicate_aspect") or "STATE"
            predicate = claim.get("predicate") or "event"
            relation = f"event_occurred_{predicate}" if aspect == "EVENT" else f"state_{predicate}"
            return f"(--> {subject} {relation}) (stv {freq} {conf})"
        # ROBOT_OBSERVED: polarity now genuinely preserved instead of the pre-repair
        # hardcoded "true".
        return f"(--> {subject} observed_state_true) (stv {freq} {conf})"
    return None


_VALID_WORLD_EVENT_PREDICATE_ASPECTS = {"EVENT", "STATE"}


def _resolve_premise_claim(ref):
    """Looks up and classifies a single premise_ref's underlying claim, without
    yet rendering it to a NAL statement. Factored out of _resolve_premise() so
    the Stage-10 bounded-canary eligibility gate (grounded_reason_resolve_json,
    CHANGE APPROVAL 115) can inspect a claim's own raw fields (subject_scope,
    predicate, predicate_aspect, input_claim_type) BEFORE rendering -- one
    lookup/classification path, reused, not duplicated.

    TRUTH-SAFETY FIX (WORLD_EVENT_UNKNOWN_PREDICATE_ASPECT_COLLAPSED_TO_STATE, doc
    119): grounded_proposition.classify_claim() (FROZEN, not modified) has never
    independently validated predicate_aspect for a WORLD_EVENT claim -- only
    predicate presence. Combined with two now-fixed data-fabrication points
    (observation_memory.py's own write-time fallback and _to_claim()'s own
    read-time fallback, both formerly "or STATE"), an admitted WORLD_EVENT claim
    could reach every caller of this function with a predicate_aspect that was
    never actually supplied. This check closes that gap HERE -- the nearest
    point this round's own authorized files can add an admission-equivalent
    fail-closed rule without touching the frozen grounded_proposition.py itself.
    Applies to EVERY caller (internal engine and the JSON wrapper alike) -- this
    is a general truth-safety fix, not a production-canary-only narrowing."""
    found = _find_by_provenance_ref(ref)
    if found is None:
        return None, "UNKNOWN_PREMISE_REF"
    cname, meta, doc = found
    claim = _to_claim(cname, meta, doc)
    classification = grounded_proposition.classify_claim(claim)
    if not classification["reasoning_eligible"]:
        return None, "PREMISE_NOT_ADMITTED"
    if claim.get("input_claim_type") == "WORLD_EVENT":
        aspect = claim["raw_claim"].get("predicate_aspect")
        if aspect not in _VALID_WORLD_EVENT_PREDICATE_ASPECTS:
            return None, "PREMISE_PREDICATE_ASPECT_UNKNOWN"
    return claim, None


def _resolve_premise(ref):
    claim, err = _resolve_premise_claim(ref)
    if err:
        return None, err
    stmt = _statement_for(claim["source_ref"], claim)
    if stmt is None:
        return None, "UNSUPPORTED_CLAIM_SHAPE"
    return stmt, None


def grounded_reason(premise_ref_1, premise_ref_2, operator):
    if operator not in OPERATOR_TEMPLATES:
        return {"result": None, "premise_refs": [premise_ref_1, premise_ref_2], "authority": "NONE",
                "error_code": "UNSUPPORTED_OPERATOR"}
    if not premise_ref_1 or not premise_ref_2:
        return {"result": None, "premise_refs": [premise_ref_1, premise_ref_2], "authority": "NONE",
                "error_code": "UNKNOWN_PREMISE_REF"}

    stmt1, err1 = _resolve_premise(premise_ref_1)
    if err1:
        return {"result": None, "premise_refs": [premise_ref_1, premise_ref_2], "authority": "NONE", "error_code": err1}
    stmt2, err2 = _resolve_premise(premise_ref_2)
    if err2:
        return {"result": None, "premise_refs": [premise_ref_1, premise_ref_2], "authority": "NONE", "error_code": err2}

    code = OPERATOR_TEMPLATES[operator].format(p1=f"({stmt1})", p2=f"({stmt2})")
    return {
        "metta_code": code, "premise_refs": [premise_ref_1, premise_ref_2],
        "operator": operator, "authority": "NONE", "error_code": None,
    }


def grounded_reason_resolve(premise_ref_1, premise_ref_2, operator):
    """Thin wrapper for the .metta layer: returns either the constructed
    metta code string (starts with "(", safe to eval directly) or an
    "ERR:<code>" string the .metta layer maps to an (Error ...) term --
    avoids needing dict/JSON marshalling across the py-call boundary."""
    result = grounded_reason(premise_ref_1, premise_ref_2, operator)
    if result.get("error_code"):
        return f"ERR:{result['error_code']}"
    return result["metta_code"]


_GROUNDED_REASON_JSON_KEYS = {"premise_ref_1", "premise_ref_2", "operator"}

# STAGE-10 BOUNDED REVISION CANARY (CHANGE APPROVAL 115, autonomous finalization,
# 2026-09-26): the production, LLM-facing wrapper below exposes ONLY `revision` --
# the sole operator with real, repeated E2E product evidence (4 independent complete
# formal-path witnesses, all `revision`). `deduction`/`pln_forward`/`pln_abduction`
# remain fully available to internal/dev/research callers that use
# grounded_reason()/grounded_reason_resolve() directly (unchanged, not touched by
# this gate) -- only this JSON wrapper, the one real LLM-reachable surface, is
# narrowed.
_STAGE10_CANARY_ALLOWED_OPERATORS = {"revision"}


def _revision_eligible(claim1, claim2):
    """Stage-10 bounded-canary eligibility gate (CHANGE APPROVAL 115, narrowed by
    118): the empirically-validated production class is two WORLD_EVENT claims
    describing the EXACT SAME proposition -- same subject, same predicate, same
    predicate_aspect -- matching grounded_reason.metta's own skill-description
    text verbatim ("revision... combines two premises that describe the EXACT
    SAME thing") -- AND genuinely OPPOSING values (CHANGE APPROVAL 118): this
    thread's own real E2E evidence is 4/4 opposing-value conflicts; a same-value
    pair (confidence-boosting), while a real, documented, mathematically valid
    use of `revision` in general, has never been independently real-E2E-tested
    for THIS production canary, so it is narrowed out here specifically --
    `grounded_reason_resolve()` (the internal/dev engine) remains fully callable
    with a same-value pair directly, unrestricted, unchanged. Returns
    (eligible: bool, reason: str|None)."""
    if claim1.get("input_claim_type") != "WORLD_EVENT" or claim2.get("input_claim_type") != "WORLD_EVENT":
        return False, "REVISION_REQUIRES_WORLD_EVENT_CLAIMS"
    if claim1.get("subject_scope") != claim2.get("subject_scope"):
        return False, "REVISION_SUBJECT_MISMATCH"
    if claim1.get("predicate") != claim2.get("predicate"):
        return False, "REVISION_PREDICATE_MISMATCH"
    aspect1 = claim1["raw_claim"].get("predicate_aspect") or "STATE"
    aspect2 = claim2["raw_claim"].get("predicate_aspect") or "STATE"
    if aspect1 != aspect2:
        return False, "REVISION_PREDICATE_ASPECT_MISMATCH"
    freq1, resolved1 = _truth_frequency(claim1["raw_claim"].get("state"))
    freq2, resolved2 = _truth_frequency(claim2["raw_claim"].get("state"))
    if not resolved1 or not resolved2:
        return False, "REVISION_REQUIRES_RESOLVED_VALUES"
    if freq1 == freq2:
        return False, "REVISION_REQUIRES_OPPOSING_VALUES_IN_PRODUCTION_CANARY"
    return True, None


def grounded_reason_resolve_json(json_str):
    """ABI REPAIR (GROUNDED_REASON_ARGUMENT_MARSHALLING_INTERFACE_BUG,
    autonomous continuation, 2026-09-26): the original THREE-bare-positional-
    argument form was confirmed (2/2 real LLM traces, seeds 963002/963003) to
    always fail with a metta arity-unification error, the same
    domain_error py_term failure doc 81 recorded for query_observation_claims --
    the core prompt's own generic single-argument-per-tool-call convention
    always collapses the three values into one quoted string. Now takes ONE
    JSON-object-string argument, matching query_observation_claims's own
    already-proven convention (_query_observation_claims_json) exactly --
    same deterministic-parsing discipline (reject unknown keys / wrong types /
    malformed JSON with a typed string, never guess). This is an ABI-only
    repair: delegates to the existing, unchanged grounded_reason_resolve()
    (and therefore the unchanged grounded_reason() core: premise resolution,
    the Stage 8 admission gate, NAL/PLN statement construction, and the
    hardcoded authority="NONE" are none of them touched)."""
    try:
        spec = json.loads(json_str)
    except (TypeError, ValueError, json.JSONDecodeError):
        return "ERR:INVALID_ARGUMENT_MALFORMED_JSON"
    if not isinstance(spec, dict):
        return "ERR:INVALID_ARGUMENT_NOT_A_JSON_OBJECT"

    unknown_keys = set(spec.keys()) - _GROUNDED_REASON_JSON_KEYS
    if unknown_keys:
        return "ERR:INVALID_ARGUMENT_UNKNOWN_KEYS"
    missing_keys = _GROUNDED_REASON_JSON_KEYS - set(spec.keys())
    if missing_keys:
        return "ERR:INVALID_ARGUMENT_MISSING_KEYS"
    premise_ref_1, premise_ref_2, operator = (
        spec.get("premise_ref_1"), spec.get("premise_ref_2"), spec.get("operator"))
    if not all(isinstance(v, str) for v in (premise_ref_1, premise_ref_2, operator)):
        return "ERR:INVALID_ARGUMENT_NON_STRING_VALUE"

    # Stage-10 bounded revision canary (CHANGE APPROVAL 115) -- production-canary-only
    # gates, checked here, never inside grounded_reason()/grounded_reason_resolve()
    # (which internal/dev/research callers use directly, unrestricted, unchanged).
    if operator not in _STAGE10_CANARY_ALLOWED_OPERATORS:
        return "ERR:OPERATOR_NOT_PERMITTED_IN_PRODUCTION_CANARY"

    claim1, err1 = _resolve_premise_claim(premise_ref_1)
    if err1:
        return f"ERR:{err1}"
    claim2, err2 = _resolve_premise_claim(premise_ref_2)
    if err2:
        return f"ERR:{err2}"
    eligible, reason = _revision_eligible(claim1, claim2)
    if not eligible:
        return f"ERR:{reason}"

    return grounded_reason_resolve(premise_ref_1, premise_ref_2, operator)


# FORMAL_RESULT_CONSUMPTION_CONTRACT (CHANGE APPROVAL 122, autonomous finalization, 2026-09-26):
# production canonical guardrail ("raw STV must not be production decision authority without a
# validated consumption contract" -- ENGINEERING_GUARDRAILS.md 2026-09-21 addendum; "raw STV
# consumption can hurt, and an exact-tie interpretation failure remains unresolved" --
# CURRENT_STATE_DELTA.md/NEW_CHAT_EXHAUSTIVE_HANDOFF.md, from this project's own prior confirmatory
# formal-reasoning benchmark) was confirmed, via a real trace (doc 121), to still be live: the raw,
# unlabeled stv(frequency, confidence) text was exposed directly to the LLM with no machine-owned
# interpretation anywhere, and the model mislabeled frequency as confidence in that real completion
# (landed on a safe final action anyway, by luck, not by contract). This wires up STV_RE (defined
# above, never previously referenced anywhere in this file) to close that gap for THIS bounded
# production canary specifically -- NOT a general STV interpreter for arbitrary operators/claim
# shapes, which remains a genuinely open research question this fix deliberately does not attempt
# to solve. Called ONLY from grounded_reason.metta's own equation, ONLY after a successful
# doc-115/118-gated JSON-wrapper revision result -- never from the internal grounded_reason()/
# grounded_reason_resolve() engine, which continues returning raw metta code unchanged for
# internal/dev/research callers using arbitrary operators/claim shapes this fixed label would not
# validly describe.
_MIN_VALID_STV = 0.0
_MAX_VALID_STV = 1.0


def materialize_advisory(raw_result):
    """raw_result: the ALREADY-EVALUATED, UNCHANGED NAL result text (grounded_reason.metta's own
    `(repr (swrite (eval $code)))` -- this function performs NO computation of its own over NAL/PLN
    math; it only parses and labels a value that already exists. Returns a JSON object string (the
    same established interchange convention this codebase already uses for query_observation_claims
    and grounded_reason_resolve_json) starting with "{" on success, or an "ERR:<code>" string on any
    failure -- fail-closed, matching the existing convention exactly, never a guessed/fabricated
    semantic label.

    The semantic label and recommended action are FIXED, not derived from the parsed numbers --
    doc 115's own operator gate and doc 118's own _revision_eligible() gate have ALREADY confirmed,
    before this function is ever reached, that both premises are WORLD_EVENT claims describing the
    exact same proposition with genuinely opposing resolved values. Every successful result
    reaching this function is therefore, by construction, a resolution of two directly-conflicting
    real observations about the same thing -- true regardless of exactly where the resulting
    frequency numerically lands (this sidesteps the general, still-open exact-tie/STV-interpretation
    research question entirely, rather than attempting to solve it)."""
    match = STV_RE.search(raw_result or "")
    if match is None:
        return "ERR:MALFORMED_FORMAL_RESULT_NO_STV_FOUND"
    try:
        frequency = float(match.group(1))
        confidence = float(match.group(2))
    except (TypeError, ValueError):
        return "ERR:MALFORMED_FORMAL_RESULT_UNPARSEABLE_STV"
    for name, value in (("frequency", frequency), ("confidence", confidence)):
        if value != value or value in (float("inf"), float("-inf")):  # NaN/inf check, no math.isnan dependency
            return f"ERR:MALFORMED_FORMAL_RESULT_{name.upper()}_NOT_FINITE"
        if value < _MIN_VALID_STV or value > _MAX_VALID_STV:
            return f"ERR:MALFORMED_FORMAL_RESULT_{name.upper()}_OUT_OF_RANGE"

    return json.dumps({
        "frequency": frequency,
        "confidence": confidence,
        "epistemic_interpretation": "UNRESOLVED_CONFLICT_BETWEEN_OPPOSING_GROUNDED_CLAIMS",
        "recommended_cognitive_action": "ESCALATE_OR_RECHECK",
        "authority": "NONE",
    }, sort_keys=True)
