from acfqp import construction_k7_open_world_manifest_reveals_v181r4 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r4 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181


def test_v181r4_reveals_match_frozen_commitments() -> None:
    document = reveals.freeze_open_world_manifest_reveals_v181r4().to_document()
    assert document["protocol_successor_id"] == protocol.EXPECTED_SUCCESSOR_ID
    assert tuple(document["manifest_commitments"]) == protocol.MANIFEST_COMMITMENTS_V181R4
    assert tuple(
        manifest_commitment_v181(row) for row in document["manifest_documents"]
    ) == protocol.MANIFEST_COMMITMENTS_V181R4
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False


def test_v181r4_fresh_denominator_retains_higher_order_partial_dynamics() -> None:
    rows = reveals.MANIFEST_DOCUMENTS_V181R4
    assert [row["horizon"] for row in rows] == [6, 7, 8]
    assert [len(row["support"]) for row in rows] == [2, 2, 3]
    assert [row["state_width"] for row in rows] == [5, 6, 7]
