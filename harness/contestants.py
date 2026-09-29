"""B0/B1/C prompt construction (directive sections 7-9, 12, 17). No branding/placebo cues
anywhere in the rendered text (section 12) -- labels are neutral ("ADVISORY"), never "Omega",
"NAL", "baseline", "control", "treatment". B1 and C's treatment blocks are byte-identical
except the two numeric fields (frequency/confidence) -- see fairness_check.py for the
automated proof.
"""
import json
import real_metta_runner

SYSTEM_PROMPT = (
    "You are a robot's cognition module answering questions about its own recorded evidence. "
    "Read the evidence below and answer with a single JSON object using EXACTLY these keys: "
    "epistemic_status (one of SUPPORTED_CURRENT, HISTORICAL_SUPPORT_ONLY, UNRESOLVED_CONFLICT, "
    "STALE_ONLY, UNKNOWN), current_physical_claim (one of TRUE, FALSE, UNKNOWN), "
    "relative_historical_support (one of TRUE_STRONGER, FALSE_STRONGER, APPROX_BALANCED, "
    "INSUFFICIENT), recommended_action (one of ACT, RECHECK, ASK, ESCALATE, WAIT, IGNORE), "
    "may_treat_as_current_authoritative (true or false), reason_class (one of "
    "FOLLOWED_ADVISORY, FOLLOWED_STRUCTURAL_LABEL, OWN_JUDGMENT_RECENCY, "
    "OWN_JUDGMENT_SOURCE_TRUST, OWN_JUDGMENT_OTHER). "
    "Output ONLY the JSON object and nothing else -- no markdown fences, no commentary, "
    "no hidden reasoning."
)


def _render_event(e):
    return (f"- subject={e['subject']} predicate={e['predicate']} value={e['value']} "
            f"source_type={e['source_type']} source_id={e['source_id']} "
            f"observed_at={e['observed_at']:.1f} confidence={e['confidence']} "
            f"predicate_aspect={e['predicate_aspect']}")


def _render_evidence_block(case):
    # B0/B1/C all see the SAME two target claims + the SAME distractor volume, in the SAME
    # order -- information parity (section 11) at the raw-evidence layer.
    lines = [_render_event(case["target_claim_true"]), _render_event(case["target_claim_false"])]
    for d in case["distractors"]:
        lines.append(_render_event(d))
    return "\n".join(lines)


def _question(case):
    return f"Question: Is {case['subject']}'s {case['predicate']} currently true?"


def render_B0(case: dict) -> str:
    """Strong structured non-formal baseline, NO advisory block at all."""
    return (f"Recorded evidence (real event records, most relevant two listed first):\n"
            f"{_render_evidence_block(case)}\n\n{_question(case)}")


def _structural_label_block(case, withheld: bool, real_advisory: dict = None):
    """Byte-identical for B1/C except the two numeric lines -- verified by fairness_check.py."""
    if withheld:
        freq_line = "frequency=WITHHELD_CONTROL"
        conf_line = "confidence=WITHHELD_CONTROL"
    else:
        freq_line = f"frequency={real_advisory['frequency']}"
        conf_line = f"confidence={real_advisory['confidence']}"
    return (
        "ADVISORY A\n"
        "status=UNRESOLVED_CONFLICT_BETWEEN_OPPOSING_GROUNDED_CLAIMS\n"
        "recommended_action=ESCALATE_OR_RECHECK\n"
        "authority=NONE\n"
        f"{freq_line}\n"
        f"{conf_line}"
    )


def render_B1(case: dict) -> str:
    """B0 + a benchmark-only, deterministic structural-conflict placebo advisory (real
    eligibility gate reused -- see fairness_check.py's own verification that every case
    here is confirmed eligible via the REAL grounded_reason._revision_eligible() gate, not
    a second handwritten reimplementation of that check)."""
    block = _structural_label_block(case, withheld=True)
    return (f"Recorded evidence (real event records, most relevant two listed first):\n"
            f"{_render_evidence_block(case)}\n\n{block}\n\n{_question(case)}")


def render_C(case: dict) -> dict:
    """B1 + the REAL Omega/MeTTa Truth_Revision numeric result (real_metta_runner.py --
    real ingestion already performed by the harness driver before this is called; this
    function only invokes the real reasoning call and renders its real output).
    Returns {"prompt": str, "real_result": dict} -- real_result is logged for the trace
    audit (section 34), never itself exposed as hidden chain-of-thought."""
    result = real_metta_runner.real_grounded_reason(
        case["premise_ref_true"], case["premise_ref_false"], "revision")
    if not result["ok"]:
        raise RuntimeError(f"real_grounded_reason failed for case {case['case_id']}: {result}")
    block = _structural_label_block(case, withheld=False, real_advisory=result["advisory"])
    prompt = (f"Recorded evidence (real event records, most relevant two listed first):\n"
              f"{_render_evidence_block(case)}\n\n{block}\n\n{_question(case)}")
    return {"prompt": prompt, "real_result": result}
