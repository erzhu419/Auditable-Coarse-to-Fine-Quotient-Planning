"""Outcome-free preregistration for dependency-derived branch retention V117."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v117 as domains
from acfqp import construction_k7_cross_epoch_program_branch_preregistration_v116 as previous
from acfqp.construction_k7_cross_epoch_program_branch_campaign_v116 import (
    CAMPAIGN_ID as V116_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V116_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_cross_epoch_program_branch_independent_verifier_v116 import (
    EXPECTED_CANONICAL_SHA256 as V116_VERIFICATION_SHA256,
    VERIFICATION_ID as V116_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("d35cf64", "1dbeaaf")
PREREGISTRATION_ID = "9aafb1d13daba2078511556de4f7f6b1f12f3519a93100e6c9ebc11d4b957240"
EXPECTED_CANONICAL_BYTE_COUNT = 23_128
EXPECTED_CANONICAL_SHA256 = "97a1380d0d194403350dcb372f686b89b1440c887ab43badca3d19a282558bfa"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_029_101),
    ("COUPLED_EXCHANGE", 1_029_201),
    ("MAINTENANCE_CASCADE", 1_029_301),
)
TARGET_EPISODE_INDICES = (254, 255, 256)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 3
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "COUPLED_EXCHANGE",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v117.py",
        1735,
        "fbd0d087dcc5d826aaf5a5972e80a3a9d9bee18ec8b1160411f6f2d13242b9fc",
    ),
    (
        "src/acfqp/generic_dependency_derived_program_branch_sequence_v117.py",
        11047,
        "06accda5124d9494ebf17ead2f75dad023a5ab113387d70e7b493de40445b100",
    ),
    (
        "src/acfqp/dependency_derived_program_branch_campaign_core_v117.py",
        13252,
        "8acc3b067e97af7412379299e23fc194a0561377c4c313c4ad12a9af87033978",
    ),
    (
        "src/acfqp/construction_k7_cross_epoch_program_branch_preregistration_v116.py",
        11390,
        "2c357cfa12ccd21b0eec55d5204e3ccf0b30fbe98d6c05dd096c05c61f58eb3f",
    ),
    (
        "src/acfqp/construction_k7_cross_epoch_program_branch_campaign_v116.py",
        4857,
        "9f63c8e90d4287d9f3601e78a56f01a0b84c22a77a82e73e3201f5ca0bb9c599",
    ),
    (
        "src/acfqp/construction_k7_cross_epoch_program_branch_independent_verifier_v116.py",
        21408,
        "8c1f907e715c328701981bec2be59d6596be28e38b03fbbf4b0eb03631b5af7c",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7DependencyDerivedProgramBranchPreregistrationV117Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DependencyDerivedProgramBranchPreregistrationV117Error(
        message
    )


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v117() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v116())
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        required_target_families=REQUIRED_TARGET_FAMILIES,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.dependency_derived_program_branch_preregistration.v117",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v116_campaign_id": V116_CAMPAIGN_ID,
            "v116_campaign_sha256": V116_CAMPAIGN_SHA256,
            "v116_verification_id": V116_VERIFICATION_ID,
            "v116_verification_sha256": V116_VERIFICATION_SHA256,
            "v116_registered_gate_passed": True,
            "v116_passed_occurrence_count": 3,
            "v116_target_labels": 147,
            "v116_planning_compute_events": 92_038,
            "v116_uncached_v113_planning_compute_events": 108_126,
            "v116_planning_compute_events_avoided": 16_088,
            "v116_identity_and_bytes_retained": True,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v117_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V117),
            "frozen_before_any_registered_v117_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v117()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "one_occurrence_per_family": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "v116_branch_cache_and_v113_planner_semantics_retained": True,
            "cache_retention_decision_derived_from_exact_compiled_operator_dependencies": True,
            "candidate_assignments_action_catalogue_projected_state_and_action_are_minimal_dependencies": True,
            "observation_graph_raw_row_identity_terminal_rule_and_model_epoch_are_excluded": True,
            "dependency_receipt_rederived_before_each_episode_orderer": True,
            "exact_dependency_equality_required_for_retention": True,
            "changed_dependency_negative_control_must_invalidate_without_outcome_execution": True,
            "every_action_certificate_overlay_model_execution_and_planning_compute_must_match_v116": True,
            "compiled_model_cache_and_receipt_only_order_actions": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "all_three_registered_structural_families_present": True,
            "every_occurrence_matches_v116_sequence_bytes_and_compute": True,
            "every_occurrence_rederives_exact_dependency": True,
            "every_changed_dependency_control_invalidates_without_outcome": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "matched_v116_compute_not_charged_to_dependency_derived_arm": True,
            "dependency_derivation_compute_reported_separately": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v117_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_dependency_derived_branch_retention_verified": False,
            "compiled_model_cache_or_receipt_used_as_safety_authority": False,
            "global_lumpability_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_PREREGISTRATION_V117_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class DependencyDerivedProgramBranchPreregistrationV117:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v117(
                domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_PREREGISTRATION_V117_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V117 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: DependencyDerivedProgramBranchPreregistrationV117 | None = None


def freeze_dependency_derived_program_branch_preregistration_v117() -> DependencyDerivedProgramBranchPreregistrationV117:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V117 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V117 frozen preregistration changed")
        _CACHE = DependencyDerivedProgramBranchPreregistrationV117(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_dependency_derived_program_branch_preregistration_v117(
    value: Any,
) -> DependencyDerivedProgramBranchPreregistrationV117:
    if type(value) is not DependencyDerivedProgramBranchPreregistrationV117:
        _fail("V117 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_dependency_derived_program_branch_preregistration_v117()
    if value is not expected:
        _fail("V117 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v117",
    "freeze_dependency_derived_program_branch_preregistration_v117",
    "verify_dependency_derived_program_branch_preregistration_v117",
)
