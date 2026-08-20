"""Outcome-free preregistration for the fresh V71 factorial campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v71 as domains
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as previous
from acfqp.generic_role_free_acquisition_operator_v36 import (
    PRESERVED_V36_DEVELOPMENT_FAILURE,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.role_free_prequential_campaign_core_v71 import (
    build_role_free_prequential_campaign_document_v71,
)


IMPLEMENTATION_COMMIT = "beb0693"
PREREGISTRATION_ID = "2a006b95d9976d53693977400369636148a688185f9fa5df80403cde272da765"
EXPECTED_CANONICAL_BYTE_COUNT = 5_897
EXPECTED_CANONICAL_SHA256 = "6377751152500cca2375dbcbfc11d9b22fedcdc01346ce81b4a01125dc28d3da"
V62_LIBRARY_ID = previous.V62_LIBRARY_ID
V70_CAMPAIGN_ID = "dafe32e5ec1eec433bef6e8044722aea7474399d8bc78a10c5edd70713175548"
V70_VERIFICATION_ID = "b55346fd542c47380f5581d065b3a50b1da786f8bb0f42f611dafa05fa897fd7"
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
BALANCED_TARGET_SEEDS = (721_101, 721_102)
COUPLED_TARGET_SEEDS = (722_101, 722_102)
MAINTENANCE_TARGET_SEEDS = (723_101, 723_102)
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v71.py",
    "src/acfqp/role_free_prequential_campaign_core_v71.py",
    "src/acfqp/generic_role_free_acquisition_operator_v36.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_adaptive_role_free_terminal_acquisition_v35.py",
    "src/acfqp/generic_role_free_relational_template_v33.py",
    "src/acfqp/generic_relational_terminal_program_independent_replay_v32.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
)


class ConstructionK7RoleFreePrequentialPreregistrationV71Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RoleFreePrequentialPreregistrationV71Error(message)


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


def campaign_config_v71() -> dict[str, Any]:
    config = previous.campaign_config_v70()
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
        prequential_confidence_denominator=64,
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
        "schema": "acfqp.role_free_prequential_preregistration.v71",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v70_campaign_id": V70_CAMPAIGN_ID,
            "v70_verification_id": V70_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "preserved_development_failure": dict(PRESERVED_V36_DEVELOPMENT_FAILURE),
        "source_closure": {
            "source_facts": _source_facts(),
            "v71_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V71),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_role_free_prequential_campaign_document_v71
            ),
            "frozen_before_any_registered_v71_target_outcome": True,
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
            and min(all_seeds) > 720_000,
        },
        "factorial_acquisition_contract": {
            "arms": [
                "JOINT_SCHEDULE_AND_PROGRAM_PRIOR",
                "SCHEDULE_PRIOR_ONLY",
                "PROGRAM_PRIOR_ONLY",
                "STRICT_NO_PRIOR",
            ],
            "same_target_query_pool_all_arms": True,
            "same_v37_prequential_stop_engine_all_arms": True,
            "switched_factors": [
                "OUTCOME_BLIND_SCHEDULER",
                "PROGRAM_CODE_PRIOR",
            ],
            "prediction_must_be_frozen_before_confirmation_outcome": True,
            "failed_candidate_retrained_only_after_observed_failure": True,
            "heldout_never_participates_in_stop": True,
            "prequential_confidence_denominator": 64,
            "fixed_label_floor_present": False,
            "fixed_confirmation_block_present": False,
        },
        "registered_gate": {
            "required_relation": (
                "JOINT_PRIOR_VALIDATED_GT_ZERO_AND_STRICT_VALIDATED_GT_ZERO_AND_"
                "ALL_OOD_REJECTED_AND_ALL_SCHEDULES_OUTCOME_BLIND"
            ),
            "sample_reduction_required": False,
            "program_prior_benefit_required": False,
            "scheduler_benefit_required": False,
            "all_occurrences_retained": True,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_relational_support_branch_evaluations": 1_000_000,
            "relational_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_template_labels_separate": True,
            "offline_residual_labels_separate": True,
            "underlying_target_source_generation_labels_separate": True,
            "counterfactual_arm_consumed_labels_separate": True,
            "post_stop_heldout_audit_labels_separate": True,
            "execution_steps_separate": True,
            "scheduler_compute_separate": True,
            "proposal_constructor_compute_separate": True,
            "online_planning_compute_separate": True,
        },
        "claim_boundary": {
            "registered_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "online_adaptive_acquisition_integrated": False,
            "online_actual_sample_reduction_claimed": False,
            "statistical_coverage_claimed": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_target_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v71(
            domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_PREREGISTRATION_V71_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RoleFreePrequentialPreregistrationV71:
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
            or domains.extension_content_id_v71(
                domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_PREREGISTRATION_V71_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V71 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: RoleFreePrequentialPreregistrationV71 | None = None


def freeze_role_free_prequential_preregistration_v71() -> RoleFreePrequentialPreregistrationV71:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V71 preregistration changed")
    _CACHE = RoleFreePrequentialPreregistrationV71(_ISSUER, raw, identity)
    return _CACHE


def verify_role_free_prequential_preregistration_v71(
    value: Any,
) -> RoleFreePrequentialPreregistrationV71:
    if type(value) is not RoleFreePrequentialPreregistrationV71:
        _fail("V71 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_role_free_prequential_preregistration_v71()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V71 preregistration differs from frozen output")
    return value


__all__ = (
    "BALANCED_TARGET_SEEDS",
    "COUPLED_TARGET_SEEDS",
    "MAINTENANCE_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "campaign_config_v71",
    "freeze_role_free_prequential_preregistration_v71",
    "verify_role_free_prequential_preregistration_v71",
)
