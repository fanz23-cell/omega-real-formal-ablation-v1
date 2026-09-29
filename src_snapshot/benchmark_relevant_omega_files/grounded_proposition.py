"""grounded_proposition: deterministic, read-only epistemic/admission
classification for claims Omega's other plugins already hold, before any
of them may become a premise for formal (NAL/PLN) reasoning.

Ownership and scope (Cognitive Run V17, Change Approval A -- GRANTED):
this module classifies; it never writes, never queries a live source
itself, and never accepts an LLM-authored evidence value. Callers
(mission_memory, persistent_goals, observation_memory, and the planned
grounded_reason skill) pass in a claim dict already read from their own
collection or already obtained from an actual authoritative live query
(e.g. entity_identity.resolve_semantic_entity()); this module only
decides what epistemic weight that claim is allowed to carry.

The single rule this module exists to enforce (Cognitive Run V15's own
confirmed correction -- see STAGE8_VALIDITY_PROVENANCE_AUDIT_V15.md /
CURRENT_PHYSICAL_AUTHORITY_SURFACE_AUDIT_V15.md): a durable machine
record's own age is NEVER evidence of current physical truth. The ONLY
path to physical_authority="CURRENT_AUTHORITATIVE_WHILE_VALID" is a
claim whose record_provenance_kind is CURRENT_AUTHORITATIVE_QUERY_RESULT
-- i.e. the caller actually invoked the real owning surface (WorldState/
Identity's own resolve_semantic_entity()/localize_object equivalent)
moments ago, not a value read back out of any Chroma collection. A
mission execution receipt (MISSION_RESULT) and a persistent goal's own
status (PERSISTENT_GOAL_STATE) are never physical claims at all --
Omega's own historical/cognitive record, unaffected by this correction.

record_provenance_kind (required on every claim):
  DURABLE_MACHINE_CLAIM              -- read from any stored collection
  CURRENT_AUTHORITATIVE_QUERY_RESULT -- a live call, just now
  SOURCE_FAILURE                     -- the source could not answer at all

input_claim_type: MISSION_RESULT | PERSISTENT_GOAL_STATE |
ROBOT_OBSERVED | WORLD_EVENT | IDENTITY | CONFLICT

Output: {epistemic_class, freshness_class, admission_result,
physical_authority, reasoning_eligible}.
"""
import math
import time

_VALID_OPERATORS_NOTE = None  # this module has no operator concept; see grounded_reason


def _result(epistemic_class, freshness_class, admission_result, physical_authority, reasoning_eligible):
    return {
        "epistemic_class": epistemic_class,
        "freshness_class": freshness_class,
        "admission_result": admission_result,
        "physical_authority": physical_authority,
        "reasoning_eligible": reasoning_eligible,
    }


