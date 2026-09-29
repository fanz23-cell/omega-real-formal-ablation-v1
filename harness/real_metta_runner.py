"""Real Omega/MeTTa invocation wrapper. Runs the ACTUAL, unmodified production code
(observation_memory.record_world_event, grounded_reason's real premise-resolution/
admission/eligibility gates, and the real PeTTa/MeTTa `Truth_Revision` evaluation) inside
the isolated container built per doc 147. No handwritten NAL math anywhere in this file --
see doc 149 for the two real bugs found and fixed while proving this chain end-to-end.

This module runs on the HOST (not inside the container) and shells out to `docker exec`/
`docker cp`. It never touches the live `bison_client-omegaclaw-1` container.
"""
import json
import re
import subprocess
import tempfile
import os

ISOLATED_CONTAINER = "omega_isolated_benchmark_20260928"

_SEED_TEMPLATE = """
import sys
sys.path.insert(0, "/PeTTa/repos/OmegaClaw-Core/plugins/observation_memory")
import observation_memory
import json

events = json.loads('''{events_json}''')
results = []
for event in events:
    ok = observation_memory.record_world_event(event)
    results.append({{"event_id": event["event_id"], "recorded": ok}})
print(json.dumps(results))
"""

_EVAL_TEMPLATE = """; auto-generated, real-code-only invocation (doc 149 pattern)
!(import! &self (library lib_import))
!(git-import! "https://github.com/asi-alliance/OmegaClaw-Core.git")
!(import! &self (library OmegaClaw-Core lib_nal))
!(import! &self (library OmegaClaw-Core ./src/skills.metta))
!(import! &self (library OmegaClaw-Core ./plugins/observation_memory/observation_memory.py))
!(import! &self (library OmegaClaw-Core ./plugins/grounded_proposition/grounded_proposition.py))
!(import! &self (library OmegaClaw-Core ./plugins/grounded_reason/grounded_reason.metta))

!(grounded_reason "{json_escaped}")
"""

_ADVISORY_RE = re.compile(r"\(advisory\s+(\{.*?\})\)", re.DOTALL)
# The real underlying error code is nested: (Error UNKNOWN_SKILL_CALL ERR:<real_code>) or
# (Error UNKNOWN_SKILL_CALL ERR:<real_code>)) -- prefer the nested ERR:<code> when present
# (this is the actual grounded_reason_resolve_json()/_resolve_premise_claim() error), fall
# back to the generic wrapper code only if no nested code is found.
_NESTED_ERROR_RE = re.compile(r"ERR:([A-Z_]+)")
_ERROR_RE = re.compile(r"\(Error\s+(\S+)")


def _docker_exec_python(code: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        local_path = f.name
    try:
        remote_path = f"/tmp/{os.path.basename(local_path)}"
        subprocess.run(["docker", "cp", local_path, f"{ISOLATED_CONTAINER}:{remote_path}"],
                       check=True, capture_output=True)
        result = subprocess.run(["docker", "exec", ISOLATED_CONTAINER, "python3", remote_path],
                                 capture_output=True, text=True, timeout=30)
        return result.stdout, result.stderr, result.returncode
    finally:
        os.unlink(local_path)


def _docker_exec_metta(metta_source: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".metta", delete=False) as f:
        f.write(metta_source)
        local_path = f.name
    try:
        remote_path = f"/PeTTa/{os.path.basename(local_path)}"
        subprocess.run(["docker", "cp", local_path, f"{ISOLATED_CONTAINER}:{remote_path}"],
                       check=True, capture_output=True)
        result = subprocess.run(
            ["docker", "exec", ISOLATED_CONTAINER, "sh", "-c",
             f"cd /PeTTa && timeout 60 swipl --stack_limit=8g -q -s src/main.pl -- {remote_path}"],
            capture_output=True, text=True, timeout=90)
        return result.stdout, result.stderr, result.returncode
    finally:
        os.unlink(local_path)


def seed_claims(events: list) -> list:
    """events: list of dicts already in record_world_event()'s exact real schema
    (see doc 146's mapping table -- this function performs NO reshaping itself,
    that's ingestion_adapter.py's job). Returns list of {event_id, recorded} dicts."""
    code = _SEED_TEMPLATE.format(events_json=json.dumps(events))
    stdout, stderr, rc = _docker_exec_python(code)
    if rc != 0:
        raise RuntimeError(f"seed_claims failed (rc={rc}): {stderr}")
    return json.loads(stdout.strip().splitlines()[-1])


def real_grounded_reason(premise_ref_1: str, premise_ref_2: str, operator: str = "revision") -> dict:
    """Invokes the REAL, unmodified grounded_reason MeTTa skill end-to-end (real premise
    lookup, real admission gate, real Stage-10 eligibility gate, real Truth_Revision
    evaluation, real materialize_advisory). Returns a dict:
      {"ok": True, "advisory": {...}, "raw_result": "...", "metta_stdout": "..."}
    or
      {"ok": False, "error_code": "...", "metta_stdout": "..."}
    """
    spec = json.dumps({"premise_ref_1": premise_ref_1, "premise_ref_2": premise_ref_2,
                        "operator": operator})
    json_escaped = spec.replace('\\', '\\\\').replace('"', '\\"')
    metta_source = _EVAL_TEMPLATE.format(json_escaped=json_escaped)
    stdout, stderr, rc = _docker_exec_metta(metta_source)
    if rc != 0:
        return {"ok": False, "error_code": "METTA_PROCESS_FAILED", "metta_stdout": stdout,
                "metta_stderr": stderr}
    last_line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    advisory_match = _ADVISORY_RE.search(last_line)
    if advisory_match:
        advisory = json.loads(advisory_match.group(1))
        return {"ok": True, "advisory": advisory, "raw_result": last_line, "metta_stdout": stdout}
    nested_match = _NESTED_ERROR_RE.search(last_line)
    if nested_match:
        return {"ok": False, "error_code": nested_match.group(1), "metta_stdout": stdout}
    error_match = _ERROR_RE.search(last_line)
    if error_match:
        return {"ok": False, "error_code": error_match.group(1), "metta_stdout": stdout}
    return {"ok": False, "error_code": "UNPARSEABLE_OUTPUT", "metta_stdout": stdout}


if __name__ == "__main__":
    # Self-test: G6 near-tie-high geometry (TRUE 0.91 / FALSE 0.89), different subject/predicate
    # than the doc-149 witness, to confirm the wrapper generalizes beyond one hand-tuned case.
    events = [
        {"event_id": "selftest_g6_true", "subject": "alarm_9", "predicate": "armed", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 2000.0,
         "confidence": 0.91, "predicate_aspect": "STATE", "semantic_entity_id": ""},
        {"event_id": "selftest_g6_false", "subject": "alarm_9", "predicate": "armed", "value": False,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 2001.0,
         "confidence": 0.89, "predicate_aspect": "STATE", "semantic_entity_id": ""},
    ]
    print("seed:", seed_claims(events))
    result = real_grounded_reason("obs:selftest_g6_true", "obs:selftest_g6_false", "revision")
    print("result:", json.dumps(result, indent=2))
