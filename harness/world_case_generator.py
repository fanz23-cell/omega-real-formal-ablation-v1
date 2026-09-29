"""Generates B0/B1/C confirmatory cases in the REAL record_world_event() schema (doc 146).
9 preregistered confidence geometries (directive section 13), at multiple history scales
(distractor event counts), with globally-unique event_ids so cross-world contamination is
structurally impossible (exact provenance_ref matching, not fuzzy search -- see doc 148).

Every case is a genuine WORLD_EVENT conflict pair (same subject/predicate/predicate_aspect,
opposing values) -- this generator does not itself decide "is this a conflict", it only
varies the confidence geometry and the surrounding distractor volume. Values are entirely
synthetic (permitted explicitly by the user's own requirement, doc 143 sec 3) but every
field is in the real, exact schema record_world_event() requires.
"""
import hashlib

GEOMETRIES = {
    "G1_SYMMETRIC_MEDIUM":  (0.80, 0.80),
    "G2_SYMMETRIC_HIGH":    (0.97, 0.97),
    "G3_SYMMETRIC_WEAK":    (0.35, 0.35),
    "G4_TRUE_STRONG":       (0.95, 0.55),
    "G5_FALSE_STRONG":      (0.55, 0.95),
    "G6_NEAR_TIE_HIGH":     (0.91, 0.89),
    "G7_NEAR_TIE_MEDIUM":   (0.71, 0.69),
    "G8_HIGH_VS_LOW":       (0.99, 0.25),
    "G9_REVERSE_HIGH_LOW":  (0.25, 0.99),
}

_PREDICATES = ["locked", "armed", "charged", "occupied", "connected", "powered", "sealed", "active"]
_SOURCE_TYPES = ["SENSOR_OBSERVATION", "THIRD_PARTY_REPORT", "USER_STATEMENT", "ROBOT_OBSERVED_DIRECT"]


def _stable_id(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def make_case(geometry_name: str, scale_n: int, rep_index: int, seed_label: str,
              source_diversity: bool = False):
    """Returns a dict: {case_id, geometry, scale_n, subject, predicate, predicate_aspect,
    target_claim_true (real-schema dict), target_claim_false (real-schema dict),
    distractors (list of real-schema dicts, unrelated predicates/subjects/entities)}."""
    freq_true_conf, freq_false_conf = GEOMETRIES[geometry_name]
    case_id = _stable_id(seed_label, geometry_name, scale_n, rep_index)
    subject = f"entity_{case_id[:8]}"
    predicate = _PREDICATES[rep_index % len(_PREDICATES)]
    aspect = "STATE"

    base_t = 100000.0 + rep_index * 500.0
    src_true = _SOURCE_TYPES[0] if not source_diversity else _SOURCE_TYPES[rep_index % 2]
    src_false = _SOURCE_TYPES[1] if not source_diversity else _SOURCE_TYPES[(rep_index + 1) % 2]

    target_true = {
        "event_id": f"{case_id}_true", "subject": subject, "predicate": predicate, "value": True,
        "source_type": src_true, "source_id": f"src_{case_id}_a", "observed_at": base_t,
        "confidence": freq_true_conf, "predicate_aspect": aspect, "semantic_entity_id": "",
    }
    target_false = {
        "event_id": f"{case_id}_false", "subject": subject, "predicate": predicate, "value": False,
        "source_type": src_false, "source_id": f"src_{case_id}_b", "observed_at": base_t + 1.0,
        "confidence": freq_false_conf, "predicate_aspect": aspect, "semantic_entity_id": "",
    }

    n_distractors = max(0, scale_n - 2)
    distractors = []
    for i in range(n_distractors):
        d_subject = f"distractor_{case_id[:8]}_{i}"
        d_predicate = _PREDICATES[(rep_index + i + 1) % len(_PREDICATES)]
        distractors.append({
            "event_id": f"{case_id}_distractor_{i}", "subject": d_subject, "predicate": d_predicate,
            "value": (i % 2 == 0), "source_type": _SOURCE_TYPES[i % len(_SOURCE_TYPES)],
            "source_id": f"src_distractor_{case_id}_{i}", "observed_at": base_t - 1000.0 - i,
            "confidence": 0.6 + (i % 4) * 0.1, "predicate_aspect": "STATE", "semantic_entity_id": "",
        })

    return {
        "case_id": case_id, "geometry": geometry_name, "scale_n": scale_n, "rep_index": rep_index,
        "subject": subject, "predicate": predicate, "predicate_aspect": aspect,
        "target_claim_true": target_true, "target_claim_false": target_false,
        "distractors": distractors,
        "premise_ref_true": f"obs:{target_true['event_id']}",
        "premise_ref_false": f"obs:{target_false['event_id']}",
    }


def generate_cases(scales, geometries, reps_per_cell, seed_label):
    """Deterministic generation (no randomness -- rep_index alone determines content,
    so the SAME (scales, geometries, reps_per_cell, seed_label) always yields identical
    cases, satisfying restart-determinism (section 24) without needing Math.random/Date)."""
    cases = []
    for geometry_name in geometries:
        for scale_n in scales:
            for rep in range(reps_per_cell):
                cases.append(make_case(geometry_name, scale_n, rep, seed_label))
    return cases


def all_events_for_case(case: dict) -> list:
    """Every real-schema event shown in the LLM-facing evidence block (target pair +
    distractors) -- for PROMPT RENDERING only, see contestants.py."""
    return [case["target_claim_true"], case["target_claim_false"]] + case["distractors"]


def real_ingestion_events(case: dict) -> list:
    """The events that actually need to go through record_world_event() into the real
    Omega/Chroma store. Deliberately EXCLUDES distractors: grounded_reason()'s real premise
    lookup is exact provenance_ref matching (never fuzzy/ranked retrieval), so a distractor
    event is never looked up by the real reasoning call regardless of how many exist --
    seeding them into the real store would only bloat _find_by_provenance_ref's full-
    collection scan for no product-relevant reason (confirmed empirically: this caused real
    slowdowns/timeouts at N=1000 scale before this fix). The "does more history change LLM
    behavior" question this benchmark's scale axis tests is about prompt context volume,
    not about Omega's own lookup mechanism, which is O(1)-semantic by construction here."""
    return [case["target_claim_true"], case["target_claim_false"]]
