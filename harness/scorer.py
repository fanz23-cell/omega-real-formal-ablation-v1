"""Scoring + statistics (directive sections 19-21, 32). Paired bootstrap CI + exact sign
test, same methodology as the prior long-horizon benchmark (Koehn 2004 / Dror et al. 2018),
applied to the NEW primary contrast (C vs B1) and the two secondary contrasts (B1 vs B0,
C vs B0). No `Math.random`/`Date.now` dependency -- a fixed, disclosed seed via Python's
own `random.Random(12345)`, exactly reproducible.
"""
import random
import oracle


def score_answer(case: dict, answer: dict) -> dict:
    gold = oracle.gold_for_case(case)
    return {
        "decision_correct": oracle.decision_correct(gold, answer),
        "wrong_confident_physical_claim": oracle.wrong_confident_physical_claim(answer),
        "conflict_preserved": oracle.conflict_preserved(answer),
        "gold": gold,
    }


def _rate(flags, key):
    n = len(flags)
    if n == 0:
        return {"n": 0, "rate": None, "count_true": 0}
    count = sum(1 for f in flags if f[key])
    return {"n": n, "rate": count / n, "count_true": count}


def overall_metrics(rows_for_arm):
    """rows_for_arm: list of score dicts (score_answer's return value)."""
    return {
        "decision_correct": _rate(rows_for_arm, "decision_correct"),
        "wrong_confident_physical_claim": _rate(rows_for_arm, "wrong_confident_physical_claim"),
        "conflict_preserved": _rate(rows_for_arm, "conflict_preserved"),
    }


def paired_bootstrap_ci(pairs, seed=12345, n_resamples=5000):
    """pairs: list of (bool_a, bool_b) tuples, same case order. Returns delta (b-a) in
    percentage points with a 95% bootstrap CI."""
    n = len(pairs)
    if n == 0:
        return {"point_estimate_pp": None, "ci95_lo_pp": None, "ci95_hi_pp": None, "n_pairs": 0}
    rng = random.Random(seed)
    point = (sum(1 for _, b in pairs if b) - sum(1 for a, _ in pairs if a)) / n * 100
    deltas = []
    idxs = list(range(n))
    for _ in range(n_resamples):
        sample = [pairs[rng.choice(idxs)] for _ in range(n)]
        rate_a = sum(1 for a, _ in sample if a) / n
        rate_b = sum(1 for _, b in sample if b) / n
        deltas.append((rate_b - rate_a) * 100)
    deltas.sort()
    lo = deltas[int(0.025 * n_resamples)]
    hi = deltas[int(0.975 * n_resamples) - 1]
    return {"point_estimate_pp": round(point, 2), "ci95_lo_pp": round(lo, 2),
            "ci95_hi_pp": round(hi, 2), "n_pairs": n, "n_resamples": n_resamples, "seed": seed}


def exact_sign_test(pairs):
    """pairs: list of (bool_a, bool_b). Returns discordant counts + exact two-sided
    binomial sign-test p-value (no scipy dependency -- plain math.comb)."""
    import math
    a_wrong_b_right = sum(1 for a, b in pairs if (not a) and b)
    a_right_b_wrong = sum(1 for a, b in pairs if a and (not b))
    n_discordant = a_wrong_b_right + a_right_b_wrong
    if n_discordant == 0:
        return {"a_wrong_b_right": 0, "a_right_b_wrong": 0, "n_discordant": 0, "p_two_sided": 1.0}
    k = min(a_wrong_b_right, a_right_b_wrong)
    # two-sided exact binomial test, p=0.5
    total = sum(math.comb(n_discordant, i) for i in range(0, k + 1)) * 2
    p = min(1.0, total / (2 ** n_discordant))
    return {"a_wrong_b_right": a_wrong_b_right, "a_right_b_wrong": a_right_b_wrong,
            "n_discordant": n_discordant, "p_two_sided": p}


def nal_numeric_incremental_value(b1_correct, c_correct, threshold_pp=5.0):
    """The directive's most important metric (section 20). Defined ONLY from C vs B1.
    Returns one of SUPPORTED / NARROW_SUPPORTED / NOT_SUPPORTED / HARMFUL, based on the
    paired bootstrap CI computed by the caller (passed in as `ci`), never re-derived here
    from raw rates alone -- see analyze.py for how this label is actually assigned using
    the CI's lower bound, per the pre-registered interpretation rules (section 21)."""
    raise NotImplementedError("call classify_nal_incremental_value(ci) instead, in analyze.py")
