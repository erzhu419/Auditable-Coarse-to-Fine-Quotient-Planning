"""Reveal the six V185 manifest preimages after the protocol commit."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v185 as domains
from acfqp import construction_k7_open_world_composite_macro_protocol_v185 as protocol
from acfqp.open_world_composite_macro_oracle_v185 import (
    composite_macro_manifest_commitment_v185,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V185 = (
    {
        "schema": "acfqp.opaque_composite_macro_manifest.v185",
        "manifest_index": 0,
        "role": "FRESH_OFFLINE_SOURCE",
        "reveal_salt": "937bd50fa8ef80397064a530d381b427aa8c4c8ca10332b84b5b9c55754e414a",
        "state_width": 8,
        "action_width": 2,
        "legal_actions": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "horizon": 4,
        "state_permutation": [0, 1, 2, 3, 4, 5, 6, 7],
        "action_permutation": [0, 1],
        "noise_support": [0, 1],
        "noise_seed_root": "886f3210e3d6ecd1ba390c8a7b6069e7aea891596ffb5d74eb094aebfcff1c92",
        "initial_seed_root": "c5fe7dbf2018e350b0295680cde33868aea361fc7e8236ea1203f996380589ac",
        "ood_rule": None,
    },
    {
        "schema": "acfqp.opaque_composite_macro_manifest.v185",
        "manifest_index": 1,
        "role": "FRESH_MATCHED_TARGET_1",
        "reveal_salt": "e3871fca6589e7fd9fd3cdbcff630a81b72186aed95d5ea5837fefc823618179",
        "state_width": 8,
        "action_width": 2,
        "legal_actions": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "horizon": 4,
        "state_permutation": [3, 1, 5, 0, 7, 2, 6, 4],
        "action_permutation": [1, 0],
        "noise_support": [0, 1],
        "noise_seed_root": "642a361a77f7c3434877f1a17dc58b80ef959d917b043a50136e41e1b2b5a02d",
        "initial_seed_root": "47e7008141479532eef332a2fa8de5802c9dd50d756d57cec20578ca6726c5bb",
        "ood_rule": None,
    },
    {
        "schema": "acfqp.opaque_composite_macro_manifest.v185",
        "manifest_index": 2,
        "role": "FRESH_MATCHED_TARGET_2",
        "reveal_salt": "f96b20ca1e0c73fb59be03a1f2285a548fd9e4527cf7e96b22f78f9084eeae0e",
        "state_width": 8,
        "action_width": 2,
        "legal_actions": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "horizon": 4,
        "state_permutation": [6, 1, 0, 7, 3, 5, 2, 4],
        "action_permutation": [0, 1],
        "noise_support": [0, 1],
        "noise_seed_root": "1b8d874697df15d21efcaace3e92fda723948572248dff56ac53157b794b0e63",
        "initial_seed_root": "8c667d39dbb443bc005fb74a37d85a0c406dbb94a0deb8aae84b8d2e3c022338",
        "ood_rule": None,
    },
    {
        "schema": "acfqp.opaque_composite_macro_manifest.v185",
        "manifest_index": 3,
        "role": "FRESH_MATCHED_TARGET_3",
        "reveal_salt": "ded149bf5b5d010c23e04300789592d85081070c21090be543dfd80ffd6c26ae",
        "state_width": 8,
        "action_width": 2,
        "legal_actions": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "horizon": 4,
        "state_permutation": [2, 6, 4, 1, 0, 7, 5, 3],
        "action_permutation": [1, 0],
        "noise_support": [0, 1],
        "noise_seed_root": "01615b3376f30bfb402030a07483f0be95a3f024587f70d7c2f098cb1e52659f",
        "initial_seed_root": "2f7940d22d564ee68d16fa5516286ea713f9d9e6d5761b28a21a1a9cb4d5cadb",
        "ood_rule": None,
    },
    {
        "schema": "acfqp.opaque_composite_macro_manifest.v185",
        "manifest_index": 4,
        "role": "FRESH_MATCHED_TARGET_4",
        "reveal_salt": "05313e7aef73ead9f2b6dbd057fcd6314df5aed4f59d0866689f270e480f71db",
        "state_width": 8,
        "action_width": 2,
        "legal_actions": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "horizon": 4,
        "state_permutation": [7, 2, 5, 0, 4, 1, 3, 6],
        "action_permutation": [0, 1],
        "noise_support": [0, 1],
        "noise_seed_root": "8dd7b2025d344703d131bad3b80afd2346a1f76e2e5b06c13c0158a1c5c78b57",
        "initial_seed_root": "451abd96acdf27dfbe3e6a7c6ec087a3705fc6075cf196c3da4f27c4b221957d",
        "ood_rule": None,
    },
    {
        "schema": "acfqp.opaque_composite_macro_manifest.v185",
        "manifest_index": 5,
        "role": "FRESH_INCOMPATIBLE_SCHEMA_OOD",
        "reveal_salt": "eb42be2b27e2a5cedb348cd37e609a8ee459077f8f0ea86b18c46d6c951021f5",
        "state_width": 9,
        "action_width": 2,
        "legal_actions": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "horizon": 4,
        "state_permutation": [4, 7, 1, 5, 2, 0, 6, 3],
        "action_permutation": [1, 0],
        "noise_support": [0, 1],
        "noise_seed_root": "30dc2518354cf1637ee5c069a98e20ed9087410e86e66f2b8fa892412f3fdd8b",
        "initial_seed_root": "749ecc5c8c054773e35a9ba9c0bbc4faaa69a7f55599c3b3f208742c79a60419",
        "ood_rule": "OPAQUE_COUNTER_INCREMENT_MOD_13",
    },
)

EXPECTED_REVEAL_ID = "e10e9718496d1f9c4288bfdfce694172036c378971a4656c92b0224843b04f94"
EXPECTED_CANONICAL_BYTE_COUNT = 4_313
EXPECTED_CANONICAL_SHA256 = "a3335a9ce3747cdad1583f1d52f39bf1db2624f5b5320e52bb392ba13f89d155"


def build_open_world_composite_macro_manifest_reveal_v185() -> dict[str, Any]:
    frozen = protocol.freeze_open_world_composite_macro_protocol_v185()
    commitments = tuple(
        composite_macro_manifest_commitment_v185(document)
        for document in MANIFEST_DOCUMENTS_V185
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V185:
        raise ValueError("V185 manifest preimages changed their commitments")
    payload = {
        "schema": "acfqp.open_world_composite_macro_manifest_reveal.v185",
        "protocol_id": frozen.protocol_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V185),
        "manifest_count": len(MANIFEST_DOCUMENTS_V185),
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
        "manifest_reveal_id": domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V185_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCompositeMacroManifestRevealV185:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V185 manifest reveal is not canonical")
        return document


def freeze_open_world_composite_macro_manifest_reveal_v185() -> OpenWorldCompositeMacroManifestRevealV185:
    document = build_open_world_composite_macro_manifest_reveal_v185()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V185 manifest reveal changed")
    return OpenWorldCompositeMacroManifestRevealV185(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V185",
    "build_open_world_composite_macro_manifest_reveal_v185",
    "freeze_open_world_composite_macro_manifest_reveal_v185",
)
