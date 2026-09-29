"""Re-runs the exact same 189 confirmatory cases through a LOCAL model (via Ollama)
instead of claude-sonnet-4-5, reusing the already-computed real Omega/MeTTa advisory
numbers verbatim (case_id-matched from 153_confirmatory_rows.json) -- the advisory is a
property of the case's injected claims, not of which downstream LLM reads it, so this is
an exact reuse, not an approximation. Only the LLM-answering step changes.
"""
import json
import random
import re
import sys
import time

import contestants
import fairness_check
import ollama_client
import oracle
import scorer
import world_case_generator

MODEL = "qwen3.5:9b"
EXECUTION_ORDER_SEED = 20260929

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_answer(raw_text):
    try:
        return json.loads(raw_text), "CLEAN_JSON"
    except (json.JSONDecodeError, TypeError):
        pass
    m = _JSON_RE.search(raw_text or "")
    if m:
        try:
            return json.loads(m.group(0)), "EXTRACTED_JSON"
        except json.JSONDecodeError:
            pass
    return None, "PARSE_FAILURE"


def load_real_advisories(prior_rows_path):
    """case_id -> real_advisory dict, reused verbatim from the sonnet-4-5 confirmatory run."""
    rows = json.load(open(prior_rows_path))
    return {r["case_id"]: r["real_advisory"] for r in rows if not r.get("invalidated")}


def run_one_case(case, real_advisory, model):
    prompt_b0 = contestants.render_B0(case)
    prompt_b1 = contestants.render_B1(case)
    prompt_c = contestants.render_C_with_advisory(case, real_advisory)

    fairness = fairness_check.check_case_fairness(case, prompt_b0, prompt_b1, prompt_c)
    if not fairness["pass"]:
        return {"case_id": case["case_id"], "invalidated": True,
                "fairness_violations": fairness["violations"]}

    arms = [("B0", prompt_b0), ("B1", prompt_b1), ("C", prompt_c)]
    rng = random.Random(EXECUTION_ORDER_SEED + hash(case["case_id"]) % 100000)
    rng.shuffle(arms)

    answers, raw = {}, {}
    for arm_name, prompt in arms:
        resp = ollama_client.call_messages(None, model, contestants.SYSTEM_PROMPT, prompt,
                                            max_tokens=300, temperature=0.0)
        parsed, parse_status = parse_json_answer(resp["text"])
        answer = parsed if parsed is not None else {
            "epistemic_status": None, "current_physical_claim": None,
            "relative_historical_support": None, "recommended_action": None,
            "may_treat_as_current_authoritative": None, "reason_class": "PARSE_FAILURE"}
        answers[arm_name] = answer
        raw[arm_name] = {"raw_text": resp["text"], "parse_status": parse_status,
                          "input_tokens": resp["input_tokens"], "output_tokens": resp["output_tokens"]}

    gold = oracle.gold_for_case(case)
    flags = {arm: scorer.score_answer(case, answers[arm]) for arm in ("B0", "B1", "C")}

    return {
        "case_id": case["case_id"], "geometry": case["geometry"], "scale_n": case["scale_n"],
        "invalidated": False,
        "gold": {**gold, "recommended_action_acceptable": list(gold["recommended_action_acceptable"])},
        "answers": answers, "raw": raw, "flags": flags, "real_advisory": real_advisory,
        "execution_order": [a[0] for a in arms], "model": model,
    }


if __name__ == "__main__":
    prior_rows_path = sys.argv[1] if len(sys.argv) > 1 else "153_confirmatory_rows.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "159_local_model_confirmatory_rows.json"

    # SCOPE NOTE (disclosed, not silent): only scale=10 is run for the local model. At
    # scale=1000, prompts run ~25-30K input tokens (the same size that made the paid sonnet
    # run cost $48.60); this CPU-only local model processes prompt tokens at ~35 tok/s, so a
    # single scale=1000 call would take ~12-14 minutes -- 189 such calls would take 40+ hours.
    # scale=10 alone (63 cases, 189 calls) still covers all 9 preregistered geometries with
    # full n=7 replication, at ~15-20s/call (~50-60 min total) -- a properly-scoped pilot, not
    # a shortcut. See docs/159_LOCAL_MODEL_PILOT_REPORT.md for the full disclosure.
    scales_to_run = [10]
    advisories = load_real_advisories(prior_rows_path)
    cases = world_case_generator.generate_cases(
        scales_to_run, world_case_generator.GEOMETRIES.keys(), 7, "CONFIRM_v1")

    # Resume support: the previous session's process was killed mid-run (ollama server +
    # this script both died when the parent session ended, not a crash of either). Skip
    # case_ids already present in out_path rather than re-spending ~15-20s/call redoing them.
    rows = []
    done_ids = set()
    try:
        with open(out_path) as f:
            rows = json.load(f)
            done_ids = {r["case_id"] for r in rows}
        print(f"Resuming: {len(done_ids)} cases already done, skipping those.")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    t0 = time.time()
    for i, case in enumerate(cases):
        if case["case_id"] in done_ids:
            continue
        advisory = advisories.get(case["case_id"])
        if advisory is None:
            print(f"[{i+1}/{len(cases)}] {case['case_id']} SKIPPED (no prior advisory found)")
            continue
        row = run_one_case(case, advisory, MODEL)
        rows.append(row)
        status = "INVALIDATED" if row.get("invalidated") else "ok"
        elapsed = time.time() - t0
        print(f"[{i+1}/{len(cases)}] {case['case_id']} {case['geometry']:22s} "
              f"n={case['scale_n']:5d} {status} ({elapsed:.0f}s elapsed)", flush=True)
        with open(out_path, "w") as f:
            json.dump(rows, f, indent=2, default=str)

    print(f"\nDone: {len(rows)} cases in {time.time()-t0:.1f}s, wrote {out_path}")
