"""Retained fresh V181r2 manifest preimages after protocol commitment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r2 as domains
from acfqp import construction_k7_open_world_protocol_successor_v181r2 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V181R2 = (
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 0,
        "reveal_salt": "a022d7627c47c524a0fbfe8d7c29a92ab79387eb3ff0fa3871595df4b31a88f8",
        "state_width": 5,
        "action_width": 2,
        "horizon": 5,
        "moduli": [6, 5, 3, 7, 4],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["A", 0]], 6],
            ["MOD", ["ADD", ["S", 1], ["K", 2]], 5],
            ["MOD", ["ADD", ["S", 2], ["A", 1]], 3],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 4],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1]],
        "iid_initial_seed_root": "de0358e25a76cdb2ddf074a7beab606d425634d9375c1c7b809a7f9897d5de6f",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 1,
        "reveal_salt": "169e4ca2739b3df5e3ef3a45f1923c169ec1171175d50ed6be8fad43999fa013",
        "state_width": 6,
        "action_width": 2,
        "horizon": 6,
        "moduli": [7, 5, 4, 8, 5, 3],
        "transition_programs": [
            ["MOD", ["ADD", ["ADD", ["S", 0], ["A", 1]], ["K", 1]], 7],
            ["MIN", ["K", 4], ["ADD", ["S", 1], ["A", 0]]],
            ["MOD", ["ADD", ["S", 2], ["A", 0]], 4],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 5],
            ["MOD", ["ADD", ["S", 5], ["K", 1]], 3],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 1]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [2]],
        "iid_initial_seed_root": "6f83c9228a944433fe5fabc36051551fe339c323034d533502504f5a761c83f3",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 2,
        "reveal_salt": "cf9688cc9fa711737486e7de06fdf56e41d74ba0f90e1b7899c21419c6304b8b",
        "state_width": 6,
        "action_width": 3,
        "horizon": 7,
        "moduli": [8, 6, 5, 9, 3, 7],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["XOR", ["A", 0], ["A", 2]]], 8],
            ["MOD", ["ADD", ["S", 1], ["A", 1]], 6],
            [
                "SELECT",
                ["LT", ["S", 2], ["K", 2]],
                ["ADD", ["S", 2], ["K", 1]],
                ["MAX", ["K", 0], ["SUB", ["S", 2], ["K", 1]]],
            ],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 3],
            ["MOD", ["ADD", ["S", 5], ["K", 1]], 7],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1], [2]],
        "iid_initial_seed_root": "672da173fb45b270e055d0cc6e0b28efb9149a139301d2afa8d759989f5a43ff",
    },
)
EXPECTED_REVEAL_ID = (
    "980701792512bb61f8d706a4fe033beaf3d27253e16c75e7851e57aa8f24ea5f"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_702
EXPECTED_CANONICAL_SHA256 = (
    "797cbb9354ad101148f4f780613143387423f54ce2c93720af0ede5d405f9c20"
)


def build_open_world_manifest_reveals_v181r2() -> dict[str, Any]:
    successor = protocol.freeze_open_world_protocol_successor_v181r2()
    commitments = tuple(
        manifest_commitment_v181(document) for document in MANIFEST_DOCUMENTS_V181R2
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V181R2:
        raise ValueError("V181r2 manifest reveal does not match prior commitments")
    payload = {
        "schema": "acfqp.open_world_manifest_reveal.v181r2",
        "protocol_successor_id": successor.protocol_successor_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V181R2),
        "manifest_count": len(MANIFEST_DOCUMENTS_V181R2),
        "preimages_revealed_after_commitment_freeze": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v181r2(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V181R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldManifestRevealsV181R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_manifest_reveals_v181r2() -> OpenWorldManifestRevealsV181R2:
    document = build_open_world_manifest_reveals_v181r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r2 manifest reveal changed")
    return OpenWorldManifestRevealsV181R2(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V181R2",
    "freeze_open_world_manifest_reveals_v181r2",
)
