"""Retained fresh V181r4 manifest preimages after protocol commitment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r4 as domains
from acfqp import construction_k7_open_world_protocol_successor_v181r4 as protocol
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V181R4 = (
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 0,
        "reveal_salt": "33454ce684dedc48c02f4f916b68dcd911f680ca1a264ba7bcc46981c6598ba0",
        "state_width": 5,
        "action_width": 2,
        "horizon": 6,
        "moduli": [6, 5, 4, 8, 5],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["A", 0]], 6],
            ["MOD", ["ADD", ["S", 1], ["K", 2]], 5],
            ["MOD", ["ADD", ["S", 2], ["A", 1]], 4],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 5],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 1]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1]],
        "iid_initial_seed_root": "0d2a85c55519a525863aafd60edaa7881de8ac18f2ba9848a51008797ee5753a",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 1,
        "reveal_salt": "2a6500b4ebba30343a8517b4e284297ec55ef737d2a9ce29c6cec68ba9889eb6",
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
            ["EQ", ["S", 0], ["K", 2]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [2]],
        "iid_initial_seed_root": "c63cc2601f0e59a08209ceba62d9ab19ac9025d8ecfbc755aa5c52df3de18bcc",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 2,
        "reveal_salt": "a226f2e25b92abdc7c2fb398c2f5a0376b3427fbba3459660553b184876d680f",
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
            ["EQ", ["S", 1], ["K", 1]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1], [2]],
        "iid_initial_seed_root": "14b387ef302aca8670e7f1de7257e49ed25f82c36834958b62a69d7b598dc8e8",
    },
)
EXPECTED_REVEAL_ID = (
    "284179ab4e1b2c336526cc5eb6b91663fa2593122db8ccde4815851e2bb327fd"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_681
EXPECTED_CANONICAL_SHA256 = (
    "ce54a7f707a4d2cd974146ee67be8e7cc8b36f466df33d0003adba029ebe7f46"
)


def build_open_world_manifest_reveals_v181r4() -> dict[str, Any]:
    successor = protocol.freeze_open_world_protocol_successor_v181r4()
    commitments = tuple(
        manifest_commitment_v181(document) for document in MANIFEST_DOCUMENTS_V181R4
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V181R4:
        raise ValueError("V181r4 manifest reveal does not match prior commitments")
    payload = {
        "schema": "acfqp.open_world_manifest_reveal.v181r4",
        "protocol_successor_id": successor.protocol_successor_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V181R4),
        "manifest_count": len(MANIFEST_DOCUMENTS_V181R4),
        "preimages_revealed_after_commitment_freeze": True,
        "target_oracle_query_count": 0,
        "target_outcomes_accessed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v181r4(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V181R4_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldManifestRevealsV181R4:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_manifest_reveals_v181r4() -> OpenWorldManifestRevealsV181R4:
    document = build_open_world_manifest_reveals_v181r4()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r4 manifest reveal changed")
    return OpenWorldManifestRevealsV181R4(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V181R4",
    "freeze_open_world_manifest_reveals_v181r4",
)
