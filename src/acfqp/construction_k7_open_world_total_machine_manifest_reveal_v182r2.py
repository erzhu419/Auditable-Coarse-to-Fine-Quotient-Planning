"""Fresh manifest preimages revealed after the V182r2 protocol commit."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v182r2 as domains
from acfqp import construction_k7_open_world_total_machine_protocol_v182r2 as protocol
from acfqp.open_world_machine_oracle_v182 import machine_manifest_commitment_v182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V182R2 = (
    {
        "schema": "acfqp.opaque_machine_manifest.v182",
        "manifest_index": 0,
        "reveal_salt": "24bc5648d3f8da7eb04f30f63e88702094ba6c310380ffb99ba61dc18c368de3",
        "state_width": 3,
        "action_width": 1,
        "action_cardinality": 2,
        "horizon": 8,
        "initial_moduli": [8, 3, 3],
        "register_count": 2,
        "maximum_execution_steps": 32,
        "coordinate_programs": [
            [[1, 0, 0], [11, 0, 2, 2], [0, 0]],
            [[1, 0, 3], [3, 0], [0, 0]],
            [[0, 0]],
        ],
        "residual_supports": [[0], [0], [0, 1, 2]],
        "terminal_program": [[1, 0, 0], [4, 0, 0], [0, 0]],
        "iid_initial_seed_root": "8dcb62cf8c3b0adcde17caf898325b9fc8380398f7e125e0ffa7cb17f66de1b1",
    },
    {
        "schema": "acfqp.opaque_machine_manifest.v182",
        "manifest_index": 1,
        "reveal_salt": "67d14143a3339368c53da4baedad14b216bf29421a85d7fdb83c253774028fc0",
        "state_width": 3,
        "action_width": 1,
        "action_cardinality": 2,
        "horizon": 9,
        "initial_moduli": [9, 4, 3],
        "register_count": 2,
        "maximum_execution_steps": 32,
        "coordinate_programs": [
            [[1, 0, 0], [11, 0, 2, 2], [0, 0]],
            [[1, 0, 3], [3, 0], [0, 0]],
            [[0, 0]],
        ],
        "residual_supports": [[0], [0], [0, 1, 2]],
        "terminal_program": [[1, 0, 0], [4, 0, 0], [0, 0]],
        "iid_initial_seed_root": "91b6b66a1729a956eac2c893136a7e83d655ecd13de5b68b8c0ce8b8911ebaec",
    },
    {
        "schema": "acfqp.opaque_machine_manifest.v182",
        "manifest_index": 2,
        "reveal_salt": "a2095f3f00dc08075d801eb3a20cff86041cd08477e2833e9dec95df18bd5d46",
        "state_width": 4,
        "action_width": 1,
        "action_cardinality": 3,
        "horizon": 7,
        "initial_moduli": [6, 3, 6, 4],
        "register_count": 2,
        "maximum_execution_steps": 32,
        "coordinate_programs": [
            [[1, 0, 0], [11, 0, 2, 2], [0, 0]],
            [[0, 0]],
            [[1, 0, 2], [11, 0, 2, 2], [0, 0]],
            [[1, 0, 4], [3, 0], [0, 0]],
        ],
        "residual_supports": [[0], [0, 1], [0], [0]],
        "terminal_program": [[1, 0, 2], [4, 0, 0], [0, 0]],
        "iid_initial_seed_root": "670652f51b455f934f3be996c3ed31e93037a8f3ccdd8a8f88072d9d4795682c",
    },
)

EXPECTED_REVEAL_ID = (
    "ba9ca87d11191ddc9daaa218d346059e5c7ebbc0c0f4b2b5bd933283f79b42e4"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_479
EXPECTED_CANONICAL_SHA256 = (
    "840cfc07d8a368dcab5efccf66262cd9196e384d20b952e9a55692e1bc2ec1c4"
)


def build_open_world_total_machine_manifest_reveal_v182r2() -> dict[str, Any]:
    frozen = protocol.freeze_open_world_total_machine_protocol_v182r2()
    commitments = tuple(
        machine_manifest_commitment_v182(document)
        for document in MANIFEST_DOCUMENTS_V182R2
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V182R2:
        raise ValueError("V182r2 manifest preimages changed their commitments")
    payload = {
        "schema": "acfqp.open_world_total_machine_manifest_reveal.v182r2",
        "protocol_id": frozen.protocol_id,
        "failed_predecessor_failure_id": (
            frozen.to_document()["failed_predecessor_failure_id"]
        ),
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V182R2),
        "manifest_count": len(MANIFEST_DOCUMENTS_V182R2),
        "preimages_revealed_after_protocol_commit": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v182r2(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V182R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldTotalMachineManifestRevealV182R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V182r2 reveal is not one canonical object")
        return document


def freeze_open_world_total_machine_manifest_reveal_v182r2() -> OpenWorldTotalMachineManifestRevealV182R2:
    document = build_open_world_total_machine_manifest_reveal_v182r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V182r2 manifest reveal changed")
    return OpenWorldTotalMachineManifestRevealV182R2(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V182R2",
    "build_open_world_total_machine_manifest_reveal_v182r2",
    "freeze_open_world_total_machine_manifest_reveal_v182r2",
)
