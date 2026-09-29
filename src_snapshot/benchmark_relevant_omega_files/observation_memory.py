"""observation_memory: deterministic, LLM-independent durable recording of
mc_multimodal's own already-structured visual observations into a
dedicated ChromaDB collection, `observation_claims_v1`.

Producer classification (P0.4 audit, confirmed by direct source read of
mc_multimodal/parser.py + node.py + mc_one/msg/VisualCheckResult.msg):
**Design B / semi-structured machine observation.** mc_multimodal's visual
provider is REQUIRED to answer in strict JSON
(state/reason/confidence/evidence -- `parser.py`'s
`parse_visual_check_response` raises ValueError on anything else, never a
free-text regex parse), and the resulting `VisualCheckResult` ROS message
already carries full provenance: a stable per-call `debug_id` (used here
as `observation_id`), the REAL sensor capture identity/timestamp
(`image_frame_id`/`image_stamp` -- not Bridge/Omega receipt time),
freshness (`image_age_sec`), and source attribution
(`provider_name`/`model_name`). None of this reached Omega before P0.4:
Bridge's own `visual_check()` HTTP handler discarded it, and nothing
durably stored it. P0.4 (this round) fixed the mechanical Bridge
passthrough (`mc_voice_pipeline_legacy` commit `f5c1dcd`) and adds this
module as the durable Omega-side intake -- Design A ("producer emits
structured observation -> Bridge mechanically carries it -> Omega durable
intake"), NOT free-text parsing (Design E, rejected) and NOT a new
Bridge-owned durable store (Design D, rejected -- Bridge stays
transport-only).

Unlike mission_memory's MISSION_RESULT intake (async: a mission is
submitted, its terminal outcome arrives much later via a separate
journal+heartbeat path), a `robot_observe` call is SYNCHRONOUS -- request
and structured response happen in one round trip, already inside
`codey_robot.py`'s own Python code. No heartbeat/journal-tailing is
needed here: `record_observation()` is called directly, once, by
`codey_robot.robot_observe()` immediately after it receives Bridge's
(now-complete) JSON response, before rendering the unchanged
LLM-facing reply text. See codey_robot.py's own call site for the
defensive try/except wrapping (a recording failure must never break the
existing conversational behavior).

Ownership / trust: the LLM controls only the QUESTION text passed into
`robot_observe(question)` -- it has no path to author or influence
`state`/`confidence`/`evidence`/`observation_id`/`image_frame_id`/
`image_stamp`/`provider_name`/`model_name`, all of which are 100%
computed by the real camera + real vision-model + real Bridge round trip
before `record_observation()` ever runs. This module exposes NO add-skill
of its own -- there is no LLM-callable write path to
`observation_claims_v1` at all, mirroring `mission_memory`'s own
MISSION_RESULT trust boundary exactly.

Historical vs. current truth: a stored ROBOT_OBSERVED claim means "the
robot observed X at time T" -- never "X is true now". No renderer is
built in this module (P0.4 does not require a general LLM-facing
observation-history skill); the only consumers of this collection so far
are the internal query helpers below, used for live-acceptance/testing
verification, not exposed to the LLM.
"""
import datetime
import fcntl
import json
import os
import threading
import traceback
import uuid

JOURNAL_SCHEMA = "mc.robot_observation.v1"

CHROMA_PATH = os.environ.get(
    "OBSERVATION_MEMORY_CHROMA_PATH", "/PeTTa/repos/OmegaClaw-Core/memory/chroma_db")
COLLECTION_NAME = os.environ.get("OBSERVATION_MEMORY_COLLECTION", "observation_claims_v1")
LOG_PATH = os.environ.get(
    "OBSERVATION_MEMORY_LOG", "/PeTTa/repos/OmegaClaw-Core/memory/observation_memory.log")

DUMMY_EMBEDDING = [0.0]

_stats = {"recorded": 0, "rejected": 0}
_collection_cache = {"col": None}
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
    import chromadb
    lock_path = CHROMA_PATH.rstrip("/") + ".init.lock"
    lock_dir = os.path.dirname(lock_path) or "."
    os.makedirs(lock_dir, exist_ok=True)
    with open(lock_path, "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            return chromadb.PersistentClient(path=CHROMA_PATH)
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _log(msg):
    line = f"{datetime.datetime.utcnow().isoformat()}Z {msg}"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _get_collection():
    with _chroma_lock:
        if _collection_cache["col"] is None:
            client = _new_chroma_client()
            _collection_cache["col"] = client.get_or_create_collection(COLLECTION_NAME)
        return _collection_cache["col"]


def _deterministic_id(observation_id):
    # observation_id is already a fresh uuid4 minted by mc_multimodal per
    # call (msg.debug_id) -- reused directly as the Chroma record id
    # (still namespaced/hashed so a malformed/empty value can never collide
    # with an unrelated record).
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"observation:{observation_id}"))


