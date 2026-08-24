from acfqp import construction_k7_open_world_total_machine_manifest_reveal_v182r2 as reveal
from acfqp import construction_k7_open_world_total_machine_protocol_v182r2 as protocol
from acfqp.open_world_machine_oracle_v182 import machine_manifest_commitment_v182


def test_v182r2_reveal_opens_exact_frozen_commitments_without_queries() -> None:
    document = reveal.freeze_open_world_total_machine_manifest_reveal_v182r2().to_document()
    commitments = tuple(
        machine_manifest_commitment_v182(row)
        for row in reveal.MANIFEST_DOCUMENTS_V182R2
    )
    assert commitments == protocol.MANIFEST_COMMITMENTS_V182R2
    assert document["manifest_commitments"] == list(commitments)
    assert document["preimages_revealed_after_protocol_commit"] is True
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False
    assert document["official_execution_allowed"] is False
