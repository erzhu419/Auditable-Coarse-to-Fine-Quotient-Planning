import hashlib

from acfqp import construction_k7_full_ground_fallback_source_catalog_evidence_freeze_v180r7r1 as frozen


def test_v180r7r1_source_catalog_manifest_and_repair_are_exactly_frozen() -> None:
    value = frozen.load_frozen_full_ground_fallback_source_catalog_manifest_v180r7r1()
    document = value.to_document()
    assert value.manifest_id == frozen.EXPECTED_MANIFEST_ID
    assert value.repair_id == frozen.EXPECTED_REPAIR_ID
    assert len(value.canonical_bytes) == frozen.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == (
        frozen.EXPECTED_CANONICAL_SHA256
    )
    assert document["source_catalog_manifest_id"] == frozen.EXPECTED_MANIFEST_ID
    assert document["source_closure_repair_id"] == frozen.EXPECTED_REPAIR_ID
    assert document["source_catalog_facts_sha256"] == (
        frozen.EXPECTED_CATALOG_FACTS_SHA256
    )
    assert document["source_catalog_module_count"] == 1_955
    assert document["source_catalog_source_byte_count"] == 49_484_313
    assert len(document["source_closure_repair"]["root_modules"]) == 151
    assert document["source_closure_repair"]["reachable_runtime"][
        "module_count"
    ] == 307
    assert document["source_closure_repair"]["reachable_runtime"][
        "source_byte_count"
    ] == 15_129_926


def test_v180r7r1_source_catalog_freeze_retains_all_claim_locks() -> None:
    document = (
        frozen.load_frozen_full_ground_fallback_source_catalog_manifest_v180r7r1()
        .to_document()
    )
    assert document["fresh_execution_authorization_issued"] is False
    assert document["fresh_fallback_execution_started"] is False
    assert document["scientific_occurrence_executed"] is False
    assert document["production_outcome_accessed"] is False
    assert document["producer_free_verification_present"] is False
    assert document["success_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["construction_only"] is True