def _is_bad_number(x):
    return not isinstance(x, (int, float)) or isinstance(x, bool) or (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def classify_claim(claim, now=None):
    """claim: dict with keys input_claim_type, record_provenance_kind,
    raw_claim, subject_scope, semantic_entity_id, live_entity_id,
    source_ref, provenance_ref, observed_at, ingest_time. `now` is
    injectable for tests; defaults to the real wall clock."""
    now = time.time() if now is None else now
    ct = claim.get("input_claim_type")
    rpk = claim.get("record_provenance_kind")
    raw = claim.get("raw_claim") or {}
    source_ref = claim.get("source_ref")
    provenance_ref = claim.get("provenance_ref") or []
    observed_at = claim.get("observed_at")
    semantic_entity_id = claim.get("semantic_entity_id")

    if source_ref in ("UNAVAILABLE", "TIMEOUT", "MISSING_COLLECTION"):
        return _result("UNKNOWN", "unknown", "UNKNOWN", "NONE", False)
    if source_ref == "MALFORMED":
        return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
    if source_ref == "PARTIAL_RESULT":
        return _result("UNKNOWN", "unknown", "RECHECK_REQUIRED", "NONE", False)
    if source_ref == "AVAILABLE_EMPTY":
        return _result("HISTORICAL_ONLY", "historical-only", "ADMIT", "NONE", True)
    if not source_ref:
        return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)

    if rpk == "DURABLE_MACHINE_CLAIM":
        if ct == "MISSION_RESULT":
            if raw.get("terminal_state") is None:
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            return _result("HISTORICAL_ONLY", "historical-only", "ADMIT", "NONE", True)

        if ct == "PERSISTENT_GOAL_STATE":
            if not raw.get("status"):
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            return _result("SEMANTIC_DURABLE", "semantic-policy-nonphysical", "ADMIT", "NONE", True)

        if ct == "IDENTITY":
            if raw.get("attacker_supplied_live_entity_id") or raw.get("nearest_same_class_entity"):
                return _result("SEMANTIC_DURABLE", "semantic-policy-nonphysical", "REJECT", "NONE", False)
            if raw.get("originally_a_live_query_result_cached_by_caller"):
                return _result("HISTORICAL_ONLY", "historical-only", "RECHECK_REQUIRED", "NONE", False)
            # A durable record's own grounding_state (RESOLVED or otherwise)
            # is never trusted -- age/storage alone cannot confer authority.
            return _result("HISTORICAL_ONLY", "historical-only", "ADMIT", "NONE", True)

        if ct in ("ROBOT_OBSERVED", "WORLD_EVENT"):
            if not provenance_ref:
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            conf = raw.get("confidence")
            if conf is not None and (_is_bad_number(conf) or conf < 0 or conf > 1):
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            if observed_at is None or isinstance(observed_at, str):
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            if _is_bad_number(observed_at):
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            skew = observed_at - now
            if skew > 300:
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            if skew > 0:
                return _result("REQUIRES_CURRENT_RECHECK", "requires-current-worldstate-recheck",
                                "RECHECK_REQUIRED", "NONE", False)
            if ct == "ROBOT_OBSERVED" and not semantic_entity_id:
                return _result("HISTORICAL_ONLY", "historical-only", "RECHECK_REQUIRED", "NONE", False)
            if ct == "WORLD_EVENT" and raw.get("event_kind") is None:
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            # Age is irrelevant to physical authority for a durable record --
            # historical regardless of how recently it was ingested.
            return _result("HISTORICAL_ONLY", "historical-only", "ADMIT", "NONE", True)

        if ct == "CONFLICT":
            return _result("HISTORICAL_ONLY", "historical-only", "RECHECK_REQUIRED", "NONE", True)

        return _result("UNKNOWN", "unknown", "HUMAN_JUDGMENT_REQUIRED", "NONE", False)

    if rpk == "CURRENT_AUTHORITATIVE_QUERY_RESULT":
        if ct == "IDENTITY":
            if raw.get("candidates"):
                return _result("UNKNOWN", "unknown", "HUMAN_JUDGMENT_REQUIRED", "NONE", False)
            if not semantic_entity_id:
                return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)
            gs = raw.get("grounding_state")
            if gs == "UNRESOLVED":
                return _result("SEMANTIC_DURABLE", "semantic-policy-nonphysical", "ADMIT", "NONE", True)
            if gs == "RESOLVED":
                track_changed = raw.get("prior_live_entity_id") is not None
                has_reacq = any("reacquisition_evidence" in p for p in provenance_ref)
                if track_changed and not has_reacq:
                    return _result("UNKNOWN", "unknown", "RECHECK_REQUIRED", "NONE", False)
                return _result("CURRENT_AUTHORITATIVE", "current-authoritative-live-query",
                                "ADMIT", "CURRENT_AUTHORITATIVE_WHILE_VALID", True)
            return _result("UNKNOWN", "unknown", "REJECT", "NONE", False)

        if ct == "CONFLICT":
            return _result("CURRENT_AUTHORITATIVE", "current-authoritative-live-query",
                            "ADMIT", "CURRENT_AUTHORITATIVE_WHILE_VALID", True)

        return _result("UNKNOWN", "unknown", "HUMAN_JUDGMENT_REQUIRED", "NONE", False)

    return _result("UNKNOWN", "unknown", "HUMAN_JUDGMENT_REQUIRED", "NONE", False)
