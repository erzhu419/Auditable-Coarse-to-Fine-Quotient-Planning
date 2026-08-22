"""Outcome-free preregistration for V154 cross-structure operator reuse."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v154 as domains
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    FAMILY,
    relation_fanout_routing_config_v154,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_cross_structure_application_receipt_v154 import (
    APPLICATION_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as APPLICATION_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as APPLICATION_RECEIPT_SHA256,
)


IMPLEMENTATION_COMMITS = (
    "bd374195fe555d954c66c05ad98ab65de6edd33f",
    "6db535c0411b265ff7c64481907bb009446aec64",
)
PREREGISTRATION_ID = "2458a1600cd5eb7f9935e4284cad22d55542d13c840ebcc4265bf45597d7a141"
EXPECTED_CANONICAL_BYTE_COUNT = 4_930
EXPECTED_CANONICAL_SHA256 = "c69f43eb60789af44b7811fc2b598093acf136902850138024a510271f0861a3"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_511, 1_047_515))
TARGET_EPISODE_INDICES = (661, 662, 663, 664)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v154.py", 1_734, "4cec28b5f7dc8be086bb9f8eb36f349b180ff90c3de489c7a85ba0f46f5498bf"),
    ("src/acfqp/domains/stochastic_relation_fanout_routing_v154.py", 6_392, "979d0b992e9d543ad814cff8f5b5b768194e1c82184f576ef99197cdfc378f93"),
    ("src/acfqp/generic_relation_fanout_routing_adapter_v154.py", 4_414, "ba0900cc6ee50cb904f73a966651e7b94b47d61f3b79c24b78af241c95350fa2"),
    ("src/acfqp/certified_memoized_planner_sequence_v154.py", 6_600, "60c6b6409bf604385c6fc3f90182841485bd1561b4e06766fda2858154db5cfb"),
    ("src/acfqp/relation_coverage_cross_structure_application_receipt_v154.py", 6_309, "1f235896f968287d830079f82dbb3dbcbfd022dd147532c1b592d01ff377ec41"),
    ("src/acfqp/relation_coverage_cross_structure_campaign_core_v154.py", 12_557, "2ffaef2be46de3b523de8ce9741b7e7ccf09365954e4d9b85becbf43990a9b86"),
    ("src/acfqp/relation_coverage_acquisition_operator_v153.py", 6_417, "b6c8c5faaccc25653d49c9126c11e1844ae0c3c6bee508ce188a5b7d61ca5e8d"),
    ("src/acfqp/certified_planner_abstention_sequence_v150.py", 3_595, "51b83c5e91b47761211487b74ae2d901527a07519c6796cccbd961c7b7d4a01b"),
)


class ConstructionK7RelationCoverageCrossStructurePreregistrationV154Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationCoverageCrossStructurePreregistrationV154Error(message)


def campaign_config_v154():
    config = relation_fanout_routing_config_v154()
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(application_receipt_raw: bytes):
    application = loads_canonical_json(application_receipt_raw)
    if (
        canonical_json_bytes(application) != application_receipt_raw
        or len(application_receipt_raw) != APPLICATION_RECEIPT_BYTE_COUNT
        or hashlib.sha256(application_receipt_raw).hexdigest() != APPLICATION_RECEIPT_SHA256
        or application.get("application_receipt_id") != APPLICATION_RECEIPT_ID
        or application.get("registered_application", {}).get("fresh_target_outcomes_accessed") is not False
    ):
        _fail("V154 frozen application receipt changed")
    source_facts = [
        {
            "relative_path": path,
            "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]:
        _fail("V154 frozen implementation source changed")
    config = campaign_config_v154()
    payload = {
        "schema": "acfqp.relation_coverage_cross_structure_preregistration.v154",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_application_receipt": application,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_cross_structure_target_identities": True,
            "application_receipt_frozen_before_target_outcomes": True,
            "same_exact_v153_operator_required": True,
            "matched_legacy_path_first_prior_baseline_required": True,
            "operator_noninferior_per_occurrence_and_positive_in_aggregate": True,
            "factor_prior_noninferior_per_occurrence_and_positive_in_aggregate": True,
            "v115_memoized_plan_receipt_consumption_required_both_arms": True,
            "both_arms_receding_planning_and_certificate_recovery_required": True,
            "nonrelational_ood_rejection_before_bank_access_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "cross_structure_operator_reuse_observed": False,
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
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v154(
            domains.CONSTRUCTION_K7_PREREGISTRATION_V154_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationCoverageCrossStructurePreregistrationV154:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_relation_coverage_cross_structure_preregistration_v154(
    application_receipt_raw: bytes,
):
    document = _document(application_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and (
        document["preregistration_id"] != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V154 frozen preregistration changed")
    return RelationCoverageCrossStructurePreregistrationV154(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v154",
    "freeze_relation_coverage_cross_structure_preregistration_v154",
)
