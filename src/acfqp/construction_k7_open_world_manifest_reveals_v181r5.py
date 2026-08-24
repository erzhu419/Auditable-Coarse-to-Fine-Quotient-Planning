"""Retained fresh V181r5 manifest preimages after protocol commitment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r5 as domains
from acfqp import construction_k7_open_world_protocol_successor_v181r5 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V181R5 = (
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 0,
        "reveal_salt": "3877f1386e0a512b238308b0dc9a475b941305b08d975e9fedf2a0d722d249c2",
        "state_width": 5,
        "action_width": 2,
        "horizon": 8,
        "moduli": [7, 6, 5, 9, 4],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["A", 0]], 7],
            ["MOD", ["ADD", ["S", 1], ["K", 2]], 6],
            ["MOD", ["ADD", ["S", 2], ["XOR", ["A", 0], ["A", 1]]], 5],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 4],
        ],
        "terminal_program": ["EQ", ["S", 3], ["K", 0]],
        "support": [[0], [1]],
        "iid_initial_seed_root": "37dda781612de3784cd34e806afc8831e11ba789d32c7016d0bc6217dcd9ac34",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 1,
        "reveal_salt": "05b52ed41456a6b5fb276df3199a52a2a69b7e4a193cb75bcca57cbe7367d3e8",
        "state_width": 6,
        "action_width": 2,
        "horizon": 9,
        "moduli": [8, 7, 6, 10, 5, 4],
        "transition_programs": [
            ["MOD", ["ADD", ["ADD", ["S", 0], ["A", 1]], ["K", 1]], 8],
            ["MIN", ["K", 6], ["ADD", ["S", 1], ["A", 0]]],
            ["MOD", ["ADD", ["S", 2], ["A", 0]], 6],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 5],
            ["MOD", ["ADD", ["S", 5], ["K", 1]], 4],
        ],
        "terminal_program": ["EQ", ["S", 3], ["K", 0]],
        "support": [[0], [2]],
        "iid_initial_seed_root": "0d1dc0057050ea2b28bcbc7b905e562b506e744516717a0f5f1d5433c673f570",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 2,
        "reveal_salt": "4e37f742cf948fad02e4e305b52fe5d47fdcae5804e79e8fcb03a10248c9f71c",
        "state_width": 7,
        "action_width": 3,
        "horizon": 10,
        "moduli": [9, 8, 7, 11, 4, 6, 5],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["XOR", ["A", 0], ["A", 2]]], 9],
            ["MOD", ["ADD", ["S", 1], ["A", 1]], 8],
            ["MOD", ["ADD", ["S", 2], ["A", 0]], 7],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 4],
            ["MOD", ["ADD", ["S", 5], ["K", 1]], 6],
            ["MIN", ["K", 4], ["ADD", ["S", 6], ["A", 2]]],
        ],
        "terminal_program": ["EQ", ["S", 3], ["K", 0]],
        "support": [[0], [1], [2]],
        "iid_initial_seed_root": "5e15a6eb80aecc2c2caba7efa1b0728a19dce827cd344be685a52ec6bfe37450",
    },
)
EXPECTED_REVEAL_ID = (
    "d4b60ab311f96f4e11e3ceb0457165e3a683a4dc5a7ad904e185bb7259802961"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_606
EXPECTED_CANONICAL_SHA256 = (
    "56d8a758216fb79ab8a8a2aa870c41a2ab7be853542e1e871ca3535f7148913e"
)


def build_open_world_manifest_reveals_v181r5() -> dict[str, Any]:
    successor = protocol.freeze_open_world_protocol_successor_v181r5()
    commitments = tuple(
        manifest_commitment_v181(document) for document in MANIFEST_DOCUMENTS_V181R5
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V181R5:
        raise ValueError("V181r5 manifest reveal does not match prior commitments")
    payload = {
        "schema": "acfqp.open_world_manifest_reveal.v181r5",
        "protocol_successor_id": successor.protocol_successor_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V181R5),
        "manifest_count": len(MANIFEST_DOCUMENTS_V181R5),
        "preimages_revealed_after_commitment_freeze": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v181r5(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V181R5_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldManifestRevealsV181R5:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_manifest_reveals_v181r5() -> OpenWorldManifestRevealsV181R5:
    document = build_open_world_manifest_reveals_v181r5()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r5 manifest reveal changed")
    return OpenWorldManifestRevealsV181R5(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V181R5",
    "freeze_open_world_manifest_reveals_v181r5",
)
