"""Outcome-free preregistration for V75 cross-occurrence model reuse."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75 as domains
from acfqp import construction_k7_reusable_version_space_preregistration_v73 as v73_pre
from acfqp.cross_occurrence_reusable_model_campaign_core_v75 import (
    build_cross_occurrence_reuse_campaign_document_v75,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "4ca98d4"
PREREGISTRATION_ID = "7b631cb303116d941b20a3f89e3178df95694eca8822712eb078009ea2478a17"
EXPECTED_CANONICAL_BYTE_COUNT = 6_774
EXPECTED_CANONICAL_SHA256 = "44f2c7f8e30c9ce86dd0f8b67a90397029b8edf81aed7d290a38f7f63f30045b"
V74_PREREGISTRATION_ID = "9eb5e746c44fd34632b959c41c9037193accfe3ce71f322a49b04f2062044c9d"
V74_CAMPAIGN_ID = "a60009b54923558baca3dd26af35c298b6618a86c3c4ec64639d7efa4c7a76f4"
V74_VERIFICATION_ID = "c43f1028c19871433bd0470fa37f5f2977a20bb1f31f94d3b0005db8d30f877f"
TEMPLATE_LIBRARY_ARTIFACT_ID = v73_pre.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_SEED_BY_FAMILY = {
    "COUPLED_EXCHANGE": 752_102,
    "MAINTENANCE_CASCADE": 753_101,
}
FRESH_TARGET_SEEDS = {
    "COUPLED_EXCHANGE": (761_201, 761_202),
    "MAINTENANCE_CASCADE": (761_301, 761_302),
}
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDEX = 1
SOURCE_WORKER_COUNT = 2
TARGET_WORKER_COUNT = 4
FRESH_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_COMPILED_SOURCE_COUNT = 2
MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT = 1
MAXIMUM_TARGET_GROUND_SUPPORT_LABELS = 100_000
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v75.py",
    "src/acfqp/cross_occurrence_reusable_model_campaign_core_v75.py",
    "src/acfqp/generic_reusable_version_space_certificate_planner_v43.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_learned_successor_support_acquisition_v41.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_reusable_amortization_campaign_v74.py",
    "src/acfqp/construction_k7_reusable_amortization_independent_verifier_v74.py",
)


class ConstructionK7CrossOccurrenceReusePreregistrationV75Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossOccurrenceReusePreregistrationV75Error(message)


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


def campaign_config_v75() -> dict[str, Any]:
    config = v73_pre.campaign_config_v73()
    config.update(
        source_seed_by_family=dict(SOURCE_SEED_BY_FAMILY),
        fresh_target_seeds=dict(FRESH_TARGET_SEEDS),
        source_episode_index=SOURCE_EPISODE_INDEX,
        target_episode_index=TARGET_EPISODE_INDEX,
        source_worker_count=SOURCE_WORKER_COUNT,
        target_worker_count=TARGET_WORKER_COUNT,
        fresh_target_occurrence_count=FRESH_TARGET_OCCURRENCE_COUNT,
        required_compiled_source_count=REQUIRED_COMPILED_SOURCE_COUNT,
        minimum_reduced_target_occurrence_count=(
            MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT
        ),
        maximum_target_ground_support_labels=MAXIMUM_TARGET_GROUND_SUPPORT_LABELS,
    )
    return config


def _document() -> dict[str, Any]:
    target_seeds = tuple(
        seed for seeds in FRESH_TARGET_SEEDS.values() for seed in seeds
    )
    payload = {
        "schema": "acfqp.cross_occurrence_reuse_preregistration.v75",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v74_preregistration_id": V74_PREREGISTRATION_ID,
            "v74_campaign_id": V74_CAMPAIGN_ID,
            "v74_verification_id": V74_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
            "v75_campaign_core_implementation_commit": IMPLEMENTATION_COMMIT,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v75_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_cross_occurrence_reuse_campaign_document_v75
            ),
            "frozen_before_any_registered_v75_target_outcome": True,
        },
        "identity_contract": {
            "source_seed_by_family": dict(SOURCE_SEED_BY_FAMILY),
            "source_models_are_deterministic_reconstructions_of_compiled_v73_sources": True,
            "source_outcomes_are_not_fresh_v75_selection_evidence": True,
            "fresh_target_seeds": {
                family: list(seeds) for family, seeds in FRESH_TARGET_SEEDS.items()
            },
            "fresh_target_occurrence_count": FRESH_TARGET_OCCURRENCE_COUNT,
            "fresh_target_seed_count": len(set(target_seeds)),
            "fresh_target_seeds_unique": len(target_seeds) == len(set(target_seeds)),
            "source_and_target_seeds_disjoint": not (
                set(SOURCE_SEED_BY_FAMILY.values()) & set(target_seeds)
            ),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
            "source_and_target_episode_indices_disjoint": (
                SOURCE_EPISODE_INDEX != TARGET_EPISODE_INDEX
            ),
        },
        "construction_contract": {
            "one_source_model_frozen_per_registered_family": True,
            "source_model_frozen_before_fresh_target_occurrences": True,
            "fresh_target_common_partial_candidate_acquired_before_matched_arms": True,
            "target_outcomes_used_to_refit_source_model": False,
            "same_target_adapter_kernel_seed_episode_in_both_arms": True,
            "same_exact_query_local_certificate_engine": True,
            "only_source_model_availability_differs_between_target_arms": True,
            "structural_compatibility_checked_before_abstract_search": True,
            "every_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "strict_incompatible_schema_rejected_without_ground_transition": True,
        },
        "registered_gate": {
            "required_relation": (
                "TWO_FROZEN_SOURCE_MODELS_AND_ZERO_SOURCE_HELDOUT_FAILURES_AND_"
                "FOUR_FRESH_CROSS_OCCURRENCE_MATCHED_TARGETS_AND_ZERO_ARM_FAILURES_"
                "AND_ALL_OOD_REJECTIONS_AND_CERTIFICATE_DISCIPLINE_CLEAN_AND_"
                "AGGREGATE_DERIVED_TARGET_LABELS_LT_STRICT_AND_AT_LEAST_ONE_"
                "TARGET_OCCURRENCE_STRICTLY_REDUCED"
            ),
            "required_compiled_source_count": REQUIRED_COMPILED_SOURCE_COUNT,
            "required_fresh_target_occurrence_count": FRESH_TARGET_OCCURRENCE_COUNT,
            "minimum_reduced_target_occurrence_count": (
                MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT
            ),
            "aggregate_cross_occurrence_target_reduction_required": True,
            "all_unfavourable_results_retained": True,
            "failure_must_be_preserved_before_any_successor": True,
        },
        "resource_schedule": {
            "source_worker_count": SOURCE_WORKER_COUNT,
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "maximum_target_ground_support_labels_per_arm_occurrence": (
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
            "source_partial_and_certificate_local_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "target_certificate_local_labels_separate_by_arm": True,
            "source_and_target_execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v75_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "cross_occurrence_model_reuse_verified": False,
            "cross_family_model_reuse_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v75_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v75(
            domains.CONSTRUCTION_K7_CROSS_OCCURRENCE_REUSE_PREREGISTRATION_V75_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossOccurrenceReusePreregistrationV75:
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
            or domains.extension_content_id_v75(
                domains.CONSTRUCTION_K7_CROSS_OCCURRENCE_REUSE_PREREGISTRATION_V75_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V75 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CrossOccurrenceReusePreregistrationV75 | None = None


def freeze_cross_occurrence_reuse_preregistration_v75(
) -> CrossOccurrenceReusePreregistrationV75:
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
        _fail("frozen V75 preregistration changed")
    _CACHE = CrossOccurrenceReusePreregistrationV75(_ISSUER, raw, identity)
    return _CACHE


def verify_cross_occurrence_reuse_preregistration_v75(
    value: Any,
) -> CrossOccurrenceReusePreregistrationV75:
    if type(value) is not CrossOccurrenceReusePreregistrationV75:
        _fail("V75 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_cross_occurrence_reuse_preregistration_v75()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V75 preregistration differs from frozen output")
    return value


__all__ = (
    "FRESH_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "SOURCE_SEED_BY_FAMILY",
    "campaign_config_v75",
    "freeze_cross_occurrence_reuse_preregistration_v75",
    "verify_cross_occurrence_reuse_preregistration_v75",
)
