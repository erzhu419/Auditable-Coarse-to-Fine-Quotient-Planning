from acfqp import construction_k7_open_world_ranked_machine_manifest_reveal_v183 as reveal
from acfqp import construction_k7_open_world_ranked_machine_protocol_v183 as protocol
from acfqp.open_world_ranked_machine_oracle_v183 import (
    ranked_machine_manifest_commitment_v183,
)


def test_v183_manifest_reveal_matches_prior_commitments_without_outcomes() -> None:
    frozen = reveal.freeze_open_world_ranked_machine_manifest_reveal_v183()
    document = frozen.to_document()
    assert tuple(
        ranked_machine_manifest_commitment_v183(row)
        for row in reveal.MANIFEST_DOCUMENTS_V183
    ) == protocol.MANIFEST_COMMITMENTS_V183
    assert document["manifest_reveal_id"] == reveal.EXPECTED_REVEAL_ID
    assert document["preimages_revealed_after_protocol_commit"] is True
    assert document["source_or_target_oracle_query_count"] == 0
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["scientific_success_claimed"] is False
