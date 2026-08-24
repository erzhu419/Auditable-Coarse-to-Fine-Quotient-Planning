from acfqp import construction_k7_open_world_manifest_reveals_v181r3 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r3 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181


def test_v181r3_reveals_match_prior_commitments_exactly() -> None:
    document = reveals.freeze_open_world_manifest_reveals_v181r3().to_document()
    assert document["protocol_successor_id"] == protocol.EXPECTED_SUCCESSOR_ID
    assert tuple(document["manifest_commitments"]) == protocol.MANIFEST_COMMITMENTS_V181R3
    assert tuple(
        manifest_commitment_v181(row) for row in document["manifest_documents"]
    ) == protocol.MANIFEST_COMMITMENTS_V181R3
    assert document["preimages_revealed_after_commitment_freeze"] is True
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False


def test_v181r3_reveals_are_higher_horizon_partial_dynamics() -> None:
    documents = reveals.MANIFEST_DOCUMENTS_V181R3
    assert [row["horizon"] for row in documents] == [6, 7, 8]
    assert [len(row["support"]) for row in documents] == [2, 2, 3]
    assert [row["state_width"] for row in documents] == [5, 6, 7]
    assert all(
        any("W" in repr(expression) for expression in row["transition_programs"])
        for row in documents
    )
