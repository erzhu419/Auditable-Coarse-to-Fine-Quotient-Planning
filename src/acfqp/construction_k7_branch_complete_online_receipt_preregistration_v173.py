"""Outcome-free V173 preregistration for all four online source branches."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v173 as domains
from acfqp.branch_complete_online_receipt_campaign_core_v173 import (
    PACKET_BATCHING_FAMILY,
    branch_complete_online_receipt_campaign_config_v173,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("ca12e93", "fab4d90")
TARGET_OCCURRENCES = (
    (PACKET_BATCHING_FAMILY, 1_089_851),
    (PACKET_BATCHING_FAMILY, 1_089_852),
)
TARGET_EPISODE_INDICES = (1_003, 1_004, 1_005, 1_006)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/domains/stochastic_packet_batching.py",
        9_735,
        "08097fe843771f188cafd593065a27c2553e2a7819bb5c567b7f9ebde6a7e979",
    ),
    (
        "src/acfqp/generic_packet_batching_adapter_v134.py",
        4_279,
        "10fba1e8f4aee4e86fe3de184cd455601b48f1cb115a7c5dd79c166770e2d817",
    ),
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
        "src/acfqp/construction_k7_domain_registry_extension_v173.py",
        1_565,
        "111acced7a900ca5f762ff45d32893c41f7e4ce5c3857e300a0a088bef556bc7",
    ),
    (
        "src/acfqp/branch_complete_online_receipt_campaign_core_v173.py",
        11_573,
        "4b713df082aeb010a41f17b5c4eed2ef32f6da110392eb4ef8adcd368fa873f1",
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
)
PREREGISTRATION_ID = "fa26bc0178eef945cf6d00e2f519c85b66f5b3d5c2b2c0cdf7e62c2c96fe477c"
EXPECTED_CANONICAL_BYTE_COUNT = 3_169
EXPECTED_CANONICAL_SHA256 = "f4f21dec9e74e30140cf3bbaade6a6a4b2613b34508f6ba168b63738de596abb"


class ConstructionK7BranchCompleteOnlineReceiptPreregistrationV173Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7BranchCompleteOnlineReceiptPreregistrationV173Error(
        message
    )


def campaign_config_v173():
    config = branch_complete_online_receipt_campaign_config_v173()
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
        _fail(f"V173 frozen predecessor changed: {name}")
    return document


def build_branch_complete_online_receipt_preregistration_v173():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V173 implementation changed before outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    predecessors = [_frozen(row) for row in FROZEN_PREDECESSORS]
    if not (
        predecessors[0]["registered_gate"]["passed"] is True
        and predecessors[1]["producer_free_online_issuance_reconstruction"] is True
        and predecessors[1]["producer_free_execution_join_reconstruction"] is True
    ):
        _fail("V173 predecessor boundary changed")
    config = campaign_config_v173()
    payload = {
        "schema": "acfqp.branch_complete_online_receipt_preregistration.v173",
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
        "maximum_acquisition_labels": config["families"][
            PACKET_BATCHING_FAMILY
        ]["maximum_acquisition_labels"],
        "registered_gate": {
            "fresh_packet_identities_fixed_before_outcomes": True,
            "direct_online_source_required": True,
            "memoized_online_source_required": True,
            "observation_online_source_required": True,
            "dependency_revalidated_online_source_required": True,
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
        "preregistration_id": domains.extension_content_id_v173(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V173_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class BranchCompleteOnlineReceiptPreregistrationV173:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_branch_complete_online_receipt_preregistration_v173():
    document = build_branch_complete_online_receipt_preregistration_v173()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V173 frozen preregistration changed")
    return BranchCompleteOnlineReceiptPreregistrationV173(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v173",
    "freeze_branch_complete_online_receipt_preregistration_v173",
)
