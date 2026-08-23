"""Outcome-free preregistration for V173r1 cross-family branch coverage."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v173r1 as domains
from acfqp.cross_family_branch_complete_online_receipt_core_v173r1 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    cross_family_branch_complete_campaign_config_v173r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("6c717e6", "af443e2", "fab4d90")
TARGET_OCCURRENCES = (
    (PACKET_FAMILY, 1_099_851),
    (PACKET_FAMILY, 1_099_852),
    (RESERVOIR_FAMILY, 1_109_851),
    (RESERVOIR_FAMILY, 1_109_852),
)
TARGET_EPISODE_INDICES = (1_023, 1_024, 1_025, 1_026)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/online_typed_plan_receipt_sequence_v172.py",
        12_289,
        "34e52b2afd8db4a0f6ef654911aa4151fc2aace11c48841ef4cd3a64eacf3108",
    ),
    (
        "src/acfqp/online_typed_plan_receipt_campaign_core_v172.py",
        15_983,
        "4508937be410f283023751a4ac50e7d505d76eab3dd5efdc9b6983fddc8c3109",
    ),
    (
        "src/acfqp/branch_complete_online_receipt_campaign_core_v173.py",
        11_573,
        "4b713df082aeb010a41f17b5c4eed2ef32f6da110392eb4ef8adcd368fa873f1",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v173r1.py",
        1_572,
        "91d8aa3998a2d7ed97cbff1f85ec795e707fe5a3fffc69c958ac111aca5bd83a",
    ),
    (
        "src/acfqp/cross_family_branch_complete_online_receipt_core_v173r1.py",
        11_011,
        "753ac58d2083950597358d58c3a3ced5dbd6c73d99b8d0143091e0be565041bb",
    ),
)
FROZEN_PREDECESSORS = (
    (
        "v172r1_online_typed_plan_receipt_campaign.json",
        14_761_292,
        "2988188d53f74266839e107fb2e6a378cf3d2b8dfbe5f29fae3076b36556fb99",
        "campaign_id",
        "c904d48bd590a287c4a1085ffecf41920ddde5cbba7a958e3906232afdd4128b",
    ),
    (
        "v172r1_online_typed_plan_receipt_verification.json",
        1_716,
        "2285bd267a3e2f1270a67fa8bd3ccdd8f23a2d6b3ff2bb6009d89ae705f80869",
        "verification_id",
        "200a3eb5fd8109a2f8ac8f9cdf612e080edcc67c2b68af44c406380f5784ef3f",
    ),
    (
        "v173_branch_complete_online_receipt_failure.json",
        868,
        "51a17147979246fda296b52464a3363b7ef6c69e762855b5d9530d40c5f90318",
        "failure_id",
        "ce5ca1449b5956b9b60fd3b0cfa45ce2ea987822f34145cb63ec4e5a87a5626d",
    ),
)
PREREGISTRATION_ID = "fbfbfa167d59806e19270c41e951da03c3fe7677bf6c668de1a747d164804ba9"
EXPECTED_CANONICAL_BYTE_COUNT = 3_525
EXPECTED_CANONICAL_SHA256 = "3f0811eb6ab03c99e1f7ac6c27cd2f2bead80dd2691d709f957b29f2a15002c2"


class ConstructionK7CrossFamilyBranchCompletePreregistrationV173R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossFamilyBranchCompletePreregistrationV173R1Error(
        message
    )


def campaign_config_v173r1():
    config = cross_family_branch_complete_campaign_config_v173r1()
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=len(TARGET_OCCURRENCES),
    )
    return config


def _frozen(row):
    name, count, digest, identity_key, identity = row
    raw = (ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V173r1 frozen predecessor changed: {name}")
    return document


def build_cross_family_branch_complete_preregistration_v173r1():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V173r1 implementation changed before outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    predecessors = [_frozen(row) for row in FROZEN_PREDECESSORS]
    if not (
        predecessors[0]["registered_gate"]["passed"] is True
        and predecessors[1]["producer_free_online_issuance_reconstruction"] is True
        and predecessors[2]["same_preregistration_identity_may_be_rerun"] is False
    ):
        _fail("V173r1 predecessor boundary changed")
    config = campaign_config_v173r1()
    payload = {
        "schema": "acfqp.cross_family_branch_complete_preregistration.v173r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_predecessors": [
            {
                "name": row[0],
                "byte_count": row[1],
                "sha256": row[2],
                row[3]: row[4],
            }
            for row in FROZEN_PREDECESSORS
        ],
        "target_occurrences": [
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": len(TARGET_OCCURRENCES),
        "registered_branch_coverage_roles": {
            PACKET_FAMILY: "DIRECT_BRANCH_COVERAGE",
            RESERVOIR_FAMILY: "MEMOIZED_BRANCH_COVERAGE",
        },
        "registered_gate": {
            "fresh_cross_family_identities_fixed_before_outcomes": True,
            "failed_v173_identity_preserved_not_rerun": True,
            "direct_memoized_observation_dependency_sources_all_required": True,
            "every_plan_receipt_issued_before_return_required": True,
            "every_execution_joined_to_prior_receipt_required": True,
            "factor_prior_strict_label_reduction_each_occurrence_required": True,
            "query_policy_noninferiority_each_occurrence_required": True,
            "producer_free_reconstruction_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "branch_complete_online_receipt_taxonomy_observed": False,
            "factor_prior_sample_tax_reduction_observed": False,
            "receipt_taxonomy_is_model_or_safety_authority": False,
            "query_local_exact_overlay_remains_only_safety_authority": True,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v173r1(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V173R1_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossFamilyBranchCompletePreregistrationV173R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_cross_family_branch_complete_preregistration_v173r1():
    document = build_cross_family_branch_complete_preregistration_v173r1()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V173r1 frozen preregistration changed")
    return CrossFamilyBranchCompletePreregistrationV173R1(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v173r1",
    "freeze_cross_family_branch_complete_preregistration_v173r1",
)
