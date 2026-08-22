"""Outcome-free preregistration for the V153 sample-tax operator campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v153 as domains
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import FAMILY, quaternary_relation_workflow_config_v153
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_operator_receipt_v153 import EXPECTED_CANONICAL_BYTE_COUNT as RECEIPT_BYTE_COUNT, EXPECTED_CANONICAL_SHA256 as RECEIPT_SHA256, OPERATOR_RECEIPT_ID


IMPLEMENTATION_COMMITS = ("0f8e405717957063493ec5b6834b79a30f8f41f3", "e40f5bd1aefb7b247b5ccaf0860afcaecf82eccd")
PREREGISTRATION_ID = "c8f9ea990c7408f386780e17798127dae6f1c901b9e0343442942bde53a2f230"
EXPECTED_CANONICAL_BYTE_COUNT = 4_852
EXPECTED_CANONICAL_SHA256 = "12997f69cfdf3b662ca10d3ae0d389ed307db475816d44fe0748d065728978be"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_411, 1_047_415))
TARGET_EPISODE_INDICES = (641, 642, 643, 644)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v153.py", 1_568, "2db12871293889e8fb87461ee0cf46e2d55c753ae4f214a584d9d0a90aff42e4"),
    ("src/acfqp/domains/stochastic_quaternary_relation_workflow_v153.py", 2_807, "a7028665665ca4e14e122406ddd688d30889e637113474c304136b71f949017b"),
    ("src/acfqp/generic_quaternary_relation_workflow_adapter_v153.py", 3_669, "8c0dcdf7a5aff8af5d00992d8e304bcefeb3759d26bdb2e69bd855fe383c8d84"),
    ("src/acfqp/relation_coverage_acquisition_operator_v153.py", 6_417, "b6c8c5faaccc25653d49c9126c11e1844ae0c3c6bee508ce188a5b7d61ca5e8d"),
    ("src/acfqp/relation_coverage_operator_receipt_v153.py", 6_265, "710d6fd959bdb1a3c26c3135af359a1b679fccb0ff06778aad77c4cfcfc68239"),
    ("src/acfqp/relation_coverage_planning_campaign_core_v153.py", 8_356, "ba501a49030cef38310dbc64f6cd57270c78e196c0db5a17978bff49e43873eb"),
    ("src/acfqp/certified_planner_abstention_sequence_v150.py", 3_595, "51b83c5e91b47761211487b74ae2d901527a07519c6796cccbd961c7b7d4a01b"),
    ("src/acfqp/cross_domain_relational_factor_bank_campaign_core_v149.py", 15_468, "6759f91c3508857dafb00ee6a2b565f4a7f93d05c1790b2e0ffc1bf49875a9a4"),
)


class ConstructionK7RelationCoveragePreregistrationV153Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationCoveragePreregistrationV153Error(message)


def campaign_config_v153():
    config = quaternary_relation_workflow_config_v153()
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(operator_receipt_raw: bytes):
    receipt = loads_canonical_json(operator_receipt_raw)
    if canonical_json_bytes(receipt) != operator_receipt_raw or len(operator_receipt_raw) != RECEIPT_BYTE_COUNT or hashlib.sha256(operator_receipt_raw).hexdigest() != RECEIPT_SHA256 or receipt.get("operator_receipt_id") != OPERATOR_RECEIPT_ID or receipt.get("operator", {}).get("future_target_outcomes_accessed") is not False:
        _fail("V153 frozen operator receipt changed")
    source_facts = [
        {"relative_path": path, "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()), "sha256": hashlib.sha256(raw).hexdigest()}
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != [{"relative_path": path, "byte_count": count, "sha256": digest} for path, count, digest in FROZEN_SOURCE_FACTS]:
        _fail("V153 frozen implementation source changed")
    config = campaign_config_v153()
    payload = {
        "schema": "acfqp.relation_coverage_preregistration.v153",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_operator_receipt": receipt,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_quaternary_relation_target_identities": True,
            "operator_receipt_frozen_before_target_outcomes": True,
            "adaptive_prior_vs_adaptive_strict_uses_same_query_policy_synthesizer_and_stop_rule": True,
            "legacy_path_first_prior_baseline_required": True,
            "operator_positive_reduction_vs_legacy_prior_everywhere": True,
            "factor_prior_positive_within_same_operator_everywhere": True,
            "four_key_relation_observation_derived_and_selected": True,
            "both_adaptive_arms_receding_planning_and_certificate_recovery_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "sample_tax_reduction_observed": False,
            "operator_is_model_planning_or_certificate_authority": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v153(domains.CONSTRUCTION_K7_PREREGISTRATION_V153_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationCoveragePreregistrationV153:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_relation_coverage_preregistration_v153(operator_receipt_raw: bytes):
    document = _document(operator_receipt_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (identity != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("V153 frozen preregistration changed")
    return RelationCoveragePreregistrationV153(_ISSUER, raw, identity)


__all__ = ("PREREGISTRATION_ID", "campaign_config_v153", "freeze_relation_coverage_preregistration_v153")
