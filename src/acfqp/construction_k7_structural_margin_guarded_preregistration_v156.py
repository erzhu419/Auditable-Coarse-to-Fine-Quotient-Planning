"""Outcome-free preregistration for the V156 mixed-family margin campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v156 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.structural_margin_guarded_campaign_core_v156 import FALLBACK_FAMILY, POSITIVE_FAMILY, structural_margin_campaign_config_v156
from acfqp.structural_margin_query_guard_receipt_v156 import (
    EXPECTED_CANONICAL_BYTE_COUNT as GUARD_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as GUARD_RECEIPT_SHA256,
    GUARD_RECEIPT_ID,
)


IMPLEMENTATION_COMMITS = (
    "8f63b29ff21a6fe94f6d2a29c2ba2d56146539ac",
    "826b3b4da4091b1b02937f6e5618b1e781173620",
)
PREREGISTRATION_ID = "7f67166d1fc555840bb20c3f5ee5e892213ebc096088a2b365edd74475567bbd"
EXPECTED_CANONICAL_BYTE_COUNT = 5_733
EXPECTED_CANONICAL_SHA256 = "8601a0ae0f198bcf95c10d43bc9876f7a71c1d0d08b8737ddac50536bab5f6f3"
TARGET_OCCURRENCES = tuple(
    [(POSITIVE_FAMILY, seed) for seed in range(1_047_711, 1_047_715)]
    + [(FALLBACK_FAMILY, seed) for seed in range(1_047_721, 1_047_725)]
)
TARGET_EPISODE_INDICES = (701, 702, 703, 704)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v156.py", 1_603, "dfd9db365b7fc2fb50c7be1b509122c58e788727bc218a319eafa430fd47b781"),
    ("src/acfqp/structural_margin_query_guard_receipt_v156.py", 6_823, "e24d6cc84f55bca4f35301e58cf0b6b6d79f0b2dd57e92c0267edcfd23220cca"),
    ("src/acfqp/structural_margin_guarded_acquisition_operator_v156.py", 4_788, "da7fc3ad2b96cb83d06aa83d909d66d594f16f2df0397d5f63523e71fa1e5e98"),
    ("src/acfqp/structural_margin_guarded_campaign_core_v156.py", 13_039, "fbce837bb5487e6308f906df19867507d67bc57ad993c2bd3e592550ed593b41"),
    ("src/acfqp/relation_coverage_acquisition_operator_v153.py", 6_417, "b6c8c5faaccc25653d49c9126c11e1844ae0c3c6bee508ce188a5b7d61ca5e8d"),
    ("src/acfqp/generic_quaternary_relation_workflow_adapter_v153.py", 3_669, "8c0dcdf7a5aff8af5d00992d8e304bcefeb3759d26bdb2e69bd855fe383c8d84"),
    ("src/acfqp/generic_relation_fanout_routing_adapter_v154.py", 4_414, "ba0900cc6ee50cb904f73a966651e7b94b47d61f3b79c24b78af241c95350fa2"),
    ("src/acfqp/certified_memoized_planner_sequence_v154.py", 6_600, "60c6b6409bf604385c6fc3f90182841485bd1561b4e06766fda2858154db5cfb"),
    ("src/acfqp/relation_coverage_cross_structure_campaign_core_v154.py", 12_557, "2ffaef2be46de3b523de8ce9741b7e7ccf09365954e4d9b85becbf43990a9b86"),
    ("src/acfqp/anonymous_relational_factor_bank_acquisition_v148.py", 26_160, "3094d26ef86aa2fde1c4932cb8872a666e4cbdeec0c8c24a23a973a6e1b12a84"),
)


class ConstructionK7StructuralMarginGuardedPreregistrationV156Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralMarginGuardedPreregistrationV156Error(message)


def campaign_config_v156():
    config = structural_margin_campaign_config_v156()
    for family, _seed in TARGET_OCCURRENCES:
        config["families"][family]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(guard_receipt_raw: bytes):
    guard = loads_canonical_json(guard_receipt_raw)
    if (
        canonical_json_bytes(guard) != guard_receipt_raw
        or len(guard_receipt_raw) != GUARD_RECEIPT_BYTE_COUNT
        or hashlib.sha256(guard_receipt_raw).hexdigest() != GUARD_RECEIPT_SHA256
        or guard.get("guard_receipt_id") != GUARD_RECEIPT_ID
        or guard.get("guard_frozen_before_v156_target_outcomes") is not True
    ):
        _fail("V156 frozen guard receipt changed")
    source_facts = [
        {"relative_path": path, "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()), "sha256": hashlib.sha256(raw).hexdigest()}
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]:
        _fail("V156 frozen implementation source changed")
    config = campaign_config_v156()
    payload = {
        "schema": "acfqp.structural_margin_guarded_preregistration.v156",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_guard_receipt": guard,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_mixed_family_target_identities": True,
            "guard_receipt_frozen_before_target_outcomes": True,
            "exact_signature_registry_must_remain_absent": True,
            "both_margin_sides_must_be_observed": True,
            "positive_margin_relation_coverage_must_be_positive_in_aggregate": True,
            "fallback_margin_must_have_zero_guard_regression_everywhere": True,
            "factor_prior_noninferior_everywhere_and_positive_in_aggregate": True,
            "v115_memoized_plan_receipt_consumption_required_both_arms": True,
            "both_arms_receding_planning_and_certificate_recovery_required": True,
            "nonrelational_ood_rejection_before_bank_access_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "structural_margin_guard_cross_family_nonregression_and_gain_observed": False,
            "guard_is_model_planning_or_certificate_authority": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v156(domains.CONSTRUCTION_K7_PREREGISTRATION_V156_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralMarginGuardedPreregistrationV156:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_structural_margin_guarded_preregistration_v156(guard_receipt_raw: bytes):
    document = _document(guard_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and (
        document["preregistration_id"] != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V156 frozen preregistration changed")
    return StructuralMarginGuardedPreregistrationV156(_ISSUER, raw, document["preregistration_id"])


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v156",
    "freeze_structural_margin_guarded_preregistration_v156",
)
