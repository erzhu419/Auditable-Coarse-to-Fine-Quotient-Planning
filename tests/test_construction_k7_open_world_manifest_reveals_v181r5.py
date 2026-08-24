from acfqp import construction_k7_open_world_manifest_reveals_v181r5 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r5 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181


def test_v181r5_reveals_match_frozen_commitments() -> None:
    document = reveals.freeze_open_world_manifest_reveals_v181r5().to_document()
    assert document["protocol_successor_id"] == protocol.EXPECTED_SUCCESSOR_ID
    assert tuple(document["manifest_commitments"]) == protocol.MANIFEST_COMMITMENTS_V181R5
    assert tuple(
        manifest_commitment_v181(row) for row in document["manifest_documents"]
    ) == protocol.MANIFEST_COMMITMENTS_V181R5
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False


def test_v181r5_fresh_denominator_retains_higher_order_partial_dynamics() -> None:
    rows = reveals.MANIFEST_DOCUMENTS_V181R5
    assert [row["horizon"] for row in rows] == [8, 9, 10]
    assert [len(row["support"]) for row in rows] == [2, 2, 3]
    assert [row["state_width"] for row in rows] == [5, 6, 7]
    assert all(row["terminal_program"] == ["EQ", ["S", 3], ["K", 0]] for row in rows)
