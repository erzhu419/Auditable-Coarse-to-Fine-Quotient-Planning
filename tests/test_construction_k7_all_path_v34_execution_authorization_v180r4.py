import hashlib

from acfqp import construction_k7_all_path_v34_execution_authorization_v180r4 as authorization


def test_v34_authorization_is_source_pinned_and_outcome_free() -> None:
    frozen = authorization.freeze_v34_execution_authorization_v180r4()
    document = frozen.to_document()
    assert frozen.authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
    assert len(frozen.canonical_bytes) == authorization.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        authorization.EXPECTED_CANONICAL_SHA256
    )
    assert document["production_execution_slot"]["terminal_code"] == (
        "ABSTRACT_CERTIFIED"
    )
    assert len(document["source_facts"]) == 6
    assert len({row["sha256"] for row in document["source_facts"]}) == 6
    assert document["output_root_must_be_absent"] is True
    assert document["same_authorization_rerun_after_progress_or_terminal_forbidden"] is True
    assert document["fresh_v34_execution_started"] is False
    assert document["production_outcome_accessed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
