"""Outcome-free preregistration for V74 reusable-model amortization."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v74 as domains
from acfqp import construction_k7_reusable_version_space_preregistration_v73 as v73_pre
from acfqp.construction_k7_reusable_version_space_campaign_v73 import (
    CAMPAIGN_ID as V73_CAMPAIGN_ID,
)
from acfqp.construction_k7_reusable_version_space_independent_verifier_v73 import (
    VERIFICATION_ID as V73_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.reusable_amortization_campaign_core_v74 import (
    build_reusable_amortization_campaign_document_v74,
)


IMPLEMENTATION_COMMIT = "1139cd3"
PREREGISTRATION_ID = "9eb5e746c44fd34632b959c41c9037193accfe3ce71f322a49b04f2062044c9d"
EXPECTED_CANONICAL_BYTE_COUNT = 7_556
EXPECTED_CANONICAL_SHA256 = "bcc0831a8a39024d96c4653daca4b6a0d2ffb04b1432711aec4c73708a3f08cb"
TEMPLATE_LIBRARY_ARTIFACT_ID = v73_pre.TEMPLATE_LIBRARY_ARTIFACT_ID
BALANCED_TARGET_SEEDS = v73_pre.BALANCED_TARGET_SEEDS
COUPLED_TARGET_SEEDS = v73_pre.COUPLED_TARGET_SEEDS
MAINTENANCE_TARGET_SEEDS = v73_pre.MAINTENANCE_TARGET_SEEDS
SOURCE_EPISODE_INDEX = v73_pre.SOURCE_EPISODE_INDEX
AMORTIZATION_TARGET_EPISODE_INDICES = tuple(range(2, 34))
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
MINIMUM_COMPILED_OCCURRENCE_COUNT = 3
MAXIMUM_TARGET_GROUND_SUPPORT_LABELS = 100_000
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v74.py",
    "src/acfqp/reusable_amortization_campaign_core_v74.py",
    "src/acfqp/generic_reusable_version_space_certificate_planner_v43.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_learned_successor_support_acquisition_v41.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_adaptive_role_free_terminal_acquisition_v35.py",
    "src/acfqp/generic_role_free_relational_template_v33.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_reusable_version_space_campaign_v73.py",
    "src/acfqp/construction_k7_reusable_version_space_independent_verifier_v73.py",
)


class ConstructionK7ReusableAmortizationPreregistrationV74Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReusableAmortizationPreregistrationV74Error(message)


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


def campaign_config_v74() -> dict[str, Any]:
    config = v73_pre.campaign_config_v73()
    config.update(
        target_seeds={
            "BALANCED_BATCH_REFINEMENT": BALANCED_TARGET_SEEDS,
            "COUPLED_EXCHANGE": COUPLED_TARGET_SEEDS,
            "MAINTENANCE_CASCADE": MAINTENANCE_TARGET_SEEDS,
        },
        target_occurrence_count=TARGET_OCCURRENCE_COUNT,
        worker_count=WORKER_COUNT,
        source_episode_index=SOURCE_EPISODE_INDEX,
        amortization_target_episode_indices=AMORTIZATION_TARGET_EPISODE_INDICES,
        minimum_compiled_occurrence_count=MINIMUM_COMPILED_OCCURRENCE_COUNT,
        maximum_target_ground_support_labels=MAXIMUM_TARGET_GROUND_SUPPORT_LABELS,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.reusable_amortization_preregistration.v74",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v73_preregistration_id": v73_pre.PREREGISTRATION_ID,
            "v73_campaign_id": V73_CAMPAIGN_ID,
            "v73_verification_id": V73_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
            "v74_campaign_core_implementation_commit": IMPLEMENTATION_COMMIT,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v74_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V74),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_reusable_amortization_campaign_document_v74
            ),
            "frozen_before_any_registered_v74_target_outcome": True,
        },
        "identity_contract": {
            "source_occurrence_identities_reused_exactly_from_frozen_v73": True,
            "source_outcomes_are_not_fresh_v74_selection_evidence": True,
            "source_target_families": {
                "BALANCED_BATCH_REFINEMENT": list(BALANCED_TARGET_SEEDS),
                "COUPLED_EXCHANGE": list(COUPLED_TARGET_SEEDS),
                "MAINTENANCE_CASCADE": list(MAINTENANCE_TARGET_SEEDS),
            },
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "fresh_target_episode_indices": list(
                AMORTIZATION_TARGET_EPISODE_INDICES
            ),
            "fresh_target_episode_count": len(AMORTIZATION_TARGET_EPISODE_INDICES),
            "target_episodes_disjoint_from_v73_target_episode_one": (
                1 not in AMORTIZATION_TARGET_EPISODE_INDICES
            ),
            "target_episodes_disjoint_from_source": (
                SOURCE_EPISODE_INDEX not in AMORTIZATION_TARGET_EPISODE_INDICES
            ),
            "all_registered_target_episode_identities_retained": True,
        },
        "construction_contract": {
            "deterministically_reconstruct_frozen_v73_source_models": True,
            "source_model_frozen_once_before_all_fresh_target_episodes": True,
            "target_outcomes_used_to_refit_source_model": False,
            "fresh_exact_overlay_for_every_arm_episode": True,
            "same_target_adapter_kernel_seed_episode_per_matched_pair": True,
            "same_exact_query_local_certificate_engine": True,
            "only_reusable_model_availability_differs": True,
            "every_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "source_abstentions_retained_without_target_execution": True,
        },
        "registered_gate": {
            "required_relation": (
                "SOURCE_HELDOUT_FAILURES_EQ_ZERO_AND_COMPILED_GE_3_AND_ALL_"
                "REGISTERED_TARGET_ARMS_SUCCEED_AND_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_EVERY_TARGET_EPISODE_AGGREGATE_LABEL_SAVINGS_GT_ZERO_AND_"
                "CUMULATIVE_SAVINGS_REPAY_INCREMENTAL_SOURCE_MODEL_LABELS_WITHIN_"
                "THE_32_EPISODE_HORIZON"
            ),
            "minimum_compiled_occurrence_count": MINIMUM_COMPILED_OCCURRENCE_COUNT,
            "positive_aggregate_savings_required_in_every_target_episode": True,
            "incremental_break_even_required_within_registered_horizon": True,
            "all_occurrences_and_abstentions_retained": True,
            "unfavourable_result_must_be_preserved_before_any_successor": True,
        },
        "sample_amortization_contract": {
            "investment_axis": "INCREMENTAL_CERTIFICATE_LOCAL_SOURCE_MODEL_LABELS_ON_COMPILED_OCCURRENCES",
            "repayment_axis": "CUMULATIVE_MATCHED_STRICT_MINUS_REUSABLE_TARGET_CERTIFICATE_LOCAL_LABELS",
            "first_break_even_episode_ordinal_reported": True,
            "shared_partial_acquisition_excluded_as_common_to_both_arms": True,
            "offline_library_labels_excluded": True,
            "planning_compute_excluded": True,
            "execution_steps_excluded": True,
            "empirical_incremental_sample_amortization_only": True,
            "official_N_break_even_claimed": False,
            "workload_economics_claimed": False,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "target_episode_count_per_compiled_occurrence": len(
                AMORTIZATION_TARGET_EPISODE_INDICES
            ),
            "maximum_target_ground_support_labels_per_arm_episode": (
                MAXIMUM_TARGET_GROUND_SUPPORT_LABELS
            ),
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_successor_support_states": 4_096,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
            "relational_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_template_labels_separate": True,
            "offline_residual_labels_separate": True,
            "source_common_partial_labels_separate": True,
            "incremental_source_model_labels_separate": True,
            "target_certificate_local_labels_separate_by_arm_and_episode": True,
            "source_and_target_execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v74_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "source_model_investment_fully_amortized": False,
            "official_economics_evaluated": False,
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
        "fresh_registered_v74_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v74(
            domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_PREREGISTRATION_V74_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReusableAmortizationPreregistrationV74:
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
            or domains.extension_content_id_v74(
                domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_PREREGISTRATION_V74_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V74 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ReusableAmortizationPreregistrationV74 | None = None


def freeze_reusable_amortization_preregistration_v74(
) -> ReusableAmortizationPreregistrationV74:
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
        _fail("frozen V74 preregistration changed")
    _CACHE = ReusableAmortizationPreregistrationV74(_ISSUER, raw, identity)
    return _CACHE


def verify_reusable_amortization_preregistration_v74(
    value: Any,
) -> ReusableAmortizationPreregistrationV74:
    if type(value) is not ReusableAmortizationPreregistrationV74:
        _fail("V74 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_reusable_amortization_preregistration_v74()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V74 preregistration differs from frozen output")
    return value


__all__ = (
    "AMORTIZATION_TARGET_EPISODE_INDICES",
    "BALANCED_TARGET_SEEDS",
    "COUPLED_TARGET_SEEDS",
    "MAINTENANCE_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "campaign_config_v74",
    "freeze_reusable_amortization_preregistration_v74",
    "verify_reusable_amortization_preregistration_v74",
)
