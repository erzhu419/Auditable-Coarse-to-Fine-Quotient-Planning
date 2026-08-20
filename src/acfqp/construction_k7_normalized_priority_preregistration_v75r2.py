"""Outcome-free preregistration for V75r2 normalized portable priorities."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75r2 as domains
from acfqp import construction_k7_reusable_version_space_preregistration_v73 as v73_pre
from acfqp.normalized_portable_priority_campaign_core_v75r2 import (
    build_normalized_portable_priority_campaign_document_v75r2,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "3f1df61"
FLAT_ACTION_ADAPTER_COMMIT = "a388342"
PREREGISTRATION_ID = "27391ec9730a7038e78a17bbf95bd83b95fefc2e6a982a67f170f836553b995e"
EXPECTED_CANONICAL_BYTE_COUNT = 7_315
EXPECTED_CANONICAL_SHA256 = "f348c61592c03bc5aef10e4351053c70c240112c11b14f43bba3950b7199af78"
V75_FAILURE_ID = "975419a711a99e4c546555b6790dd205cc98f328a2001fc99316b3f712cd2921"
V75R1_PREREGISTRATION_ID = "b36ec9a233328d4493386d9bfa3e362886397bc11c07a64104490b7db9ab4acd"
V75R1_FAILURE_ID = "1024e36371f1cf3eada5ed3fab62e8910e1eb820041f2d6a79729c9835864078"
V74_CAMPAIGN_ID = "a60009b54923558baca3dd26af35c298b6618a86c3c4ec64639d7efa4c7a76f4"
V74_VERIFICATION_ID = "c43f1028c19871433bd0470fa37f5f2977a20bb1f31f94d3b0005db8d30f877f"
TEMPLATE_LIBRARY_ARTIFACT_ID = v73_pre.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_SEED_BY_FAMILY = {
    "COUPLED_EXCHANGE": 752_102,
    "MAINTENANCE_CASCADE": 753_101,
}
FRESH_TARGET_SEEDS = {
    "COUPLED_EXCHANGE": (763_201, 763_202),
    "MAINTENANCE_CASCADE": (763_301, 763_302),
}
SOURCE_EPISODE_INDEX = 0
PRIORITY_SOURCE_EPISODE_INDEX = 1
TARGET_EPISODE_INDEX = 3
SOURCE_WORKER_COUNT = 2
TARGET_WORKER_COUNT = 4
FRESH_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_USABLE_SOURCE_COUNT = 2
MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT = 1
MAXIMUM_TARGET_GROUND_SUPPORT_LABELS = 100_000
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v75r2.py",
    "src/acfqp/normalized_portable_priority_campaign_core_v75r2.py",
    "src/acfqp/generic_flat_action_adapter_v45.py",
    "src/acfqp/generic_portable_certificate_query_priority_v44.py",
    "src/acfqp/portable_priority_cross_occurrence_campaign_core_v75r1.py",
    "src/acfqp/cross_occurrence_reusable_model_campaign_core_v75.py",
    "src/acfqp/generic_reusable_version_space_certificate_planner_v43.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/construction_k7_cross_occurrence_reuse_failure_v75.py",
    "src/acfqp/construction_k7_portable_priority_failure_v75r1.py",
)


class ConstructionK7NormalizedPriorityPreregistrationV75R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7NormalizedPriorityPreregistrationV75R2Error(message)


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


def campaign_config_v75r2() -> dict[str, Any]:
    config = v73_pre.campaign_config_v73()
    config.update(
        source_seed_by_family=dict(SOURCE_SEED_BY_FAMILY),
        fresh_target_seeds=dict(FRESH_TARGET_SEEDS),
        source_episode_index=SOURCE_EPISODE_INDEX,
        priority_source_episode_index=PRIORITY_SOURCE_EPISODE_INDEX,
        target_episode_index=TARGET_EPISODE_INDEX,
        source_worker_count=SOURCE_WORKER_COUNT,
        target_worker_count=TARGET_WORKER_COUNT,
        fresh_target_occurrence_count=FRESH_TARGET_OCCURRENCE_COUNT,
        required_usable_source_count=REQUIRED_USABLE_SOURCE_COUNT,
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
        "schema": "acfqp.normalized_priority_preregistration.v75r2",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v75_failure_id": V75_FAILURE_ID,
            "v75r1_preregistration_id": V75R1_PREREGISTRATION_ID,
            "v75r1_failure_id": V75R1_FAILURE_ID,
            "v74_campaign_id": V74_CAMPAIGN_ID,
            "v74_verification_id": V74_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
            "flat_action_adapter_commit": FLAT_ACTION_ADAPTER_COMMIT,
            "v75r2_campaign_core_implementation_commit": IMPLEMENTATION_COMMIT,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v75r2_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R2),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_normalized_portable_priority_campaign_document_v75r2
            ),
            "frozen_before_any_registered_v75r2_target_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v75_zero_reduction_failure_preserved": True,
            "v75r1_pre_campaign_adapter_failure_preserved": True,
            "v75_or_v75r1_target_identity_reused": False,
            "corrective_mechanism": (
                "DOMAIN_ACTIONS_FOR_KERNEL_AND_FLAT_RAW_ACTIONS_FOR_GENERIC_RECEIPTS"
            ),
            "flat_action_adapter_applied_to_both_target_arms": True,
            "query_priority_remains_ordering_only": True,
        },
        "identity_contract": {
            "source_seed_by_family": dict(SOURCE_SEED_BY_FAMILY),
            "priority_source_episode_index": PRIORITY_SOURCE_EPISODE_INDEX,
            "fresh_target_seeds": {
                family: list(seeds) for family, seeds in FRESH_TARGET_SEEDS.items()
            },
            "fresh_target_occurrence_count": FRESH_TARGET_OCCURRENCE_COUNT,
            "fresh_target_seed_count": len(set(target_seeds)),
            "fresh_target_seeds_unique": len(target_seeds) == len(set(target_seeds)),
            "fresh_target_seeds_disjoint_from_predecessors": min(target_seeds) > 763_000,
            "source_and_target_seeds_disjoint": not (
                set(SOURCE_SEED_BY_FAMILY.values()) & set(target_seeds)
            ),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
            "source_priority_and_target_episode_indices_pairwise_disjoint": len(
                {SOURCE_EPISODE_INDEX, PRIORITY_SOURCE_EPISODE_INDEX, TARGET_EPISODE_INDEX}
            )
            == 3,
        },
        "construction_contract": {
            "one_model_and_priority_frozen_per_registered_family": True,
            "source_artifacts_frozen_before_fresh_target_occurrences": True,
            "domain_to_flat_action_adapter_used_by_both_target_arms": True,
            "domain_actions_used_only_for_kernel_calls": True,
            "flat_raw_actions_used_for_generic_receipts_and_planning": True,
            "target_outcomes_used_to_refit_source_artifacts": False,
            "same_target_adapter_kernel_seed_episode_in_both_arms": True,
            "same_exact_query_local_certificate_engine": True,
            "only_reusable_ordering_artifacts_differ_between_arms": True,
            "every_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "strict_incompatible_schema_rejected_before_ground_query": True,
        },
        "registered_gate": {
            "required_relation": (
                "TWO_USABLE_SOURCE_PAIRS_AND_FOUR_FRESH_TARGETS_AND_ZERO_ARM_"
                "FAILURES_AND_PRIORITY_USED_ON_ALL_TARGETS_AND_ALL_OOD_REJECTIONS_"
                "AND_CERTIFICATE_DISCIPLINE_CLEAN_AND_AGGREGATE_DERIVED_LABELS_"
                "LT_STRICT_AND_AT_LEAST_ONE_TARGET_REDUCED"
            ),
            "required_usable_source_count": REQUIRED_USABLE_SOURCE_COUNT,
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
            "offline_and_source_labels_separate": True,
            "priority_source_certificate_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "target_certificate_local_labels_separate_by_arm": True,
            "execution_steps_separate": True,
            "priority_lookup_and_abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v75r2_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "normalized_priority_cross_occurrence_reduction_verified": False,
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
        "fresh_registered_v75r2_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v75r2(
            domains.CONSTRUCTION_K7_NORMALIZED_PRIORITY_PREREGISTRATION_V75R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class NormalizedPriorityPreregistrationV75R2:
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
            or domains.extension_content_id_v75r2(
                domains.CONSTRUCTION_K7_NORMALIZED_PRIORITY_PREREGISTRATION_V75R2_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V75r2 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: NormalizedPriorityPreregistrationV75R2 | None = None


def freeze_normalized_priority_preregistration_v75r2(
) -> NormalizedPriorityPreregistrationV75R2:
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
        _fail("frozen V75r2 preregistration changed")
    _CACHE = NormalizedPriorityPreregistrationV75R2(_ISSUER, raw, identity)
    return _CACHE


def verify_normalized_priority_preregistration_v75r2(
    value: Any,
) -> NormalizedPriorityPreregistrationV75R2:
    if type(value) is not NormalizedPriorityPreregistrationV75R2:
        _fail("V75r2 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_normalized_priority_preregistration_v75r2()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V75r2 preregistration differs from frozen output")
    return value


__all__ = (
    "FRESH_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "SOURCE_SEED_BY_FAMILY",
    "campaign_config_v75r2",
    "freeze_normalized_priority_preregistration_v75r2",
    "verify_normalized_priority_preregistration_v75r2",
)
