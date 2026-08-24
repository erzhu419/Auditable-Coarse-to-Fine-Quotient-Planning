from __future__ import annotations

from acfqp import construction_k7_open_world_machine_manifest_reveal_v182r1 as reveal
from acfqp import construction_k7_open_world_machine_protocol_v182 as protocol
from acfqp.open_world_machine_oracle_v182 import (
    machine_manifest_commitment_v182,
    reveal_opaque_machine_oracle_v182,
)
from acfqp.phase3e_ids import canonical_json_bytes


def test_v182r1_reveal_exactly_opens_prior_commitments_without_queries() -> None:
    frozen = reveal.freeze_open_world_machine_manifest_reveal_v182r1()
    document = frozen.to_document()
    commitments = tuple(
        machine_manifest_commitment_v182(row)
        for row in reveal.MANIFEST_DOCUMENTS_V182R1
    )
    assert commitments == protocol.MANIFEST_COMMITMENTS_V182
    assert document["manifest_commitments"] == list(commitments)
    assert document["preimages_revealed_after_protocol_commit"] is True
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False


def test_v182r1_revealed_manifests_build_three_opaque_oracles() -> None:
    oracles = tuple(
        reveal_opaque_machine_oracle_v182(
            manifest_bytes=canonical_json_bytes(document),
            expected_commitment=commitment,
        )
        for document, commitment in zip(
            reveal.MANIFEST_DOCUMENTS_V182R1,
            protocol.MANIFEST_COMMITMENTS_V182,
            strict=True,
        )
    )
    assert tuple(row.schema_signature() for row in oracles) == (
        (3, 1, 2),
        (3, 1, 2),
        (4, 1, 2),
    )
    assert all(row.legal_actions() == ((0,), (1,)) for row in oracles)
