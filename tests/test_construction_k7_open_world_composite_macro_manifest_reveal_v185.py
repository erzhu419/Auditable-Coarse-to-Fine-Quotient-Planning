from acfqp import construction_k7_open_world_composite_macro_manifest_reveal_v185 as reveal
from acfqp import construction_k7_open_world_composite_macro_protocol_v185 as protocol
from acfqp.open_world_composite_macro_oracle_v185 import (
    composite_macro_manifest_commitment_v185,
)


def test_v185_reveal_matches_prior_commit_and_accesses_no_outcome() -> None:
    document = reveal.freeze_open_world_composite_macro_manifest_reveal_v185().to_document()
    assert document["manifest_reveal_id"] == reveal.EXPECTED_REVEAL_ID
    assert document["protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
    assert tuple(
        composite_macro_manifest_commitment_v185(row)
        for row in document["manifest_documents"]
    ) == protocol.MANIFEST_COMMITMENTS_V185
    assert document["preimages_revealed_after_protocol_commit"] is True
    assert document["source_or_target_oracle_query_count"] == 0
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["scientific_success_claimed"] is False
    assert document["official_execution_allowed"] is False
