"""$0 paired-power analysis (directive section 25). Monte Carlo simulation of the exact
sign test's power to detect a C-vs-B1 paired accuracy delta, under a range of plausible
discordant-pair rates (unknown until calibration, so swept rather than assumed). Chooses
the smallest N (per geometry-cell replicate count) with reasonable power (>=0.80) for a
PRACTICALLY_MEANINGFUL_EFFECT, defined here BEFORE any paid call:

PRACTICALLY_MEANINGFUL_EFFECT := a >=10 percentage point paired C-vs-B1 accuracy delta.
(5pp is checked too, for context, but 10pp is the pre-registered target this plan optimizes
for -- smaller effects are real but this benchmark is not resourced to chase them, matching
the directive's own "use the smallest scientifically defensible sample" instruction.)
"""
import random
import math


def simulate_power(n_pairs, discordant_rate, favor_rate, alpha=0.05, n_sims=3000, seed=777):
    """discordant_rate: fraction of pairs where B1 and C differ.
    favor_rate: among discordant pairs, fraction favoring C (0.5 = no true effect)."""
    rng = random.Random(seed)
    rejections = 0
    for _ in range(n_sims):
        n_discordant = sum(1 for _ in range(n_pairs) if rng.random() < discordant_rate)
        if n_discordant == 0:
            continue
        favor_c = sum(1 for _ in range(n_discordant) if rng.random() < favor_rate)
        favor_b1 = n_discordant - favor_c
        k = min(favor_c, favor_b1)
        p = min(1.0, sum(math.comb(n_discordant, i) for i in range(0, k + 1)) * 2 / (2 ** n_discordant))
        if p < alpha:
            rejections += 1
    return rejections / n_sims


def favor_rate_for_effect(effect_pp, discordant_rate):
    """A paired accuracy delta of effect_pp translates to a favor_rate among discordant
    pairs: delta = discordant_rate * (2*favor_rate - 1) * 100 => solve for favor_rate."""
    if discordant_rate == 0:
        return 0.5
    return 0.5 + (effect_pp / 100.0) / (2 * discordant_rate)


def plan(target_effects_pp=(5, 10, 20), discordant_rates=(0.15, 0.25, 0.35),
         candidate_n=(10, 15, 20, 25, 30, 40, 50)):
    results = {}
    for effect in target_effects_pp:
        for d_rate in discordant_rates:
            favor = favor_rate_for_effect(effect, d_rate)
            if favor > 1.0:
                continue  # this (effect, discordant_rate) combination is not achievable
            for n in candidate_n:
                power = simulate_power(n, d_rate, favor)
                key = (effect, d_rate, n)
                results[key] = power
    return results


if __name__ == "__main__":
    results = plan()
    print(f"{'effect_pp':>10} {'discordant_rate':>16} {'n_per_cell':>11} {'power':>7}")
    for (effect, d_rate, n), power in sorted(results.items()):
        marker = " <-- >=0.80" if power >= 0.80 else ""
        print(f"{effect:>10} {d_rate:>16} {n:>11} {power:>7.2f}{marker}")

    # Recommendation for the pre-registered target (10pp effect)
    print("\n=== Recommendation for PRACTICALLY_MEANINGFUL_EFFECT = 10pp ===")
    for d_rate in (0.15, 0.25, 0.35):
        for n in (10, 15, 20, 25, 30, 40, 50):
            key = (10, d_rate, n)
            if key in results and results[key] >= 0.80:
                print(f"discordant_rate={d_rate}: n_per_cell={n} reaches power={results[key]:.2f}")
                break
