import hashlib

from acfqp import construction_k7_all_path_v34_execution_authorization_v180r5 as authorization
from acfqp import construction_k7_all_path_v34_failure_freeze_v180r4 as failure


def test_v180r5_preserves_failure_and_authorizes_only_corrected_successor() -> None:
    frozen = authorization.freeze_v34_execution_authorization_v180r5()
    document = frozen.to_document()
    assert frozen.authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
    assert len(frozen.canonical_bytes) == authorization.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        authorization.EXPECTED_CANONICAL_SHA256
    )
    assert document["preserved_v180r4_failure_id"] == failure.EXPECTED_FAILURE_ID
    assert document["v180r4_same_identity_rerun"] is False
    assert document["corrected_boundary"] == "PATH_SUBCLASS_ACCEPTED_BY_ISINSTANCE"
    assert document["production_execution_slot"]["terminal_code"] == (
        "ABSTRACT_CERTIFIED"
    )
    assert len(document["source_facts"]) == 7
    assert document["fresh_v34_execution_started"] is False
    assert document["production_outcome_accessed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
