"""Automated fairness/information-boundary checker (directive section 11 / doc 148).
Invalidates (does not score) any case that fails. Run BEFORE scoring, on every case.
"""
import re

_EVIDENCE_RE = re.compile(r"Recorded evidence.*?\n\n", re.DOTALL)


def _evidence_block(prompt: str) -> str:
    m = _EVIDENCE_RE.search(prompt)
    return m.group(0) if m else ""


def check_case_fairness(case: dict, prompt_B0: str, prompt_B1: str, prompt_C: str) -> dict:
    """Returns {"pass": bool, "violations": [str, ...]}."""
    violations = []

    ev_b0, ev_b1, ev_c = _evidence_block(prompt_B0), _evidence_block(prompt_B1), _evidence_block(prompt_C)
    if not (ev_b0 == ev_b1 == ev_c):
        violations.append("RAW_EVIDENCE_MISMATCH_ACROSS_ARMS")

    # B1 must have exactly one ADVISORY block with WITHHELD_CONTROL numerics
    if "ADVISORY A" not in prompt_B1:
        violations.append("B1_MISSING_ADVISORY_BLOCK")
    if "frequency=WITHHELD_CONTROL" not in prompt_B1 or "confidence=WITHHELD_CONTROL" not in prompt_B1:
        violations.append("B1_NUMERIC_FIELDS_NOT_WITHHELD")

    # C must have exactly one ADVISORY block, same shape, but real numerics (not WITHHELD)
    if "ADVISORY A" not in prompt_C:
        violations.append("C_MISSING_ADVISORY_BLOCK")
    if "frequency=WITHHELD_CONTROL" in prompt_C or "confidence=WITHHELD_CONTROL" in prompt_C:
        violations.append("C_NUMERIC_FIELDS_STILL_WITHHELD")

    # B1 vs C treatment block: byte-identical except the two numeric lines.
    def _block_lines(p):
        idx = p.find("ADVISORY A")
        end = p.find("\n\n", idx)
        return p[idx:end].splitlines()

    b1_lines, c_lines = _block_lines(prompt_B1), _block_lines(prompt_C)
    if len(b1_lines) != len(c_lines):
        violations.append("TREATMENT_BLOCK_LINE_COUNT_MISMATCH")
    else:
        for i, (l1, l2) in enumerate(zip(b1_lines, c_lines)):
            is_numeric_line = l1.startswith("frequency=") or l1.startswith("confidence=")
            if not is_numeric_line and l1 != l2:
                violations.append(f"TREATMENT_BLOCK_UNEXPECTED_DIFF_LINE_{i}")

    # No brand/placebo cues anywhere (section 12). WITHHELD_CONTROL is the directive's own
    # specified placeholder text (section 9's example) and is explicitly exempted before
    # scanning -- it is a data placeholder, not a brand/placebo cue leaking arm identity.
    forbidden = ["Omega", "NAL", "PLN", "MeTTa", "baseline", "control", "treatment",
                 "formal engine", "more trustworthy"]
    for p, name in ((prompt_B0, "B0"), (prompt_B1, "B1"), (prompt_C, "C")):
        scan_text = p.replace("WITHHELD_CONTROL", "")
        for term in forbidden:
            if term.lower() in scan_text.lower():
                violations.append(f"BRAND_CUE_LEAK_{name}_{term!r}")

    return {"pass": len(violations) == 0, "violations": violations}
