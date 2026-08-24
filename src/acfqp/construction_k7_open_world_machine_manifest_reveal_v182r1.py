"""Manifest preimages revealed only after the V182 commitments were frozen."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v182r1 as domains
from acfqp import construction_k7_open_world_machine_protocol_v182 as protocol
from acfqp.open_world_machine_oracle_v182 import machine_manifest_commitment_v182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V182R1 = (
    {
        "schema": "acfqp.opaque_machine_manifest.v182",
        "manifest_index": 0,
        "reveal_salt": "606d1ec278b235e0e8ef20f8b01ea7a1ec33fc164d3e289ee50600c763475e9e",
        "state_width": 3,
        "action_width": 1,
        "action_cardinality": 2,
        "horizon": 6,
        "initial_moduli": [6, 3, 3],
        "register_count": 2,
        "maximum_execution_steps": 32,
        "coordinate_programs": [
            [[1, 0, 0], [11, 0, 2, 2], [0, 0]],
            [[1, 0, 3], [3, 0], [0, 0]],
            [[0, 0]],
        ],
        "residual_supports": [[0], [0], [0, 1]],
        "terminal_program": [[1, 0, 0], [4, 0, 0], [0, 0]],
        "iid_initial_seed_root": "54035c84e50ddcde24d46dee981bad21f8f88269f9fffaba1aa4f44837a9f976",
    },
    {
        "schema": "acfqp.opaque_machine_manifest.v182",
        "manifest_index": 1,
        "reveal_salt": "d7ca67a65f7d997e133d23c1f969709e8b0363e3755900d983b94bd66304a967",
        "state_width": 3,
        "action_width": 1,
        "action_cardinality": 2,
        "horizon": 7,
        "initial_moduli": [7, 4, 4],
        "register_count": 2,
        "maximum_execution_steps": 32,
        "coordinate_programs": [
            [[1, 0, 0], [11, 0, 2, 2], [0, 0]],
            [[1, 0, 3], [3, 0], [0, 0]],
            [[0, 0]],
        ],
        "residual_supports": [[0], [0], [0, 1, 2]],
        "terminal_program": [[1, 0, 0], [4, 0, 0], [0, 0]],
        "iid_initial_seed_root": "6e33dd64677b17293e61a5023bffd4401c08039d0f42ec3ef94ab7e4eb4cbfbc",
    },
    {
        "schema": "acfqp.opaque_machine_manifest.v182",
        "manifest_index": 2,
        "reveal_salt": "d5ff0d7b4ab3cdf6695502d75075344b281b6e8e293a4ccc99d3f65c5bb7836b",
        "state_width": 4,
        "action_width": 1,
        "action_cardinality": 2,
        "horizon": 8,
        "initial_moduli": [4, 3, 8, 3],
        "register_count": 2,
        "maximum_execution_steps": 32,
        "coordinate_programs": [
            [[1, 0, 0], [3, 0], [0, 0]],
            [[0, 0]],
            [[1, 0, 2], [11, 0, 2, 2], [0, 0]],
            [[1, 0, 4], [3, 0], [0, 0]],
        ],
        "residual_supports": [[0], [0, 1], [0], [0]],
        "terminal_program": [[1, 0, 2], [4, 0, 0], [0, 0]],
        "iid_initial_seed_root": "a01ab19dfc4e5f15b42463e9b493d64880e6638835c8a3d54939e185c82889ca",
    },
)

EXPECTED_REVEAL_ID = (
    "d7d7c90e8fc51d9e265b9b77e49ce4592ce0e07ccb9e327389f77bbe944242bc"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_367
EXPECTED_CANONICAL_SHA256 = (
    "027402490bffe14e44c0f2cf8c5d3d8f049e3a27beadb38d3929295ed3303340"
)


def build_open_world_machine_manifest_reveal_v182r1() -> dict[str, Any]:
    frozen = protocol.freeze_open_world_machine_protocol_v182()
    commitments = tuple(
        machine_manifest_commitment_v182(document)
        for document in MANIFEST_DOCUMENTS_V182R1
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V182:
        raise ValueError("V182r1 manifest preimages changed their prior commitments")
    payload = {
        "schema": "acfqp.open_world_machine_manifest_reveal.v182r1",
        "protocol_id": frozen.protocol_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V182R1),
        "manifest_count": len(MANIFEST_DOCUMENTS_V182R1),
        "preimages_revealed_after_protocol_commit": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v182r1(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V182R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldMachineManifestRevealV182R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V182r1 reveal is not one canonical object")
        return document


def freeze_open_world_machine_manifest_reveal_v182r1() -> OpenWorldMachineManifestRevealV182R1:
    document = build_open_world_machine_manifest_reveal_v182r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V182r1 manifest reveal changed")
    return OpenWorldMachineManifestRevealV182R1(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V182R1",
    "freeze_open_world_machine_manifest_reveal_v182r1",
)
