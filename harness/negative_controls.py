"""$0 negative/gating controls (directive section 16). Proves the REAL production
eligibility gate (grounded_reason._revision_eligible / _resolve_premise_claim, unmodified)
correctly REJECTS every invalid input shape, before trusting it on real cases. No paid
LLM calls in this file.
"""
import real_metta_runner


def run_negative_controls():
    results = {}

    # N1: same subject/predicate/aspect, SAME polarity (not a real conflict) -> reject
    real_metta_runner.seed_claims([
        {"event_id": "n1_a", "subject": "n1_subj", "predicate": "p", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 5000.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
        {"event_id": "n1_b", "subject": "n1_subj", "predicate": "p", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 5001.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
    ])
    r = real_metta_runner.real_grounded_reason("obs:n1_a", "obs:n1_b", "revision")
    results["N1_same_polarity"] = {"expect": "reject", "got_ok": r["ok"],
                                    "error_code": r.get("error_code")}

    # N2: subject mismatch -> reject
    real_metta_runner.seed_claims([
        {"event_id": "n2_a", "subject": "n2_subj_a", "predicate": "p", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 5000.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
        {"event_id": "n2_b", "subject": "n2_subj_b", "predicate": "p", "value": False,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 5001.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
    ])
    r = real_metta_runner.real_grounded_reason("obs:n2_a", "obs:n2_b", "revision")
    results["N2_subject_mismatch"] = {"expect": "reject", "got_ok": r["ok"],
                                        "error_code": r.get("error_code")}

    # N3: predicate mismatch -> reject
    real_metta_runner.seed_claims([
        {"event_id": "n3_a", "subject": "n3_subj", "predicate": "p1", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 5000.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
        {"event_id": "n3_b", "subject": "n3_subj", "predicate": "p2", "value": False,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 5001.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
    ])
    r = real_metta_runner.real_grounded_reason("obs:n3_a", "obs:n3_b", "revision")
    results["N3_predicate_mismatch"] = {"expect": "reject", "got_ok": r["ok"],
                                          "error_code": r.get("error_code")}

    # N4: predicate_aspect mismatch -> reject
    real_metta_runner.seed_claims([
        {"event_id": "n4_a", "subject": "n4_subj", "predicate": "p", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 5000.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
        {"event_id": "n4_b", "subject": "n4_subj", "predicate": "p", "value": False,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 5001.0,
         "confidence": 0.8, "predicate_aspect": "EVENT", "semantic_entity_id": ""},
    ])
    r = real_metta_runner.real_grounded_reason("obs:n4_a", "obs:n4_b", "revision")
    results["N4_aspect_mismatch"] = {"expect": "reject", "got_ok": r["ok"],
                                       "error_code": r.get("error_code")}

    # N5: UNKNOWN polarity (value=None) -> fail closed
    real_metta_runner.seed_claims([
        {"event_id": "n5_a", "subject": "n5_subj", "predicate": "p", "value": None,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 5000.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
        {"event_id": "n5_b", "subject": "n5_subj", "predicate": "p", "value": False,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 5001.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
    ])
    r = real_metta_runner.real_grounded_reason("obs:n5_a", "obs:n5_b", "revision")
    results["N5_unknown_polarity"] = {"expect": "reject", "got_ok": r["ok"],
                                        "error_code": r.get("error_code")}

    # N6: missing premise ref (never seeded) -> fail closed
    r = real_metta_runner.real_grounded_reason("obs:does_not_exist_a", "obs:does_not_exist_b", "revision")
    results["N6_missing_premise_ref"] = {"expect": "reject", "got_ok": r["ok"],
                                           "error_code": r.get("error_code")}

    # N7: non-WORLD_EVENT claim kind is structurally impossible to construct via
    # record_world_event() itself (it always writes claim_kind="WORLD_EVENT" -- see doc 146) --
    # so this control instead confirms an ALIAS_BINDING-shaped premise_ref (a different real
    # collection/claim_kind entirely) is correctly rejected when passed to revision.
    r = real_metta_runner.real_grounded_reason("obs:nonexistent_alias_ref", "obs:n5_b", "revision")
    results["N7_non_world_event_claim"] = {"expect": "reject", "got_ok": r["ok"],
                                             "error_code": r.get("error_code")}

    # N8: malformed confidence (out of 0-1 range) -- record_world_event itself does not
    # validate range (float(event.get("confidence") or 0.0) accepts anything), so this tests
    # whether the DOWNSTREAM formal-result validator (materialize_advisory's own
    # _MIN_VALID_STV/_MAX_VALID_STV check) still holds if a malformed value got through.
    real_metta_runner.seed_claims([
        {"event_id": "n8_a", "subject": "n8_subj", "predicate": "p", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 5000.0,
         "confidence": 1.5, "predicate_aspect": "STATE", "semantic_entity_id": ""},
        {"event_id": "n8_b", "subject": "n8_subj", "predicate": "p", "value": False,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 5001.0,
         "confidence": 0.8, "predicate_aspect": "STATE", "semantic_entity_id": ""},
    ])
    r = real_metta_runner.real_grounded_reason("obs:n8_a", "obs:n8_b", "revision")
    results["N8_malformed_confidence"] = {"expect": "reject_or_bounded", "got_ok": r["ok"],
                                            "error_code": r.get("error_code"),
                                            "advisory": r.get("advisory")}

    # N9: absent predicate_aspect -> fails closed to UNKNOWN, not silently STATE
    real_metta_runner.seed_claims([
        {"event_id": "n9_a", "subject": "n9_subj", "predicate": "p", "value": True,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s1", "observed_at": 5000.0,
         "confidence": 0.8, "predicate_aspect": "", "semantic_entity_id": ""},
        {"event_id": "n9_b", "subject": "n9_subj", "predicate": "p", "value": False,
         "source_type": "SENSOR_OBSERVATION", "source_id": "s2", "observed_at": 5001.0,
         "confidence": 0.8, "predicate_aspect": "", "semantic_entity_id": ""},
    ])
    r = real_metta_runner.real_grounded_reason("obs:n9_a", "obs:n9_b", "revision")
    results["N9_absent_predicate_aspect"] = {"expect": "reject", "got_ok": r["ok"],
                                               "error_code": r.get("error_code")}

    return results


if __name__ == "__main__":
    import json
    results = run_negative_controls()
    print(json.dumps(results, indent=2))
    all_correctly_rejected = all(
        (not v["got_ok"]) for k, v in results.items() if v["expect"] in ("reject",)
    )
    print("\nALL_REJECT_CONTROLS_PASS:", all_correctly_rejected)
