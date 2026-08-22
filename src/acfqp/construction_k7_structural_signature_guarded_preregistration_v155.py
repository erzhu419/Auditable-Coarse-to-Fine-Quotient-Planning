"""Outcome-free preregistration for the V155 guarded sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v155 as domains
from acfqp.generic_relation_fanout_routing_adapter_v154 import FAMILY, relation_fanout_routing_config_v154
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.structural_signature_query_guard_receipt_v155 import (
    EXPECTED_CANONICAL_BYTE_COUNT as GUARD_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as GUARD_RECEIPT_SHA256,
    GUARD_RECEIPT_ID,
)


IMPLEMENTATION_COMMITS = ("38078821fd25f6fb181741fd092c3e8d1f04aaa6",)
PREREGISTRATION_ID = "4799e536dab144b074b7f865144247cd20f1dcd17c0e8ccfa117f1168a58386f"
EXPECTED_CANONICAL_BYTE_COUNT = 5_142
EXPECTED_CANONICAL_SHA256 = "cce7d3df166005eabed9a8cdc1a2d546cee34200f2db84c7c40d31f42d70d2b0"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_611, 1_047_615))
TARGET_EPISODE_INDICES = (681, 682, 683, 684)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v155.py", 1_634, "81325d0c73c2b0f5db0ede5e96dc14cbd3409563d73fc21a177f76fa3d697730"),
    ("src/acfqp/structural_signature_query_guard_receipt_v155.py", 6_627, "62bc2c4b67a4144a4c0037796973b51acd103f3dd3560591f42d4bf28fcd9208"),
    ("src/acfqp/structural_signature_guarded_acquisition_operator_v155.py", 4_423, "130d34bb5de3e7ced2c2087f1f7305699d27c9e798426c6cd8465719577fdf28"),
    ("src/acfqp/structural_signature_guarded_campaign_core_v155.py", 10_829, "5dfc3b8c8a69440756db926e3c9c54646e71bb04364064cd4c48451289834a2b"),
    ("src/acfqp/domains/stochastic_relation_fanout_routing_v154.py", 6_392, "979d0b992e9d543ad814cff8f5b5b768194e1c82184f576ef99197cdfc378f93"),
    ("src/acfqp/generic_relation_fanout_routing_adapter_v154.py", 4_414, "ba0900cc6ee50cb904f73a966651e7b94b47d61f3b79c24b78af241c95350fa2"),
    ("src/acfqp/certified_memoized_planner_sequence_v154.py", 6_600, "60c6b6409bf604385c6fc3f90182841485bd1561b4e06766fda2858154db5cfb"),
    ("src/acfqp/relation_coverage_cross_structure_campaign_core_v154.py", 12_557, "2ffaef2be46de3b523de8ce9741b7e7ccf09365954e4d9b85becbf43990a9b86"),
    ("src/acfqp/anonymous_relational_factor_bank_acquisition_v148.py", 26_160, "3094d26ef86aa2fde1c4932cb8872a666e4cbdeec0c8c24a23a973a6e1b12a84"),
)


class ConstructionK7StructuralSignatureGuardedPreregistrationV155Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralSignatureGuardedPreregistrationV155Error(message)


def campaign_config_v155():
    config = relation_fanout_routing_config_v154()
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
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
        or guard.get("guard_frozen_before_v155_target_outcomes") is not True
    ):
        _fail("V155 frozen guard receipt changed")
    source_facts = [
        {"relative_path": path, "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()), "sha256": hashlib.sha256(raw).hexdigest()}
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]:
        _fail("V155 frozen implementation source changed")
    config = campaign_config_v155()
    payload = {
        "schema": "acfqp.structural_signature_guarded_preregistration.v155",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_guard_receipt": guard,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_guarded_target_identities": True,
            "guard_receipt_frozen_before_target_outcomes": True,
            "failed_signature_must_select_exact_path_first_fallback": True,
            "zero_guard_sample_regression_required_everywhere": True,
            "factor_prior_noninferior_everywhere_and_positive_in_aggregate": True,
            "inherited_v153_verified_reduction_must_remain_positive": True,
            "v115_memoized_plan_receipt_consumption_required_both_arms": True,
            "both_arms_receding_planning_and_certificate_recovery_required": True,
            "nonrelational_ood_rejection_before_bank_access_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "guard_prevented_v154_sample_regression_observed": False,
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
    return {**payload, "preregistration_id": domains.extension_content_id_v155(domains.CONSTRUCTION_K7_PREREGISTRATION_V155_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralSignatureGuardedPreregistrationV155:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_structural_signature_guarded_preregistration_v155(guard_receipt_raw: bytes):
    document = _document(guard_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and (
        document["preregistration_id"] != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V155 frozen preregistration changed")
    return StructuralSignatureGuardedPreregistrationV155(_ISSUER, raw, document["preregistration_id"])


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v155",
    "freeze_structural_signature_guarded_preregistration_v155",
)
