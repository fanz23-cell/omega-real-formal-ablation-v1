"""Confirmatory (and calibration) run driver. Requires a real Anthropic API key path as
argv[1] -- never searched for, always supplied explicitly by the operator. Randomizes
per-case B0/B1/C execution order with a fixed, disclosed seed (directive section 29).
"""
import json
import random
import sys
import time

import contestants
import fairness_check
import llm_client
import oracle
import real_metta_runner
import scorer
import world_case_generator

MODEL = "claude-sonnet-4-5-20250929"
EXECUTION_ORDER_SEED = 20260928


def run_one_case(api_key, model, case):
    events = world_case_generator.real_ingestion_events(case)
    real_metta_runner.seed_claims(events)

    prompt_b0 = contestants.render_B0(case)
    prompt_b1 = contestants.render_B1(case)
    c_result = contestants.render_C(case)
    prompt_c = c_result["prompt"]

    fairness = fairness_check.check_case_fairness(case, prompt_b0, prompt_b1, prompt_c)
    if not fairness["pass"]:
        return {"case_id": case["case_id"], "invalidated": True,
                "fairness_violations": fairness["violations"]}

    arms = [("B0", prompt_b0), ("B1", prompt_b1), ("C", prompt_c)]
    rng = random.Random(EXECUTION_ORDER_SEED + hash(case["case_id"]) % 100000)
    rng.shuffle(arms)

    answers = {}
    raw = {}
    for arm_name, prompt in arms:
        resp = llm_client.call_messages(api_key, model, contestants.SYSTEM_PROMPT, prompt,
                                         max_tokens=300, temperature=0.0)
        try:
            answer = json.loads(resp["text"])
            parse_status = "CLEAN_JSON"
        except (json.JSONDecodeError, TypeError):
            answer = {"epistemic_status": None, "current_physical_claim": None,
                      "relative_historical_support": None, "recommended_action": None,
                      "may_treat_as_current_authoritative": None, "reason_class": "PARSE_FAILURE"}
            parse_status = "PARSE_FAILURE"
        answers[arm_name] = answer
        raw[arm_name] = {"raw_text": resp["text"], "parse_status": parse_status,
                          "input_tokens": resp["input_tokens"], "output_tokens": resp["output_tokens"]}

    gold = oracle.gold_for_case(case)
    flags = {arm: scorer.score_answer(case, answers[arm]) for arm in ("B0", "B1", "C")}

    return {
        "case_id": case["case_id"], "geometry": case["geometry"], "scale_n": case["scale_n"],
        "invalidated": False, "gold": {**gold, "recommended_action_acceptable": list(gold["recommended_action_acceptable"])},
        "answers": answers, "raw": raw, "flags": flags,
        "real_advisory": c_result["real_result"]["advisory"],
        "execution_order": [a[0] for a in arms],
    }


def run_batch(api_key, model, cases, out_path):
    rows = []
    for i, case in enumerate(cases):
        row = run_one_case(api_key, model, case)
        rows.append(row)
        status = "INVALIDATED" if row.get("invalidated") else "ok"
        print(f"[{i+1}/{len(cases)}] {case['case_id']} {case['geometry']:22s} n={case['scale_n']:5d} {status}",
              flush=True)
        with open(out_path, "w") as f:
            json.dump(rows, f, indent=2, default=str)
    return rows


if __name__ == "__main__":
    key_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "calibration"
    api_key = llm_client.load_key(key_path)

    if mode == "calibration":
        cases = world_case_generator.generate_cases([10], world_case_generator.GEOMETRIES.keys(), 1, "CAL_v1")
        out_path = "152_calibration_rows.json"
    elif mode == "confirmatory":
        cases = world_case_generator.generate_cases([10, 100, 1000], world_case_generator.GEOMETRIES.keys(),
                                                       7, "CONFIRM_v1")
        out_path = "153_confirmatory_rows.json"
    else:
        raise SystemExit(f"unknown mode {mode!r}")

    t0 = time.time()
    rows = run_batch(api_key, MODEL, cases, out_path)
    print(f"\nDone: {len(rows)} cases in {time.time()-t0:.1f}s, wrote {out_path}")