def record_observation(observed):
    """Called directly by codey_robot.robot_observe() -- NOT an add-skill,
    NOT LLM-callable. `observed` is a dict built entirely from Bridge's
    already-fixed, already-structured /visual_check response (see
    codey_robot.py's call site) -- every field here is machine-computed,
    never LLM-authored. Never raises (matches mission_memory.tick()'s own
    contract): a recording failure must degrade to "this observation
    wasn't durably recorded", never break robot_observe's existing
    conversational behavior.

    Required keys in `observed`: state, reason, confidence, evidence
    (json string), observation_id, image_source, image_frame_id,
    image_stamp_sec, image_age_sec, provider_name, model_name, query.
    Skipped (not recorded, not an error) when state == "UNKNOWN" AND
    observation_id is empty (the "no fresh frame"/"server not ready"
    failure shape Bridge already uses -- nothing was actually observed).
    """
    try:
        return _record_observation(observed)
    except Exception:
        _log("FATAL(caught) unexpected exception in record_observation, "
             "continuing:\n" + traceback.format_exc())
        _stats["rejected"] += 1
        return False


def _record_observation(observed):
    observation_id = str(observed.get("observation_id") or "")
    state = str(observed.get("state") or "UNKNOWN")
    if not observation_id:
        # No real mc_multimodal call actually completed (e.g. "server not
        # ready", "no fresh camera frame") -- nothing was observed, so
        # nothing is recorded. Not an error; distinct from a real
        # completed call that happened to answer UNKNOWN.
        _log("INFO no observation_id present, skipping (no real observation occurred)")
        return False

    try:
        evidence = json.loads(observed.get("evidence") or "{}")
        if not isinstance(evidence, dict):
            evidence = {}
    except (TypeError, ValueError, json.JSONDecodeError):
        evidence = {}

    envelope = {
        "schema": JOURNAL_SCHEMA,
        "claim_kind": "ROBOT_OBSERVED",
        "observation_id": observation_id,
        "query": str(observed.get("query") or ""),
        "state": state,
        "reason": str(observed.get("reason") or ""),
        "confidence": float(observed.get("confidence") or 0.0),
        "evidence": evidence,
        "source_kind": "mc_multimodal.visual_check",
        "image_source": str(observed.get("image_source") or ""),
        "image_frame_id": str(observed.get("image_frame_id") or ""),
        "observed_at": float(observed.get("image_stamp_sec") or 0.0),
        "image_age_sec": float(observed.get("image_age_sec") or 0.0),
        "provider_name": str(observed.get("provider_name") or ""),
        "model_name": str(observed.get("model_name") or ""),
        # V1: no reliable subject/semantic_entity_id linkage exists on any
        # current robot_observe call path (confirmed: codey_robot.py never
        # sends context_json/grounded_entities to /visual_check) -- honest
        # empty list, not fabricated. See P0_4 schema-debt disposition.
        "subject_refs": [],
    }
    metadata = {
        "claim_kind": "ROBOT_OBSERVED",
        "observation_id": observation_id,
        "state": state,
        "confidence": float(observed.get("confidence") or 0.0),
        "source_kind": "mc_multimodal.visual_check",
        "image_frame_id": str(observed.get("image_frame_id") or ""),
        "observed_at": float(observed.get("image_stamp_sec") or 0.0),
        "provider_name": str(observed.get("provider_name") or ""),
        "model_name": str(observed.get("model_name") or ""),
        "semantic_entity_id": "",  # honest -- no linkage exists yet, see above
        "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    document = json.dumps(envelope, sort_keys=True)

    col = _get_collection()
    with _chroma_lock:
        col.upsert(ids=[_deterministic_id(observation_id)], documents=[document],
                   metadatas=[metadata], embeddings=[DUMMY_EMBEDDING])
    _stats["recorded"] += 1
    return True


def record_world_event(event):
    """Grounded Proposition contract completion (Change Approval, this round):
    durable, LLM-independent recording of a GENERIC world-state/event claim --
    the WORLD_EVENT counterpart to record_observation()'s own camera-only
    ROBOT_OBSERVED intake. Reuses the SAME collection (observation_claims_v1)
    and the SAME provenance-ref scheme (`obs:<observation_id>`, matched by
    grounded_reason._find_by_provenance_ref()'s own existing, UNCHANGED
    observation_claims_v1 lookup) -- not a new collection, not a new truth
    store, not a new EvidenceHub.

    Ownership / trust: identical discipline to record_observation() -- the
    caller must supply already-computed, non-LLM-authored fields; this
    function does not accept free text and does not infer any field it is
    not given. Never raises -- a recording failure degrades to "this event
    wasn't durably recorded", never breaks the caller's own behavior.

    Required keys in `event`: event_id (a fresh, caller-minted stable id --
    e.g. a UUID or a deterministic per-fact id), subject, predicate, value
    (the actual observed value -- used to derive polarity: None -> UNKNOWN
    (nothing was actually resolved -- fails closed downstream, never becomes
    a claim), False/""/"False" -> a NEGATIVE claim, anything else truthy ->
    a POSITIVE claim; polarity is preserved end-to-end, never collapsed to a
    hardcoded positive OR negative the way the pre-repair ROBOT_OBSERVED path
    hardcoded positive), source_type, source_id,
    observed_at (a real, comparable timestamp -- REQUIRED, never a raw
    simulation-relative value; grounded_proposition.classify_claim() compares
    it to wall-clock time), confidence (0.0-1.0), predicate_aspect (one of
    the existing typed values, e.g. "EVENT" or "STATE" -- preserved through
    to the formal statement, never defaulted or dropped).
    Optional: semantic_entity_id (empty string when no linkage exists, same
    honest-empty discipline as record_observation()).
    """
    try:
        return _record_world_event(event)
    except Exception:
        _log("FATAL(caught) unexpected exception in record_world_event, "
             "continuing:\n" + traceback.format_exc())
        _stats["rejected"] += 1
        return False


def _record_world_event(event):
    event_id = str(event.get("event_id") or "")
    if not event_id:
        _log("INFO no event_id present, skipping (no real event to record)")
        return False

    value = event.get("value")
    # A genuinely unresolved value (None -- "nothing observed/no answer") must NOT
    # collapse into polarity="false" -- that would be the exact same truth-safety
    # defect this whole repair exists to close, just reintroduced for WORLD_EVENT.
    # Only an explicit falsy VALUE (False/""/"False") is a real negative claim.
    if value is None:
        polarity = "unknown"
    elif value is False or value == "" or value == "False":
        polarity = "false"
    else:
        polarity = "true"

    envelope = {
        "schema": JOURNAL_SCHEMA,
        "claim_kind": "WORLD_EVENT",
        "observation_id": event_id,
        "subject": str(event.get("subject") or ""),
        "predicate": str(event.get("predicate") or ""),
        "value": value,
        "polarity": polarity,
        # TRUTH-SAFETY FIX (WORLD_EVENT_UNKNOWN_PREDICATE_ASPECT_COLLAPSED_TO_STATE, doc 119,
        # autonomous finalization, 2026-09-26): an omitted/falsy predicate_aspect must NOT be
        # silently fabricated as "STATE" -- same principle as value=None -> polarity="unknown"
        # above, never collapsed to a guessed specific value. Preserved honestly as "UNKNOWN";
        # grounded_reason.py's own _resolve_premise_claim() now fails closed on this value.
        "predicate_aspect": str(event.get("predicate_aspect") or "UNKNOWN"),
        "confidence": float(event.get("confidence") or 0.0),
        "source_type": str(event.get("source_type") or ""),
        "source_id": str(event.get("source_id") or ""),
        "observed_at": float(event.get("observed_at")) if event.get("observed_at") is not None else None,
        "semantic_entity_id": str(event.get("semantic_entity_id") or ""),
    }
    metadata = {
        "claim_kind": "WORLD_EVENT",
        "observation_id": event_id,
        "subject": envelope["subject"],
        "predicate": envelope["predicate"],
        "polarity": polarity,
        "predicate_aspect": envelope["predicate_aspect"],
        "confidence": envelope["confidence"],
        "observed_at": envelope["observed_at"],
        "semantic_entity_id": envelope["semantic_entity_id"],
        "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    document = json.dumps(envelope, sort_keys=True)

    col = _get_collection()
    with _chroma_lock:
        col.upsert(ids=[_deterministic_id(event_id)], documents=[document],
                   metadatas=[metadata], embeddings=[DUMMY_EMBEDDING])
    _stats["recorded"] += 1
    return True


# --- LLM-facing read-only retrieval skill (Change Approval, this round) -----

_ALLOWED_QUERY_KEYS = {"subject", "predicate", "claim_kind", "predicate_aspect",
                       "semantic_entity_id", "limit"}
_ALLOWED_QUERY_CLAIM_KINDS = {"ROBOT_OBSERVED", "WORLD_EVENT"}
_ALLOWED_QUERY_PREDICATE_ASPECTS = {"EVENT", "STATE"}


def query_observation_claims(json_str):
    """OBSERVATION CLAIM DISCOVERABILITY GAP fix: the missing discovery surface for
    observation_claims_v1 -- mirrors mission_memory's own retrieval skill (generic,
    read-only, no write path) rather than inventing a new pattern. Returns a plain,
    human-readable summary of already-admitted machine claims matching the given
    filters, each carrying its own premise_ref -- the SAME provenance-ref string
    grounded_reason._find_by_provenance_ref() already resolves, completely unchanged.

    ABI (QUERY_OBSERVATION_CLAIMS_ARGUMENT_MARSHALLING_INTERFACE_BUG repair, round 4):
    ONE argument, a single-line JSON object string -- e.g.
    {"subject":"delivery_1","predicate":"delivered_flag_1","claim_kind":"WORLD_EVENT",
    "predicate_aspect":"STATE","semantic_entity_id":"","limit":10}. This REPLACES the
    original six-bare-positional-argument form (never reachable by a real LLM call:
    the core prompt's own generic single-argument-per-tool-call convention always
    collapsed all six values into one string, causing a deterministic
    `domain_error py_term` arity mismatch -- confirmed 3/3 times in real traces, see
    81_QUERY_OBSERVATION_CLAIMS_ARGUMENT_MARSHALLING_BUG.md). Matches
    query_mission_history's own already-proven single-JSON-argument convention
    exactly, including its deterministic-parsing discipline: unknown keys, wrong
    types, and malformed/non-object JSON are REJECTED with a typed INVALID_ARGUMENT
    string, never guessed at or silently reinterpreted as free text.

    Every key is OPTIONAL (unlike query_mission_history's own required subject_ref)
    -- omitted means "no filter on this field", identical to the prior interface's
    own ""-means-wildcard convention. subject/predicate/semantic_entity_id/limit
    keep their exact prior semantics and are handed straight to the existing,
    UNCHANGED _query_observation_claims() -- this is an ABI-only repair, the actual
    query/filter/rendering behavior is not touched. A subject/predicate filter still
    only ever matches WORLD_EVENT records (ROBOT_OBSERVED carries no structured
    subject/predicate of its own -- unchanged, honest reflection of the existing
    schema). Never raises: any failure returns a typed string, never an exception
    surfaced to the LLM loop.

    This is a discovery tool only -- it does not itself call grounded_reason and
    does not suggest any specific next action; the caller decides what, if anything,
    to reason over."""
    try:
        return _query_observation_claims_json(json_str)
    except Exception:
        _log("FATAL(caught) unexpected exception in query_observation_claims, "
             "continuing:\n" + traceback.format_exc())
        return "QUERY_ERROR: internal failure, no claims returned"


def _query_observation_claims_json(json_str):
    """JSON-argument parsing layer -- same deterministic-parsing discipline as
    mission_memory._query_mission_history() (reused, not reinvented): reject
    unknown keys, wrong types, and malformed/non-object JSON with a typed
    INVALID_ARGUMENT string. Delegates the actual query to the existing, unchanged
    _query_observation_claims()."""
    try:
        spec = json.loads(json_str)
    except (TypeError, ValueError, json.JSONDecodeError):
        return "INVALID_ARGUMENT: argument must be a single valid JSON object string"
    if not isinstance(spec, dict):
        return "INVALID_ARGUMENT: argument must be a JSON object, not a list/scalar"

    unknown_keys = set(spec.keys()) - _ALLOWED_QUERY_KEYS
    if unknown_keys:
        return (f"INVALID_ARGUMENT: unknown key(s) {sorted(unknown_keys)}, "
                f"allowed: {sorted(_ALLOWED_QUERY_KEYS)}")

    subject = spec.get("subject", "")
    if not isinstance(subject, str):
        return "INVALID_ARGUMENT: subject must be a string"
    predicate = spec.get("predicate", "")
    if not isinstance(predicate, str):
        return "INVALID_ARGUMENT: predicate must be a string"
    claim_kind = spec.get("claim_kind", "")
    if not isinstance(claim_kind, str) or (claim_kind and claim_kind not in _ALLOWED_QUERY_CLAIM_KINDS):
        return (f"INVALID_ARGUMENT: claim_kind must be one of "
                f"{sorted(_ALLOWED_QUERY_CLAIM_KINDS)}, or omitted")
    predicate_aspect = spec.get("predicate_aspect", "")
    if not isinstance(predicate_aspect, str) or (
            predicate_aspect and predicate_aspect not in _ALLOWED_QUERY_PREDICATE_ASPECTS):
        return (f"INVALID_ARGUMENT: predicate_aspect must be one of "
                f"{sorted(_ALLOWED_QUERY_PREDICATE_ASPECTS)}, or omitted")
    semantic_entity_id = spec.get("semantic_entity_id", "")
    if not isinstance(semantic_entity_id, str):
        return "INVALID_ARGUMENT: semantic_entity_id must be a string"
    # limit: intentionally NOT strictly validated here -- _query_observation_claims()
    # already has its own established, tested fail-closed-to-10/cap-50 behavior for
    # any malformed value (preserving the prior interface's own "invalid limit safe"
    # contract exactly, per this round's own "preserve current query semantics").
    limit = spec.get("limit", 10)

    results = _query_observation_claims(subject, predicate, claim_kind, predicate_aspect,
                                         semantic_entity_id, limit)
    if not results:
        return "No matching observation/world-event claims found."

    lines = [f"Found {len(results)} matching claim(s):"]
    for r in results:
        lines.append(
            f"- premise_ref={r['premise_ref']} subject={r['subject']} predicate={r['predicate']} "
            f"value={r['value']} claim_kind={r['claim_kind']} predicate_aspect={r['predicate_aspect']} "
            f"observed_at={r['observed_at']} confidence={r['confidence']} "
            f"semantic_entity_id={r['semantic_entity_id'] or 'none'}")
    return "\n".join(lines)


def _query_observation_claims(subject="", predicate="", claim_kind="", predicate_aspect="",
                               semantic_entity_id="", limit="10"):
    """Internal, directly-testable form -- returns a list of dicts, one per matching
    claim, most-recent-first. Fetches the full collection and filters in plain Python
    (matching grounded_reason._find_by_provenance_ref()'s own existing, already-proven
    convention -- no reliance on chromadb `where`-operator syntax at all) rather than
    inventing a second query mechanism. Never raises on a malformed filter (an empty
    string is a wildcard); a genuinely invalid limit fails closed to the default of 10
    rather than guessing."""
    try:
        limit_n = int(limit)
        if limit_n <= 0:
            limit_n = 10
    except (TypeError, ValueError):
        limit_n = 10
    limit_n = min(limit_n, 50)

    col = _get_collection()
    with _chroma_lock:
        r = col.get(include=["metadatas"])

    out = []
    for meta in (r.get("metadatas") or []):
        if not meta:
            continue
        ck = meta.get("claim_kind")
        if ck not in ("ROBOT_OBSERVED", "WORLD_EVENT"):
            continue  # predates this skill's claim_kind convention -- skip, never guess
        observation_id = meta.get("observation_id")
        if not observation_id:
            continue

        row_subject = meta.get("subject") if ck == "WORLD_EVENT" else observation_id
        row_predicate = meta.get("predicate") if ck == "WORLD_EVENT" else None
        row_value = meta.get("polarity") if ck == "WORLD_EVENT" else meta.get("state")
        row_aspect = meta.get("predicate_aspect") if ck == "WORLD_EVENT" else None
        row_semid = meta.get("semantic_entity_id") or ""

        if subject and row_subject != subject:
            continue
        if predicate and row_predicate != predicate:
            continue
        if claim_kind and ck != claim_kind:
            continue
        if predicate_aspect and row_aspect != predicate_aspect:
            continue
        if semantic_entity_id and row_semid != semantic_entity_id:
            continue

        out.append({
            "premise_ref": f"obs:{observation_id}", "subject": row_subject,
            "predicate": row_predicate, "value": row_value, "claim_kind": ck,
            "predicate_aspect": row_aspect, "observed_at": meta.get("observed_at"),
            "confidence": meta.get("confidence"), "semantic_entity_id": row_semid,
        })

    out.sort(key=lambda x: x["observed_at"] if isinstance(x["observed_at"], (int, float)) else 0.0,
             reverse=True)
    return out[:limit_n]


# --- internal query helpers (testing/verification only -- NOT an add-skill) -

def by_observation_id(observation_id):
    col = _get_collection()
    with _chroma_lock:
        r = col.get(where={"observation_id": observation_id}, include=["metadatas", "documents"])
    return r


def recent(limit=10):
    col = _get_collection()
    with _chroma_lock:
        r = col.get(where={"claim_kind": "ROBOT_OBSERVED"}, include=["metadatas"])
    return sorted(r["metadatas"], key=lambda m: m.get("observed_at", 0.0), reverse=True)[:limit]
