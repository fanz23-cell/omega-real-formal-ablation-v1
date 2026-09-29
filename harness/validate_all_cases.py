"""$0 full mechanical validation of every calibration + confirmatory case: real ingestion,
real fairness check, real eligibility via the real gate, for every single case before any
paid call is made (directive sections 24, 26). No LLM calls in this file.
"""
import json
import world_case_generator
import contestants
import fairness_check
import real_metta_runner

CALIBRATION_SEED_LABEL = "CAL_v1"
CONFIRMATORY_SEED_LABEL = "CONFIRM_v1"

CALIBRATION_SCALES = [10]
CALIBRATION_REPS = 1  # 9 geometries x 1 scale x 1 rep = 9 cases (27 calls)

CONFIRMATORY_SCALES = [10, 100, 1000]
CONFIRMATORY_REPS = 7  # 9 geometries x 3 scales x 7 reps = 189 cases (567 calls)


def build_and_validate(seed_label, scales, reps):
    cases = world_case_generator.generate_cases(scales, world_case_generator.GEOMETRIES.keys(),
                                                 reps, seed_label)
    report = {"seed_label": seed_label, "n_cases": len(cases), "cases": []}
    for case in cases:
        events = world_case_generator.real_ingestion_events(case)
        seed_result = real_metta_runner.seed_claims(events)
        all_seeded = all(r["recorded"] for r in seed_result)

        prompt_b0 = contestants.render_B0(case)
        prompt_b1 = contestants.render_B1(case)
        c_result = contestants.render_C(case)
        prompt_c = c_result["prompt"]

        fairness = fairness_check.check_case_fairness(case, prompt_b0, prompt_b1, prompt_c)

        report["cases"].append({
            "case_id": case["case_id"], "geometry": case["geometry"], "scale_n": case["scale_n"],
            "rep_index": case["rep_index"], "all_events_seeded": all_seeded,
            "fairness_pass": fairness["pass"], "fairness_violations": fairness["violations"],
            "real_advisory": c_result["real_result"]["advisory"],
            "n_prompt_chars_b0": len(prompt_b0), "n_prompt_chars_b1": len(prompt_b1),
            "n_prompt_chars_c": len(prompt_c),
        })
    return report, cases


if __name__ == "__main__":
    cal_report, cal_cases = build_and_validate(CALIBRATION_SEED_LABEL, CALIBRATION_SCALES, CALIBRATION_REPS)
    print(f"=== CALIBRATION: {cal_report['n_cases']} cases ===")
    cal_all_pass = all(c["all_events_seeded"] and c["fairness_pass"] for c in cal_report["cases"])
    print("all_seeded_and_fair:", cal_all_pass)
    for c in cal_report["cases"]:
        print(f"  {c['geometry']:25s} n={c['scale_n']:5d} rep={c['rep_index']} "
              f"seeded={c['all_events_seeded']} fair={c['fairness_pass']} "
              f"advisory_freq={c['real_advisory']['frequency']:.4f} "
              f"advisory_conf={c['real_advisory']['confidence']:.4f}")

    with open("calibration_validation_report.json", "w") as f:
        json.dump(cal_report, f, indent=2)

    print(f"\n=== CONFIRMATORY: generating {9*len(CONFIRMATORY_SCALES)*CONFIRMATORY_REPS} cases (this will take a bit) ===")
    confirm_report, confirm_cases = build_and_validate(CONFIRMATORY_SEED_LABEL, CONFIRMATORY_SCALES, CONFIRMATORY_REPS)
    print(f"n_cases: {confirm_report['n_cases']}")
    confirm_all_pass = all(c["all_events_seeded"] and c["fairness_pass"] for c in confirm_report["cases"])
    print("all_seeded_and_fair:", confirm_all_pass)
    n_fail = sum(1 for c in confirm_report["cases"] if not (c["all_events_seeded"] and c["fairness_pass"]))
    print("n_failing_cases:", n_fail)
    if n_fail:
        for c in confirm_report["cases"]:
            if not (c["all_events_seeded"] and c["fairness_pass"]):
                print("  FAIL:", c["case_id"], c["fairness_violations"])

    with open("confirmatory_validation_report.json", "w") as f:
        json.dump(confirm_report, f, indent=2)

    print("\nCALIBRATION_MECHANICAL_VALIDATION:", "PASS" if cal_all_pass else "FAIL")
    print("CONFIRMATORY_MECHANICAL_VALIDATION:", "PASS" if confirm_all_pass else "FAIL")
