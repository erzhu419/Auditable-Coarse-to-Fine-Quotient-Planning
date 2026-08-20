"""Outcome-free preregistration for fresh V67 joint residual planning."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_combined_model_planning_preregistration_v66 as previous
from acfqp import construction_k7_domain_registry_extension_v67 as domains
from acfqp.multi_residual_planning_campaign_core_v67 import (
    build_multi_residual_planning_campaign_document_v67,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "1d99f5b"
PREREGISTRATION_ID = "49a2faf3b37abaaf3960678a12cc0450f91b6054ffc67206756e5307eb7bb239"
EXPECTED_CANONICAL_BYTE_COUNT = 5_044
EXPECTED_CANONICAL_SHA256 = "d8ed3a5e0a706529fbca28d7d0661cac6bf00fcc8f078db5c33409348c118ee1"
V62_LIBRARY_ID = previous.V62_LIBRARY_ID
V66_CAMPAIGN_ID = "b4c8e705ebe76b63c3a67831feedcff948a2b0e09ab928b9aaa03363f3d3a1a8"
V66_VERIFICATION_ID = "1b42294ccd1785763de545da0b7a159526fc4c23a212a956e341257d1149fc12"
BALANCED_TARGET_SEEDS = tuple(range(681_101, 681_105))
COUPLED_TARGET_SEEDS = tuple(range(682_101, 682_105))
MAINTENANCE_TARGET_SEEDS = tuple(range(683_101, 683_105))
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 12
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v67.py",
    "src/acfqp/multi_residual_planning_campaign_core_v67.py",
    "src/acfqp/generic_multi_residual_certificate_planner_v26.py",
    "src/acfqp/generic_multi_residual_abstract_planner_v25.py",
    "src/acfqp/generic_multi_residual_acquisition_v24.py",
    "src/acfqp/generic_total_adaptive_residual_acquisition_v20.py",
    "src/acfqp/generic_adaptive_residual_factor_acquisition_v19.py",
)


class ConstructionK7MultiResidualPlanningPreregistrationV67Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MultiResidualPlanningPreregistrationV67Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v67() -> dict[str, Any]:
    config = previous.campaign_config_v66()
    target_seeds = {
        "BALANCED_BATCH_REFINEMENT": BALANCED_TARGET_SEEDS,
        "COUPLED_EXCHANGE": COUPLED_TARGET_SEEDS,
        "MAINTENANCE_CASCADE": MAINTENANCE_TARGET_SEEDS,
    }
    for family, seeds in target_seeds.items():
        config["families"][family]["target_seeds"] = seeds
    config.update(
        target_seeds=target_seeds,
        target_occurrence_count=TARGET_OCCURRENCE_COUNT,
        worker_count=WORKER_COUNT,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
        residual_confidence_denominator=64,
        maximum_joint_support_branch_evaluations=1_000_000,
        joint_support_feasible_beam_width=16,
        offline_library_labels=204,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.multi_residual_planning_preregistration.v67",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v66_campaign_id": V66_CAMPAIGN_ID,
            "v66_verification_id": V66_VERIFICATION_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v67_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V67),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_multi_residual_planning_campaign_document_v67
            ),
            "frozen_before_any_registered_v67_outcome": True,
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "target_seeds": list(BALANCED_TARGET_SEEDS)
            },
            "COUPLED_EXCHANGE": {"target_seeds": list(COUPLED_TARGET_SEEDS)},
            "MAINTENANCE_CASCADE": {
                "target_seeds": list(MAINTENANCE_TARGET_SEEDS)
            },
            "target_occurrence_count": TARGET_OCCURRENCE_COUNT,
            "fresh_and_identity_disjoint": len(all_seeds) == len(set(all_seeds))
            and min(all_seeds) > 680_000,
        },
        "registered_gate": {
            "required_relation": "PRIOR_JOINT_GT_ZERO_AND_PRIOR_MULTI_OCCURRENCES_GT_ZERO",
            "prior_vs_strict_improvement_required": False,
            "certificate_local_label_reduction_required": False,
            "all_occurrences_and_family_projections_retained": True,
        },
        "joint_model_contract": {
            "same_partial_candidate_and_observations_between_arms": True,
            "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
            "one_physical_query_pool_shared_by_all_residual_targets": True,
            "at_least_two_compilable_proposals_required_before_joint_planning": True,
            "positive_excess_supports_retained_as_nondeterministic_branches": True,
            "and_or_search_precedes_support_feasible_receding_fallback": True,
            "joint_model_may_only_propose_abstract_first_action": True,
        },
        "safety_contract": {
            "every_unseen_ground_query_requires_prior_failed_certificate": True,
            "query_local_exact_overlay_exclusively_discharges_safety": True,
            "joint_abstract_plan_safety_authority": False,
            "unrepresented_residual_targets_assumed_known": False,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_joint_support_branch_evaluations": 1_000_000,
            "joint_support_feasible_beam_width": 16,
        },
        "accounting_contract": {
            "offline_and_common_partial_labels_separate": True,
            "prior_and_strict_certificate_local_labels_separate": True,
            "physical_labels_not_multiplied_by_residual_target_count": True,
            "execution_steps_separate": True,
            "partial_planning_compute_separate": True,
            "joint_abstract_support_compute_separate": True,
            "multi_residual_synthesis_attempts_separate": True,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "producer_free_verification_present": False,
            "complete_residual_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v67(
            domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_PREREGISTRATION_V67_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class MultiResidualPlanningPreregistrationV67:
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
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v67(
                domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_PREREGISTRATION_V67_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V67 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: MultiResidualPlanningPreregistrationV67 | None = None


def freeze_multi_residual_planning_preregistration_v67() -> MultiResidualPlanningPreregistrationV67:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V67 preregistration changed")
    if _CACHE is None:
        _CACHE = MultiResidualPlanningPreregistrationV67(_ISSUER, raw, identity)
    return _CACHE


def verify_multi_residual_planning_preregistration_v67(
    value: Any,
) -> MultiResidualPlanningPreregistrationV67:
    if type(value) is not MultiResidualPlanningPreregistrationV67:
        _fail("V67 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_multi_residual_planning_preregistration_v67()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V67 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V62_LIBRARY_ID",
    "V66_CAMPAIGN_ID",
    "V66_VERIFICATION_ID",
    "campaign_config_v67",
    "freeze_multi_residual_planning_preregistration_v67",
    "verify_multi_residual_planning_preregistration_v67",
)
