from pathlib import Path

from acfqp import construction_k7_open_world_manifest_reveals_v181r1 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r1 as successor
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181


def test_all_reveal_preimages_match_frozen_successor_commitments() -> None:
    document = reveals.freeze_open_world_manifest_reveals_v181r1().to_document()
    assert tuple(document["manifest_commitments"]) == successor.MANIFEST_COMMITMENTS_V181R1
    assert tuple(
        manifest_commitment_v181(row) for row in document["manifest_documents"]
    ) == successor.MANIFEST_COMMITMENTS_V181R1
    assert document["all_reveal_preimages_match_preregistered_commitments"] is True


def test_reveal_itself_does_not_query_target_outcomes() -> None:
    document = reveals.freeze_open_world_manifest_reveals_v181r1().to_document()
    assert document["target_oracle_query_count_at_reveal"] == 0
    assert document["target_outcomes_accessed_at_reveal"] is False


def test_retained_reveal_bytes_are_exact() -> None:
    value = reveals.freeze_open_world_manifest_reveals_v181r1()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r1_open_world_manifest_reveals.json"
    )
    assert path.read_bytes() == value.canonical_bytes
