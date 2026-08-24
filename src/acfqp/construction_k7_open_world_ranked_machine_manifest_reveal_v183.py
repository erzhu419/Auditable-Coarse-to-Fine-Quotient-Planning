"""Fresh V183 manifest preimages revealed after the protocol commit."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v183 as domains
from acfqp import construction_k7_open_world_ranked_machine_protocol_v183 as protocol
from acfqp.open_world_ranked_machine_oracle_v183 import (
    ranked_machine_manifest_commitment_v183,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V183 = (
    {
        "schema": "acfqp.opaque_ranked_machine_manifest.v183",
        "manifest_index": 0,
        "reveal_salt": "d608b7b40833bde6f9a1fa1bee9d452e93ce47a80414469b38508371bd2e8528",
        "state_width": 2,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "coordinate_0_multiplier": 2,
        "coordinate_0_action_offset": 0,
        "coordinate_0_stochastic_support": [0, 1],
        "coordinate_1_decrement": 1,
        "terminal_coordinate": 1,
        "iid_initial_seed_root": "102ac11d03b4d5de78c894b7ea8bc35f62142c782f27ed2ff366d4b384cba886",
    },
    {
        "schema": "acfqp.opaque_ranked_machine_manifest.v183",
        "manifest_index": 1,
        "reveal_salt": "07d33cc4e1271a703d065e6003e81a41dc353497a8c8e2f95b1cdd89e2182bca",
        "state_width": 2,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "coordinate_0_multiplier": 2,
        "coordinate_0_action_offset": 0,
        "coordinate_0_stochastic_support": [0, 1],
        "coordinate_1_decrement": 1,
        "terminal_coordinate": 1,
        "iid_initial_seed_root": "2bd930132b9a2104db06ff157c859234d6e4584e06df4dc3a9141a4cd2720cd8",
    },
    {
        "schema": "acfqp.opaque_ranked_machine_manifest.v183",
        "manifest_index": 2,
        "reveal_salt": "2046d0636c90b9634c0f091f6be2886766978da7f784787ded1bc6cf5466cfda",
        "state_width": 3,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "coordinate_0_multiplier": 2,
        "coordinate_0_action_offset": 0,
        "coordinate_0_stochastic_support": [0, 1],
        "coordinate_1_decrement": 1,
        "terminal_coordinate": 1,
        "iid_initial_seed_root": "df499028cd46d14a0339f9318ad905ae1f0122be6521051ce811e74595830524",
    },
)

EXPECTED_REVEAL_ID = (
    "430092f87a091771630eb69e2dd1aad91ce8b653f59bffc803ed9ac718a0e736"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_178
EXPECTED_CANONICAL_SHA256 = (
    "c820ff10ca573f7917ed58e1cfca19e5621cd3949425a8aa13b1e88a29ffb1b9"
)


def build_open_world_ranked_machine_manifest_reveal_v183() -> dict[str, Any]:
    frozen = protocol.freeze_open_world_ranked_machine_protocol_v183()
    commitments = tuple(
        ranked_machine_manifest_commitment_v183(document)
        for document in MANIFEST_DOCUMENTS_V183
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V183:
        raise ValueError("V183 manifest preimages changed their commitments")
    payload = {
        "schema": "acfqp.open_world_ranked_machine_manifest_reveal.v183",
        "protocol_id": frozen.protocol_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V183),
        "manifest_count": len(MANIFEST_DOCUMENTS_V183),
        "preimages_revealed_after_protocol_commit": True,
        "source_or_target_oracle_query_count": 0,
        "source_or_target_outcomes_accessed": False,
        "scientific_success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v183(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V183_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldRankedMachineManifestRevealV183:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V183 reveal is not canonical")
        return document


def freeze_open_world_ranked_machine_manifest_reveal_v183() -> OpenWorldRankedMachineManifestRevealV183:
    document = build_open_world_ranked_machine_manifest_reveal_v183()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V183 manifest reveal changed")
    return OpenWorldRankedMachineManifestRevealV183(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V183",
    "build_open_world_ranked_machine_manifest_reveal_v183",
    "freeze_open_world_ranked_machine_manifest_reveal_v183",
)
