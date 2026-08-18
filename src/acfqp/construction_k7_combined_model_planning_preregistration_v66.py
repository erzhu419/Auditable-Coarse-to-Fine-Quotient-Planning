"""Outcome-free preregistration for fresh V66 combined-model planning."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v66 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as previous
from acfqp.combined_model_planning_campaign_core_v66 import (
    build_combined_model_planning_campaign_document_v66,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "d5c8b95"
PREREGISTRATION_ID = "93602221454dd824a4c8b139a935427b22bc21bd04f56fe6992a977d37a8952e"
EXPECTED_CANONICAL_BYTE_COUNT = 4_987
EXPECTED_CANONICAL_SHA256 = "7cb230cb949848be1f1110bdafe600467e58a4d54d48c000e29e0becf3fc0ddf"
V62_LIBRARY_ID = "26e5e031eb6b57e73253bc85bc3d0c372f6444248ad0c4e3343a01f43353b3d0"
V65_CAMPAIGN_ID = "0754c5575634d075a005d809589dc00198ad4b66be5afcee73c15b3317f9eeda"
V65_VERIFICATION_ID = "7c33dd9829f58682936f4798e0a6186870c03fcff198765511136dc1739ebea4"
BALANCED_TARGET_SEEDS = tuple(range(671_101, 671_105))
COUPLED_TARGET_SEEDS = tuple(range(672_101, 672_105))
MAINTENANCE_TARGET_SEEDS = tuple(range(673_101, 673_105))
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 12
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v66.py",
    "src/acfqp/combined_model_planning_campaign_core_v66.py",
    "src/acfqp/generic_combined_model_certificate_planner_v23.py",
    "src/acfqp/generic_partial_residual_abstract_planner_v22.py",
    "src/acfqp/generic_adaptive_residual_factor_acquisition_v19.py",
    "src/acfqp/generic_total_adaptive_residual_acquisition_v20.py",
)


class ConstructionK7CombinedModelPlanningPreregistrationV66Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CombinedModelPlanningPreregistrationV66Error(message)


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


def campaign_config_v66() -> dict[str, Any]:
    config = previous.campaign_config_v59()
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
        maximum_combined_support_branch_evaluations=100_000,
        combined_support_feasible_beam_width=32,
        offline_library_labels=204,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.combined_model_planning_preregistration.v66",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v65_campaign_id": V65_CAMPAIGN_ID,
            "v65_campaign_sha256": "629bf0560654d23fb566a8c4d8555cb508d23ddcd09dc98f5f300755c47c8764",
            "v65_verification_id": V65_VERIFICATION_ID,
            "v65_verification_sha256": "f62da9828100c75e2e0271459272029d0f90355b98cd587582a9a394031d1bf7",
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v66_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V66),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_combined_model_planning_campaign_document_v66
            ),
            "frozen_before_any_registered_v66_outcome": True,
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
            and min(all_seeds) > 670_000,
        },
        "registered_gate": {
            "required_relation": "PRIOR_COMBINED_PLAN_SUCCESSES_GT_ZERO_AND_GE_STRICT",
            "certificate_local_label_reduction_required": False,
            "family_specific_combined_plan_success_required": False,
            "all_occurrences_and_family_projections_retained": True,
        },
        "combined_model_contract": {
            "same_partial_candidate_and_observations_between_arms": True,
            "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
            "partial_and_one_action_conditioned_zero_excess_residual_compiled": True,
            "and_or_search_attempted_before_support_feasible_receding_fallback": True,
            "robust_search_resource_truncation_retained": True,
            "combined_model_may_only_propose_abstract_first_action": True,
            "action_trajectories_required_to_match": False,
        },
        "safety_contract": {
            "every_unseen_ground_query_requires_prior_failed_certificate": True,
            "query_local_exact_overlay_exclusively_discharges_safety": True,
            "combined_abstract_plan_safety_authority": False,
            "unrepresented_residual_targets_assumed_known": False,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_combined_support_branch_evaluations": 100_000,
            "combined_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_and_common_partial_labels_separate": True,
            "prior_and_strict_certificate_local_labels_separate": True,
            "execution_steps_separate": True,
            "partial_planning_compute_separate": True,
            "combined_abstract_support_compute_separate": True,
            "residual_synthesis_attempts_separate": True,
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
        "preregistration_id": domains.extension_content_id_v66(
            domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_PREREGISTRATION_V66_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CombinedModelPlanningPreregistrationV66:
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
            or domains.extension_content_id_v66(
                domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_PREREGISTRATION_V66_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V66 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CombinedModelPlanningPreregistrationV66 | None = None


def freeze_combined_model_planning_preregistration_v66() -> CombinedModelPlanningPreregistrationV66:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V66 preregistration changed")
    if _CACHE is None:
        _CACHE = CombinedModelPlanningPreregistrationV66(_ISSUER, raw, identity)
    return _CACHE


def verify_combined_model_planning_preregistration_v66(
    value: Any,
) -> CombinedModelPlanningPreregistrationV66:
    if type(value) is not CombinedModelPlanningPreregistrationV66:
        _fail("V66 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_combined_model_planning_preregistration_v66()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V66 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V62_LIBRARY_ID",
    "V65_CAMPAIGN_ID",
    "V65_VERIFICATION_ID",
    "campaign_config_v66",
    "freeze_combined_model_planning_preregistration_v66",
    "verify_combined_model_planning_preregistration_v66",
)
