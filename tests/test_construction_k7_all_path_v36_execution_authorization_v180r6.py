import hashlib

from acfqp import construction_k7_all_path_v36_execution_authorization_v180r6 as authorization


def test_v180r6_authorizes_only_the_fresh_local_recovery_path() -> None:
    frozen = authorization.freeze_v36_execution_authorization_v180r6()
    document = frozen.to_document()
    assert frozen.authorization_id == document["v36_execution_authorization_id"]
    assert document["production_execution_slot"]["terminal_code"] == (
        "LOCAL_GROUND_RECOVERY"
    )
    assert len(document["source_facts"]) == 10
    assert document["certificate_failure_before_local_recovery_required"] is True
    assert document["ground_distinctions_before_certificate_failure_forbidden"] is True
    assert document["fresh_v36_execution_started"] is False
    assert document["production_outcome_accessed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
    if authorization.EXPECTED_AUTHORIZATION_ID != "0" * 64:
        assert frozen.authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
        assert len(frozen.canonical_bytes) == authorization.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
            authorization.EXPECTED_CANONICAL_SHA256
        )
