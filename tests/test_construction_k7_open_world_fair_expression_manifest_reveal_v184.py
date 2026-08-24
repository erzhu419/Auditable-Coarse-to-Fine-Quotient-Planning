from acfqp import construction_k7_open_world_fair_expression_manifest_reveal_v184 as reveal
from acfqp import construction_k7_open_world_fair_expression_protocol_v184 as protocol
from acfqp.open_world_fair_expression_oracle_v184 import (
    fair_expression_manifest_commitment_v184,
)


def test_v184_manifest_reveal_matches_prior_commitments_without_queries() -> None:
    document = reveal.freeze_open_world_fair_expression_manifest_reveal_v184().to_document()
    assert document["manifest_reveal_id"] == reveal.EXPECTED_REVEAL_ID
    assert tuple(
        fair_expression_manifest_commitment_v184(row)
        for row in reveal.MANIFEST_DOCUMENTS_V184
    ) == protocol.MANIFEST_COMMITMENTS_V184
    assert document["preimages_revealed_after_protocol_commit"] is True
    assert document["source_or_target_oracle_query_count"] == 0
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["scientific_success_claimed"] is False
    assert document["official_execution_allowed"] is False
