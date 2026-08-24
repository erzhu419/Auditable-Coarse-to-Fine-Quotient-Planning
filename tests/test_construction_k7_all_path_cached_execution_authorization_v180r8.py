from __future__ import annotations

from acfqp import construction_k7_all_path_cached_execution_authorization_v180r8 as authorization


def test_v180r8_authorization_is_outcome_free_and_exact() -> None:
    frozen = authorization.freeze_cached_execution_authorization_v180r8()
    document = frozen.to_document()
    assert document["cached_execution_authorization_id"] == frozen.authorization_id
    assert document["production_execution_slot"]["terminal_code"] == (
        "CACHED_EXACT_INFEASIBLE"
    )
    assert document["logical_occurrence_id"] == authorization.LOGICAL_OCCURRENCE_ID
    assert document["selected_plan_id"] == authorization.SELECTED_PLAN_ID
    assert len(document["source_facts"]) == 10
    assert len(document["proof_source_facts"]) == 21
    assert document["fresh_cached_execution_started"] is False
    assert document["production_outcome_accessed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_v180r8_authorization_pins_the_complete_proof_source_inventory() -> None:
    document = authorization.freeze_cached_execution_authorization_v180r8().to_document()
    paths = [row["relative_path"] for row in document["proof_source_facts"]]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))
    assert "artifacts/phase05/g2048/manifest.json" in paths
    assert "artifacts/phase05/g2048/ground/enumeration.json" in paths
    assert "artifacts/phase05/g2048/result/certificate_or_fallback.json" in paths
