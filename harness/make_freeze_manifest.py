"""Generates the freeze manifest (directive section 27 / doc 151): hashes every
result-affecting file BEFORE any confirmatory paid call. Re-run (with a note in doc 151)
if anything result-affecting changes after freezing -- never a silent repair.
"""
import hashlib
import json
import os

FROZEN_FILES = [
    "world_case_generator.py", "oracle.py", "contestants.py", "fairness_check.py",
    "scorer.py", "real_metta_runner.py", "negative_controls.py", "llm_client.py",
    "run_confirmatory.py",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def make_manifest():
    manifest = {"frozen_at_utc": None, "files": {}, "config": {
        "model": "claude-sonnet-4-5-20250929", "temperature": 0.0, "max_tokens": 300,
        "timeout_s": 60, "retry_policy": "none (a valid parse failure is scored PARSE_FAILURE, "
                                          "never retried; only a transport/timeout error may be "
                                          "retried, bounded, identically across all arms)",
        "execution_order_seed": 20260928, "bootstrap_seed": 12345,
        "relative_historical_support_threshold": 0.05,
        "practically_meaningful_effect_pp": 10,
        "confirmatory_geometries": 9, "confirmatory_scales": [10, 100, 1000],
        "confirmatory_reps_per_cell": 7, "confirmatory_n_cases": 189,
        "calibration_scales": [10], "calibration_reps_per_cell": 1, "calibration_n_cases": 9,
    }}
    for fname in FROZEN_FILES:
        if os.path.exists(fname):
            manifest["files"][fname] = sha256_file(fname)
        else:
            manifest["files"][fname] = "MISSING"
    return manifest


if __name__ == "__main__":
    manifest = make_manifest()
    with open("151_freeze_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))
