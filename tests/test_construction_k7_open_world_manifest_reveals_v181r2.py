from __future__ import annotations

from acfqp import construction_k7_open_world_manifest_reveals_v181r2 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r2 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181


def test_v181r2_reveals_match_frozen_commitments_without_queries() -> None:
    value = reveals.freeze_open_world_manifest_reveals_v181r2()
    document = value.to_document()
    assert tuple(
        manifest_commitment_v181(row) for row in document["manifest_documents"]
    ) == protocol.MANIFEST_COMMITMENTS_V181R2
    assert document["preimages_revealed_after_commitment_freeze"] is True
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False


def test_v181r2_reveals_cover_higher_horizon_partial_dynamics() -> None:
    document = reveals.freeze_open_world_manifest_reveals_v181r2().to_document()
    assert [row["horizon"] for row in document["manifest_documents"]] == [5, 6, 7]
    assert [len(row["support"]) for row in document["manifest_documents"]] == [2, 2, 3]
    assert document["official_execution_allowed"] is False
