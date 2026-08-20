"""Outcome-free preregistration for fresh V68 relational world models."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v68 as domains
from acfqp import construction_k7_multi_residual_planning_preregistration_v67 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relational_world_model_campaign_core_v68 import (
    build_relational_world_model_campaign_document_v68,
)


IMPLEMENTATION_COMMIT = "3cb6ae8"
PREREGISTRATION_ID = "5469acca7510f403a62c67d97f80bc764463741c6eee224e056649ab4f33095e"
EXPECTED_CANONICAL_BYTE_COUNT = 5_409
EXPECTED_CANONICAL_SHA256 = "b3b06c7c21c5fa5d572df96b6942069561e329e61157cacf769da5e767f6eade"
V62_LIBRARY_ID = previous.V62_LIBRARY_ID
V67_CAMPAIGN_ID = "4726d258497299bba1dbaf37339ed5f497e3af7e1e114c602d5b4efe9614708b"
V67_VERIFICATION_ID = "c7a219fcb73856215082022d1128efbed70aec50678c224533ba48944ebabb19"
BALANCED_TARGET_SEEDS = (691_101, 691_102)
COUPLED_TARGET_SEEDS = (692_101, 692_102)
MAINTENANCE_TARGET_SEEDS = (693_101, 693_102)
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v68.py",
    "src/acfqp/relational_world_model_campaign_core_v68.py",
    "src/acfqp/generic_relational_world_model_certificate_planner_v30.py",
    "src/acfqp/generic_relational_residual_abstract_planner_v29.py",
    "src/acfqp/generic_relational_terminal_program_v28.py",
    "src/acfqp/generic_batch_exact_multi_residual_compiler_v27.py",
    "src/acfqp/generic_multi_residual_acquisition_v24.py",
    "src/acfqp/generic_total_adaptive_residual_acquisition_v20.py",
    "src/acfqp/generic_adaptive_residual_factor_acquisition_v19.py",
)


class ConstructionK7RelationalWorldModelPreregistrationV68Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationalWorldModelPreregistrationV68Error(message)


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


def campaign_config_v68() -> dict[str, Any]:
    config = previous.campaign_config_v67()
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
        maximum_terminal_program_candidates_to_try=32,
        maximum_relational_support_branch_evaluations=1_000_000,
        relational_support_feasible_beam_width=32,
        offline_library_labels=204,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.relational_world_model_preregistration.v68",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v67_campaign_id": V67_CAMPAIGN_ID,
            "v67_verification_id": V67_VERIFICATION_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v68_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V68),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_relational_world_model_campaign_document_v68
            ),
            "frozen_before_any_registered_v68_outcome": True,
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
            and min(all_seeds) > 690_000,
        },
        "registered_gate": {
            "required_relation": (
                "PRIOR_PLAN_GT_ZERO_AND_ACTIVE_GT_ZERO_AND_REJECTION_GT_ZERO"
            ),
            "prior_vs_strict_improvement_required": False,
            "certificate_local_label_reduction_required": False,
            "all_occurrences_and_family_projections_retained": True,
        },
        "world_model_contract": {
            "same_partial_candidate_and_observations_between_arms": True,
            "only_switched_variable": (
                "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH"
            ),
            "batch_exact_residual_support_derived_from_complete_observed_batches": True,
            "anonymous_terminal_coordinate_and_relation_tree_derived_from_raw_rows": True,
            "transition_and_terminal_programs_jointly_selected_for_planning": True,
            "multiple_terminal_candidates_may_be_rejected_before_composition": True,
            "abstract_model_may_only_propose_action_order": True,
        },
        "safety_contract": {
            "every_unseen_ground_query_requires_prior_failed_certificate": True,
            "query_local_exact_overlay_exclusively_discharges_safety": True,
            "relational_abstract_plan_safety_authority": False,
            "empirical_support_promoted_to_global_exact_dynamics": False,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_relational_support_branch_evaluations": 1_000_000,
            "relational_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_and_common_partial_labels_separate": True,
            "prior_and_strict_certificate_local_labels_separate": True,
            "execution_steps_separate": True,
            "partial_planning_compute_separate": True,
            "relational_abstract_support_compute_separate": True,
            "relational_synthesis_attempts_separate": True,
            "terminal_candidate_attempts_separate": True,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "producer_free_verification_present": False,
            "complete_world_model_synthesized": False,
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
        "preregistration_id": domains.extension_content_id_v68(
            domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_PREREGISTRATION_V68_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationalWorldModelPreregistrationV68:
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
            or domains.extension_content_id_v68(
                domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_PREREGISTRATION_V68_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V68 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: RelationalWorldModelPreregistrationV68 | None = None


def freeze_relational_world_model_preregistration_v68() -> RelationalWorldModelPreregistrationV68:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V68 preregistration changed")
    if _CACHE is None:
        _CACHE = RelationalWorldModelPreregistrationV68(_ISSUER, raw, identity)
    return _CACHE


def verify_relational_world_model_preregistration_v68(
    value: Any,
) -> RelationalWorldModelPreregistrationV68:
    if type(value) is not RelationalWorldModelPreregistrationV68:
        _fail("V68 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_relational_world_model_preregistration_v68()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V68 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V62_LIBRARY_ID",
    "V67_CAMPAIGN_ID",
    "V67_VERIFICATION_ID",
    "campaign_config_v68",
    "freeze_relational_world_model_preregistration_v68",
    "verify_relational_world_model_preregistration_v68",
)
