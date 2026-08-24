import hashlib

from acfqp import construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r1 as authorization


def test_v180r12r1_authorization_is_outcome_free_and_source_closed() -> None:
    frozen = (
        authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r1()
    )
    document = frozen.to_document()
    assert frozen.authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
    assert len(frozen.canonical_bytes) == authorization.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        authorization.EXPECTED_CANONICAL_SHA256
    )
    assert document["source_group_count"] == 5
    assert document["terminal_code_count"] == 10
    assert document["source_outcomes_accessed_by_authorization"] is False
    assert document["aggregation_execution_started"] is False
    assert document["all_source_independent_verifiers_must_replay"] is True
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
    source_paths = {row["relative_path"] for row in document["source_facts"]}
    assert any("aggregation_finalizer" in row for row in source_paths)
    assert any("aggregation_independent_verifier" in row for row in source_paths)
    assert any("run_v180r12r1" in row for row in source_paths)
