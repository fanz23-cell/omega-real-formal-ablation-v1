"""$0 witness step 1: seed two real, opposing WORLD_EVENT claims via the REAL,
unmodified observation_memory.record_world_event() function -- no reimplementation,
no monkeypatched CHROMA_PATH (isolation achieved at the container/mount level
instead, per 147's isolation contract). Run inside the isolated container only.
"""
import sys
sys.path.insert(0, "/PeTTa/repos/OmegaClaw-Core/plugins/observation_memory")
import observation_memory

# Witness case (directive section 23): door_1 / locked / STATE, TRUE 0.80 vs FALSE 0.80
claim_true = {
    "event_id": "witness_claim_true_001",
    "subject": "door_1",
    "predicate": "locked",
    "value": True,
    "source_type": "SENSOR_OBSERVATION",
    "source_id": "witness_sensor_a",
    "observed_at": 1000.0,
    "confidence": 0.80,
    "predicate_aspect": "STATE",
    "semantic_entity_id": "",
}
claim_false = {
    "event_id": "witness_claim_false_001",
    "subject": "door_1",
    "predicate": "locked",
    "value": False,
    "source_type": "SENSOR_OBSERVATION",
    "source_id": "witness_sensor_b",
    "observed_at": 1001.0,
    "confidence": 0.80,
    "predicate_aspect": "STATE",
    "semantic_entity_id": "",
}

ok1 = observation_memory.record_world_event(claim_true)
ok2 = observation_memory.record_world_event(claim_false)
print("record_world_event(claim_true) ->", ok1)
print("record_world_event(claim_false) ->", ok2)
print("premise_ref_1 = obs:" + claim_true["event_id"])
print("premise_ref_2 = obs:" + claim_false["event_id"])

# Sanity: query it back through the real read-only skill, to confirm it's really durable
recent = observation_memory.recent(limit=5)
print("recent() ->", recent)
