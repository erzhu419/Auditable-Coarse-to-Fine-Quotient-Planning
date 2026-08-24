"""Fresh V181r1 manifest reveals, added only after successor preregistration."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181r1 as domains
from acfqp import construction_k7_open_world_protocol_successor_v181r1 as successor
from acfqp.open_world_transition_oracle_v181 import manifest_commitment_v181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V181R1 = (
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 0,
        "reveal_salt": "41abea61761399fd7f17bed2158db78e237a58deb92b20e3137c9fc26cb1c2e3",
        "state_width": 5,
        "action_width": 2,
        "horizon": 5,
        "moduli": [5, 4, 2, 7, 3],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["A", 0]], 5],
            ["MOD", ["ADD", ["S", 1], ["K", 1]], 4],
            ["XOR", ["S", 2], ["MOD", ["A", 1], 2]],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 3],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1]],
        "iid_initial_seed_root": "181r1-001",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 1,
        "reveal_salt": "981ee63b5c151390a96f9e8d331fc4152411a6ee44f5ed500128e2d6a76c8fc3",
        "state_width": 5,
        "action_width": 2,
        "horizon": 6,
        "moduli": [7, 6, 3, 8, 5],
        "transition_programs": [
            ["MOD", ["ADD", ["ADD", ["S", 0], ["A", 1]], ["K", 1]], 7],
            ["MIN", ["K", 5], ["ADD", ["S", 1], ["A", 0]]],
            ["MOD", ["ADD", ["S", 2], ["A", 0]], 3],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 5],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 1]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [2]],
        "iid_initial_seed_root": "181r1-101",
    },
    {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 2,
        "reveal_salt": "df021777f854b808e69a7dee33a14e33fb3a329644b89d3710c577f359255fa5",
        "state_width": 6,
        "action_width": 3,
        "horizon": 7,
        "moduli": [8, 5, 4, 9, 3, 6],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["XOR", ["A", 0], ["A", 2]]], 8],
            ["MOD", ["ADD", ["S", 1], ["A", 1]], 5],
            [
                "SELECT",
                ["LT", ["S", 2], ["K", 2]],
                ["ADD", ["S", 2], ["K", 1]],
                ["SUB", ["S", 2], ["K", 1]],
            ],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
            ["MOD", ["ADD", ["S", 4], ["W", 0]], 3],
            ["MOD", ["ADD", ["S", 5], ["K", 1]], 6],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1], [2]],
        "iid_initial_seed_root": "181r1-201",
    },
)
EXPECTED_REVEAL_ID = (
    "3eb4c0f11238c2f41c2dc1b21c42c6504505cbe06acb465bc5619b96e0f64469"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_388
EXPECTED_CANONICAL_SHA256 = (
    "1e258078fcc09efdfd9c472f6d6f1433fd59c1128149554052f93c2720f88fe1"
)


def build_open_world_manifest_reveals_v181r1() -> dict[str, Any]:
    commitments = tuple(manifest_commitment_v181(row) for row in MANIFEST_DOCUMENTS_V181R1)
    if commitments != successor.MANIFEST_COMMITMENTS_V181R1:
        raise ValueError("V181r1 retained reveal preimage changed")
    payload = {
        "schema": "acfqp.open_world_manifest_reveals.v181r1",
        "protocol_successor_id": successor.EXPECTED_SUCCESSOR_ID,
        "manifest_commitments": list(commitments),
        "manifest_documents": [dict(row) for row in MANIFEST_DOCUMENTS_V181R1],
        "all_reveal_preimages_match_preregistered_commitments": True,
        "target_oracle_query_count_at_reveal": 0,
        "target_outcomes_accessed_at_reveal": False,
    }
    return {
        **payload,
        "manifest_reveal_id": domains.extension_content_id_v181r1(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V181R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldManifestRevealsV181R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_manifest_reveals_v181r1() -> OpenWorldManifestRevealsV181R1:
    document = build_open_world_manifest_reveals_v181r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181r1 frozen manifest reveal changed")
    return OpenWorldManifestRevealsV181R1(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V181R1",
    "freeze_open_world_manifest_reveals_v181r1",
)
