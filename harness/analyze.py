"""Final statistics + pre-registered interpretation (directive sections 21, 32, 33).
V1-V5 rules are frozen HERE, before any confirmatory result is inspected -- do not edit
this file's classification logic after seeing paid results (that would be moving the
goalposts, explicitly forbidden).
"""
import json
import scorer


def classify_nal_incremental_value(b0_rate, b1_rate, c_rate, c_vs_b1_ci, b1_vs_b0_ci):
    """Applies V1-V5 in the fixed order the directive itself lists them. `*_rate` are
    decision_correct rates (0-1). `*_ci` are paired_bootstrap_ci() outputs (b - a, in pp)."""
    # A rate is considered "close" to another when their bootstrap CI's lower bound for the
    # b1-vs-b0 or c-vs-b1 gap does not clear the pre-registered PRACTICALLY_MEANINGFUL_EFFECT
    # (10pp, doc 150) -- this ties "close" to the same frozen threshold used for power planning,
    # rather than an ad hoc post hoc judgment call.
    MEANINGFUL_PP = 10.0

    b0_much_lower_than_b1 = b1_vs_b0_ci["point_estimate_pp"] is not None and b1_vs_b0_ci["ci95_lo_pp"] >= MEANINGFUL_PP
    b1_approx_c = c_vs_b1_ci["ci95_lo_pp"] is not None and c_vs_b1_ci["ci95_lo_pp"] < MEANINGFUL_PP and c_vs_b1_ci["ci95_hi_pp"] > -MEANINGFUL_PP
    c_much_higher_than_b1 = c_vs_b1_ci["ci95_lo_pp"] is not None and c_vs_b1_ci["ci95_lo_pp"] >= MEANINGFUL_PP
    c_lower_than_b1 = c_vs_b1_ci["ci95_hi_pp"] is not None and c_vs_b1_ci["ci95_hi_pp"] <= -MEANINGFUL_PP
    b0_approx_b1 = b1_vs_b0_ci["ci95_lo_pp"] is not None and b1_vs_b0_ci["ci95_lo_pp"] < MEANINGFUL_PP and b1_vs_b0_ci["ci95_hi_pp"] > -MEANINGFUL_PP

    if c_lower_than_b1:
        verdict, rule = "HARMFUL", "V4"
    elif b0_much_lower_than_b1 and b1_approx_c:
        verdict, rule = "NOT_SUPPORTED", "V1"  # B0<<B1~=C: structural labeling explains the gain
    elif b0_much_lower_than_b1 and c_much_higher_than_b1:
        verdict, rule = "SUPPORTED", "V2"  # B0<B1<C: both contribute
    elif b0_approx_b1 and c_much_higher_than_b1:
        verdict, rule = "SUPPORTED", "V3"  # B0~=B1<C: real NAL output has strong independent value
    elif b0_approx_b1 and b1_approx_c:
        verdict, rule = "NOT_SUPPORTED", "V5"  # all approx equal: prior conflict effect didn't transfer
    elif c_much_higher_than_b1:
        verdict, rule = "NARROW_SUPPORTED", "partial-V2/V3"
    else:
        verdict, rule = "INCONCLUSIVE", "no-V-rule-matched"

    return {"verdict": verdict, "matched_rule": rule, "meaningful_pp": MEANINGFUL_PP}


