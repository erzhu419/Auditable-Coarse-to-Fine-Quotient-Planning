"""Reveal the six V184 manifest preimages after the protocol commit."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v184 as domains
from acfqp import construction_k7_open_world_fair_expression_protocol_v184 as protocol
from acfqp.open_world_fair_expression_oracle_v184 import (
    fair_expression_manifest_commitment_v184,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_DOCUMENTS_V184 = (
    {
        "schema": "acfqp.opaque_fair_expression_manifest.v184",
        "manifest_index": 0,
        "role": "FRESH_OFFLINE_SOURCE",
        "reveal_salt": "67f24bae8b9d71f0c91eaa42bbddb282f2500a3a8b7ead02ea58419bfaa7c863",
        "state_width": 3,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "noise_support": [0, 1],
        "noise_seed_root": "caa03b0deafa6890a64767891b5af55b6c7a38445bb90830bacdde6ece5b7d50",
        "initial_seed_root": "4bc133cf24b4fdde78881244fad7f177ff6e891815969503006b48562ed01647",
        "ood_extra_coordinate_rule": None,
    },
    {
        "schema": "acfqp.opaque_fair_expression_manifest.v184",
        "manifest_index": 1,
        "role": "FRESH_MATCHED_TARGET_1",
        "reveal_salt": "ecce12c8152357af60c93edc489d18b7c9f53880c207c5a2fa045c02ffba8b3c",
        "state_width": 3,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "noise_support": [0, 1],
        "noise_seed_root": "5fb2e0785efe863af1b95a3f0b696d10a786b9ec21c1ac7b09f43ec6bb90ff82",
        "initial_seed_root": "8d90484fdae77dd68515f5b8d2f9c9def69eb6a5c4a7b44e00e67dd3c56d0b3d",
        "ood_extra_coordinate_rule": None,
    },
    {
        "schema": "acfqp.opaque_fair_expression_manifest.v184",
        "manifest_index": 2,
        "role": "FRESH_MATCHED_TARGET_2",
        "reveal_salt": "17f1c184cc374db0c0937d59104e30872d29d96abda62a4f31e53890f7df0c72",
        "state_width": 3,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "noise_support": [0, 1],
        "noise_seed_root": "20f95a3d63db6b1241912e862b3717be90ef68c1141e87433ff2420bbe4d3ba9",
        "initial_seed_root": "c88de2bdc11cf788ee10b2e55552c21c812f6b145ce5f5e92f990826c211db02",
        "ood_extra_coordinate_rule": None,
    },
    {
        "schema": "acfqp.opaque_fair_expression_manifest.v184",
        "manifest_index": 3,
        "role": "FRESH_MATCHED_TARGET_3",
        "reveal_salt": "d1c76143fc924fe2adab19d3a1c47058a566768043db52f9d68ea46fc2fc25ab",
        "state_width": 3,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "noise_support": [0, 1],
        "noise_seed_root": "cfc213bd0881c627d4a01277d195a6ced3f2e2bb4dd5c5b804a45c737c7a20c2",
        "initial_seed_root": "22536b8984239fe8edf084b90a97fcb41a39be79d9ad2e75d4da959209a87557",
        "ood_extra_coordinate_rule": None,
    },
    {
        "schema": "acfqp.opaque_fair_expression_manifest.v184",
        "manifest_index": 4,
        "role": "FRESH_MATCHED_TARGET_4",
        "reveal_salt": "7f1a74805d2efacafc1959e3a0040eaa10bf5e0097079ba21add19e3e0d85213",
        "state_width": 3,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "noise_support": [0, 1],
        "noise_seed_root": "6077dc4b63111814b6b548814121a4974c3f2200c27bebb6c588f9c5130c1e47",
        "initial_seed_root": "24e62c960fd8c4ac621e1a3524bda8dd417cff8fc7855bd8ba7e92c7b882918b",
        "ood_extra_coordinate_rule": None,
    },
    {
        "schema": "acfqp.opaque_fair_expression_manifest.v184",
        "manifest_index": 5,
        "role": "FRESH_INCOMPATIBLE_SCHEMA_OOD",
        "reveal_salt": "4490e2a4e92210a417d3d2635ea98ca10c06c21c1e947c55035d19e0cb3bbf14",
        "state_width": 4,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "noise_support": [0, 1],
        "noise_seed_root": "ecd3d8fef5e19a8eb0e5a60aea501488a2c818bfd12d99a1aa530e6d4e2c79cf",
        "initial_seed_root": "cd00856866517ffde728255a2ca7e8ab9c9a75e062b0ad97dccf7032f5ec4719",
        "ood_extra_coordinate_rule": "INCREMENT_MOD_11",
    },
)

EXPECTED_REVEAL_ID = "60801a98651f0ac6ece52afcae9506a8896ea23905fe0470acf7d0840764e815"
EXPECTED_CANONICAL_BYTE_COUNT = 3_914
EXPECTED_CANONICAL_SHA256 = "04ed92f2177b0092639b8463e58006ace6afeb33ec8b027cb49105a0febfd6e2"


def build_open_world_fair_expression_manifest_reveal_v184() -> dict[str, Any]:
    frozen = protocol.freeze_open_world_fair_expression_protocol_v184()
    commitments = tuple(
        fair_expression_manifest_commitment_v184(document)
        for document in MANIFEST_DOCUMENTS_V184
    )
    if commitments != protocol.MANIFEST_COMMITMENTS_V184:
        raise ValueError("V184 manifest preimages changed their commitments")
    payload = {
        "schema": "acfqp.open_world_fair_expression_manifest_reveal.v184",
        "protocol_id": frozen.protocol_id,
        "manifest_commitments": list(commitments),
        "manifest_documents": list(MANIFEST_DOCUMENTS_V184),
        "manifest_count": len(MANIFEST_DOCUMENTS_V184),
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
        "manifest_reveal_id": domains.extension_content_id_v184(
            domains.CONSTRUCTION_K7_MANIFEST_REVEAL_V184_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldFairExpressionManifestRevealV184:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    manifest_reveal_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V184 manifest reveal is not canonical")
        return document


def freeze_open_world_fair_expression_manifest_reveal_v184() -> OpenWorldFairExpressionManifestRevealV184:
    document = build_open_world_fair_expression_manifest_reveal_v184()
    raw = canonical_json_bytes(document)
    if EXPECTED_REVEAL_ID != "0" * 64 and not (
        document["manifest_reveal_id"] == EXPECTED_REVEAL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V184 manifest reveal changed")
    return OpenWorldFairExpressionManifestRevealV184(
        _ISSUER,
        raw,
        document["manifest_reveal_id"],
    )


__all__ = (
    "EXPECTED_REVEAL_ID",
    "MANIFEST_DOCUMENTS_V184",
    "build_open_world_fair_expression_manifest_reveal_v184",
    "freeze_open_world_fair_expression_manifest_reveal_v184",
)
