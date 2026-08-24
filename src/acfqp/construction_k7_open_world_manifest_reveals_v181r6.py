"""Retained fresh V181r6 manifest preimages after protocol commitment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r6 as domains
from acfqp import construction_k7_open_world_protocol_successor_v181r6 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V181R6 = (
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 0,
        "reveal_salt": "e72c280674818ac8c0fd03774023f096223f4d60dffbccff44911c81036505b7",
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
        "iid_initial_seed_root": "9e1d31d6adf120c475d41e7b8cef04498307a98610ec51c1ce9d7ea64c865b69",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 1,
        "reveal_salt": "34385305e76b3d8660ac84c0880ccbb0f5e63f733525c2c23d0c8639929461e1",
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
        "iid_initial_seed_root": "2f68ea2c866180c87debcb5ffd923971621f66c0ac584c8ee7d764de0763a222",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 2,
        "reveal_salt": "6649909a1c5ced57b045e06cce64c9df0760548080d7d74f2c8eac91a455e782",
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
        "iid_initial_seed_root": "b3d75eb9283d7b8926584d16bcfe9cc9cf2abf09c98b53c4fdbb12c1bbb51188",
    },
)
EXPECTED_REVEAL_ID = (
    "4a1673ab4439a5d20c5c6942958016d53bb34187fd2306066a1a469ef09571e8"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_606
EXPECTED_CANONICAL_SHA256 = (
    "acda0891b559ff7a52457f24ed18dcf8437e738656ddb994581ed50bffc53760"
)


def build_open_world_manifest_reveals_v181r6() -> dict[str, Any]:
    successor = protocol.freeze_open_world_protocol_successor_v181r6()
    commitments = tuple(
        manifest_commitment_v181(document) for document in MANIFEST_DOCUMENTS_V181R6
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V181R6:
        raise ValueError("V181r6 manifest reveal does not match prior commitments")
    payload = {
        "schema": "acfqp.open_world_manifest_reveal.v181r6",
        "protocol_successor_id": successor.protocol_successor_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V181R6),
        "manifest_count": len(MANIFEST_DOCUMENTS_V181R6),
        "preimages_revealed_after_commitment_freeze": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v181r6(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V181R6_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldManifestRevealsV181R6:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_manifest_reveals_v181r6() -> OpenWorldManifestRevealsV181R6:
    document = build_open_world_manifest_reveals_v181r6()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r6 manifest reveal changed")
    return OpenWorldManifestRevealsV181R6(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V181R6",
    "freeze_open_world_manifest_reveals_v181r6",
)