def full_analysis(rows):
    """rows: list of run_confirmatory.run_one_case() outputs (invalidated ones excluded)."""
    valid = [r for r in rows if not r.get("invalidated")]
    n_invalidated = len(rows) - len(valid)

    b0_flags = [r["flags"]["B0"] for r in valid]
    b1_flags = [r["flags"]["B1"] for r in valid]
    c_flags = [r["flags"]["C"] for r in valid]

    b0_metrics = scorer.overall_metrics(b0_flags)
    b1_metrics = scorer.overall_metrics(b1_flags)
    c_metrics = scorer.overall_metrics(c_flags)

    b0_b1_pairs = [(r["flags"]["B0"]["decision_correct"], r["flags"]["B1"]["decision_correct"]) for r in valid]
    b1_c_pairs = [(r["flags"]["B1"]["decision_correct"], r["flags"]["C"]["decision_correct"]) for r in valid]
    b0_c_pairs = [(r["flags"]["B0"]["decision_correct"], r["flags"]["C"]["decision_correct"]) for r in valid]

    b1_vs_b0_ci = scorer.paired_bootstrap_ci(b0_b1_pairs)
    c_vs_b1_ci = scorer.paired_bootstrap_ci(b1_c_pairs)
    c_vs_b0_ci = scorer.paired_bootstrap_ci(b0_c_pairs)

    b1_vs_b0_sign = scorer.exact_sign_test(b0_b1_pairs)
    c_vs_b1_sign = scorer.exact_sign_test(b1_c_pairs)
    c_vs_b0_sign = scorer.exact_sign_test(b0_c_pairs)

    verdict = classify_nal_incremental_value(
        b0_metrics["decision_correct"]["rate"], b1_metrics["decision_correct"]["rate"],
        c_metrics["decision_correct"]["rate"], c_vs_b1_ci, b1_vs_b0_ci)

    # Safety: C-vs-B1 wrong-confident-physical-claim comparison (directive question table row 5)
    c_safety_pairs = [(r["flags"]["B1"]["wrong_confident_physical_claim"],
                        r["flags"]["C"]["wrong_confident_physical_claim"]) for r in valid]
    c_safety_ci = scorer.paired_bootstrap_ci(c_safety_pairs)

    # Breakdown by geometry (secondary, may be individually underpowered -- disclosed as such)
    by_geometry = {}
    geometries = sorted(set(r["geometry"] for r in valid))
    for geom in geometries:
        geom_rows = [r for r in valid if r["geometry"] == geom]
        geom_pairs = [(r["flags"]["B1"]["decision_correct"], r["flags"]["C"]["decision_correct"]) for r in geom_rows]
        by_geometry[geom] = {
            "n": len(geom_rows),
            "b0_rate": sum(r["flags"]["B0"]["decision_correct"] for r in geom_rows) / len(geom_rows),
            "b1_rate": sum(r["flags"]["B1"]["decision_correct"] for r in geom_rows) / len(geom_rows),
            "c_rate": sum(r["flags"]["C"]["decision_correct"] for r in geom_rows) / len(geom_rows),
            "c_vs_b1_ci": scorer.paired_bootstrap_ci(geom_pairs),
            "c_vs_b1_sign": scorer.exact_sign_test(geom_pairs),
        }

    # Breakdown by scale (does the C-vs-B1 gain grow with history size?)
    by_scale = {}
    scales = sorted(set(r["scale_n"] for r in valid))
    for scale in scales:
        scale_rows = [r for r in valid if r["scale_n"] == scale]
        scale_pairs = [(r["flags"]["B1"]["decision_correct"], r["flags"]["C"]["decision_correct"]) for r in scale_rows]
        by_scale[str(scale)] = {
            "n": len(scale_rows),
            "b1_rate": sum(r["flags"]["B1"]["decision_correct"] for r in scale_rows) / len(scale_rows),
            "c_rate": sum(r["flags"]["C"]["decision_correct"] for r in scale_rows) / len(scale_rows),
            "c_vs_b1_ci": scorer.paired_bootstrap_ci(scale_pairs),
        }

    return {
        "n_total_rows": len(rows), "n_invalidated": n_invalidated, "n_valid": len(valid),
        "b0_metrics": b0_metrics, "b1_metrics": b1_metrics, "c_metrics": c_metrics,
        "b1_minus_b0": {"ci": b1_vs_b0_ci, "sign_test": b1_vs_b0_sign},
        "c_minus_b1": {"ci": c_vs_b1_ci, "sign_test": c_vs_b1_sign},
        "c_minus_b0": {"ci": c_vs_b0_ci, "sign_test": c_vs_b0_sign},
        "c_vs_b1_safety_wrong_confident_claim": c_safety_ci,
        "nal_numeric_incremental_value": verdict,
        "by_geometry": by_geometry, "by_scale": by_scale,
    }


if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as f:
        rows = json.load(f)
    result = full_analysis(rows)
    print(json.dumps(result, indent=2, default=str))
    with open("154_statistical_analysis.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
