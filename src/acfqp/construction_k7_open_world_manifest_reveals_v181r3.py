"""Retained fresh V181r3 manifest preimages after protocol commitment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r3 as domains
from acfqp import construction_k7_open_world_protocol_successor_v181r3 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V181R3 = (
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 0,
        "reveal_salt": "6a9cab1bc2adb1063f5ba8c893ca289f6d02917a7802c4858ae989144a3e6dfa",
        "state_width": 5,
        "action_width": 2,
        "horizon": 6,
        "moduli": [7, 5, 4, 8, 5],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["A", 0]], 7],
            ["MOD", ["ADD", ["S", 1], ["K", 2]], 5],
            ["MOD", ["ADD", ["S", 2], ["A", 1]], 4],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 5],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1]],
        "iid_initial_seed_root": "0b7088e2d8e3d5287887f6f0f10182a5c12bf0fee2870c02f302d07b39d7118c",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 1,
        "reveal_salt": "479985b45ff8c0270a25e67543f336b8b002d04a9685abb88ba4737afad8658f",
        "state_width": 6,
        "action_width": 2,
        "horizon": 7,
        "moduli": [8, 6, 5, 9, 4, 3],
        "transition_programs": [
            ["MOD", ["ADD", ["ADD", ["S", 0], ["A", 1]], ["K", 1]], 8],
            ["MIN", ["K", 5], ["ADD", ["S", 1], ["A", 0]]],
            ["MOD", ["ADD", ["S", 2], ["A", 0]], 5],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 4],
            ["MOD", ["ADD", ["S", 5], ["K", 1]], 3],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 1]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [2]],
        "iid_initial_seed_root": "4d033c2d23fef5cabc43cd5c7182baeaf51eb3f5561f0299a6d44563a0114acb",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 2,
        "reveal_salt": "e0f4e7834e414a8cd65869f39b87b538e16a4283ceefe88588665c25214ccb7b",
        "state_width": 7,
        "action_width": 3,
        "horizon": 8,
        "moduli": [9, 7, 5, 10, 3, 8, 4],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["XOR", ["A", 0], ["A", 2]]], 9],
            ["MOD", ["ADD", ["S", 1], ["A", 1]], 7],
            ["MOD", ["ADD", ["S", 2], ["A", 0]], 5],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 3],
            ["MOD", ["ADD", ["S", 5], ["K", 1]], 8],
            ["MIN", ["K", 3], ["ADD", ["S", 6], ["A", 2]]],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 1], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1], [2]],
        "iid_initial_seed_root": "03e47d0ea2d8fe8fc4b518f07306a45b1bd4a66cb1d273df229087a0b013f863",
    },
)
EXPECTED_REVEAL_ID = (
    "d97d850de80aa5d578649f3492fa70e78eceb70e6455cd6a324b90313c940ea9"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_681
EXPECTED_CANONICAL_SHA256 = (
    "b4c24af5bb624b1db2ff26d01f2085ad7f0f58aec3dbec0b2a074925baeebbcc"
)


def build_open_world_manifest_reveals_v181r3() -> dict[str, Any]:
    successor = protocol.freeze_open_world_protocol_successor_v181r3()
    commitments = tuple(
        manifest_commitment_v181(document) for document in MANIFEST_DOCUMENTS_V181R3
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V181R3:
        raise ValueError("V181r3 manifest reveal does not match prior commitments")
    payload = {
        "schema": "acfqp.open_world_manifest_reveal.v181r3",
        "protocol_successor_id": successor.protocol_successor_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V181R3),
        "manifest_count": len(MANIFEST_DOCUMENTS_V181R3),
        "preimages_revealed_after_commitment_freeze": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v181r3(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V181R3_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldManifestRevealsV181R3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_manifest_reveals_v181r3() -> OpenWorldManifestRevealsV181R3:
    document = build_open_world_manifest_reveals_v181r3()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r3 manifest reveal changed")
    return OpenWorldManifestRevealsV181R3(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V181R3",
    "freeze_open_world_manifest_reveals_v181r3",
)
