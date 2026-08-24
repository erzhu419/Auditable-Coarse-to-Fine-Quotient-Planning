import hashlib

from acfqp import construction_k7_all_path_fallback_execution_authorization_v180r7 as authorization


def test_v180r7_authorizes_one_fresh_full_fallback_occurrence() -> None:
    frozen = authorization.freeze_fallback_execution_authorization_v180r7()
    document = frozen.to_document()
    assert frozen.authorization_id == document["fallback_execution_authorization_id"]
    assert document["production_execution_slot"]["terminal_code"] == (
        "FULL_GROUND_FALLBACK"
    )
    assert len(document["source_facts"]) == 10
    assert len(document["retained_predecessor_input_facts"]) == 3
    assert document["three_route_family_vectors_must_remain_separate"] is True
    assert document["summary_to_counter_translation_forbidden"] is True
    assert document["fresh_fallback_execution_started"] is False
    assert document["production_outcome_accessed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
    if authorization.EXPECTED_AUTHORIZATION_ID != "0" * 64:
        assert frozen.authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
        assert len(frozen.canonical_bytes) == authorization.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
            authorization.EXPECTED_CANONICAL_SHA256
        )
