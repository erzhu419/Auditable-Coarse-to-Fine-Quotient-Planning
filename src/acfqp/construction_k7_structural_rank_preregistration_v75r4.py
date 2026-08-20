"""Outcome-free preregistration for V75r4 structural-rank transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75r4 as domains
from acfqp import construction_k7_fail_closed_priority_preregistration_v75r3 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.structural_rank_transfer_campaign_core_v75r4 import (
    build_structural_rank_transfer_campaign_document_v75r4,
)


IMPLEMENTATION_COMMIT = "1603350"
STRUCTURAL_RANK_PRIOR_COMMIT = "747897e"
PREREGISTRATION_ID = "569cf3397dfd495ed26dde7a86d6975c5ca207ccb970b6bfd6f4799bfe590a6e"
EXPECTED_CANONICAL_BYTE_COUNT = 6_003
EXPECTED_CANONICAL_SHA256 = "efa1ac4634451534677942c1dca96943aad2d135fcdf06f0facd991fea7ffa96"
V75_FAILURE_ID = previous.V75_FAILURE_ID
V75R1_FAILURE_ID = previous.V75R1_FAILURE_ID
V75R2_FAILURE_ID = previous.V75R2_FAILURE_ID
V75R3_CAMPAIGN_ID = "6ea230d88e962268e924c457a0e3de960797238affb8b3ff518b55fda8c40902"
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_SEED_BY_FAMILY = dict(previous.SOURCE_SEED_BY_FAMILY)
FRESH_TARGET_SEEDS = {
    "COUPLED_EXCHANGE": (765_201, 765_202),
    "MAINTENANCE_CASCADE": (765_301, 765_302),
}
TARGET_EPISODE_INDEX = 5
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v75r4.py",
    "src/acfqp/structural_rank_transfer_campaign_core_v75r4.py",
    "src/acfqp/generic_structural_rank_query_prior_v46.py",
    "src/acfqp/generic_flat_action_adapter_v45.py",
    "src/acfqp/generic_portable_certificate_query_priority_v44.py",
    "src/acfqp/normalized_portable_priority_campaign_core_v75r2.py",
    "src/acfqp/portable_priority_cross_occurrence_campaign_core_v75r1.py",
)


class ConstructionK7StructuralRankPreregistrationV75R4Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralRankPreregistrationV75R4Error(message)


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


def campaign_config_v75r4() -> dict[str, Any]:
    config = previous.campaign_config_v75r3()
    config.update(
        fresh_target_seeds={key: tuple(value) for key, value in FRESH_TARGET_SEEDS.items()},
        target_episode_index=TARGET_EPISODE_INDEX,
    )
    return config


def _document() -> dict[str, Any]:
    target_seeds = tuple(seed for values in FRESH_TARGET_SEEDS.values() for seed in values)
    payload = {
        "schema": "acfqp.structural_rank_preregistration.v75r4",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v75_failure_id": V75_FAILURE_ID,
            "v75r1_failure_id": V75R1_FAILURE_ID,
            "v75r2_failure_id": V75R2_FAILURE_ID,
            "v75r3_failed_gate_campaign_id": V75R3_CAMPAIGN_ID,
            "structural_rank_prior_commit": STRUCTURAL_RANK_PRIOR_COMMIT,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v75r4_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R4),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_structural_rank_transfer_campaign_document_v75r4
            ),
            "frozen_before_any_registered_v75r4_target_outcome": True,
        },
        "failure_driven_successor_contract": {
            "all_v75_through_v75r3_failures_preserved": True,
            "v75r3_exact_state_and_layout_priority_rejected": True,
            "source_priority_replaced_by_anonymous_legal_action_rank_relation": True,
            "target_local_priority_uses_initial_observation_and_descriptors_only": True,
            "target_transition_outcomes_used_to_translate_priority": False,
        },
        "identity_contract": {
            "source_seed_by_family": dict(SOURCE_SEED_BY_FAMILY),
            "fresh_target_seeds": {
                key: list(value) for key, value in FRESH_TARGET_SEEDS.items()
            },
            "fresh_target_seed_count": len(set(target_seeds)),
            "fresh_target_seed_identities_unique": len(target_seeds) == len(set(target_seeds)),
            "fresh_target_seeds_disjoint_from_predecessors": min(target_seeds) > 765_000,
            "source_and_target_seeds_disjoint": not (
                set(SOURCE_SEED_BY_FAMILY.values()) & set(target_seeds)
            ),
            "source_episode_index": 0,
            "priority_source_episode_index": 1,
            "target_episode_index": TARGET_EPISODE_INDEX,
        },
        "construction_contract": {
            "structural_rank_prior_derived_from_source_query_rows": True,
            "target_translation_uses_no_transition_outcome": True,
            "target_translation_is_ordering_only": True,
            "target_partial_candidate_and_initial_observation_may_be_used": True,
            "target_local_priority_cannot_supply_ground_or_safety_authority": True,
            "target_arm_failures_are_retained_before_aggregation": True,
            "domain_actions_used_only_for_kernel_calls": True,
            "flat_raw_actions_used_for_generic_receipts_and_planning": True,
            "same_target_adapter_kernel_seed_episode_in_both_arms": True,
            "target_outcomes_used_to_refit_source_artifacts": False,
            "every_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "strict_incompatible_schema_rejected_before_ground_query": True,
        },
        "registered_gate": {
            "required_relation": (
                "TWO_SOURCE_PRIORS_AND_FOUR_FRESH_TARGETS_AND_ZERO_ARM_FAILURES_AND_"
                "STRUCTURAL_RANK_PRIORITY_USED_ON_ALL_TARGETS_AND_ALL_OOD_REJECTIONS_"
                "AND_CERTIFICATE_DISCIPLINE_CLEAN_AND_AGGREGATE_DERIVED_LABELS_LT_"
                "STRICT_AND_AT_LEAST_ONE_TARGET_REDUCED"
            ),
            "required_usable_source_count": 2,
            "required_fresh_target_occurrence_count": 4,
            "minimum_reduced_target_occurrence_count": 1,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": 2,
            "target_worker_count": 4,
            "maximum_simultaneous_worker_count": 4,
            "maximum_target_ground_support_labels_per_arm_occurrence": 100_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_and_priority_source_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "target_certificate_labels_separate_by_arm": True,
            "execution_steps_separate": True,
            "planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v75r4_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "cross_occurrence_sample_reduction_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v75r4_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v75r4(
            domains.CONSTRUCTION_K7_STRUCTURAL_RANK_PREREGISTRATION_V75R4_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralRankPreregistrationV75R4:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v75r4(
                domains.CONSTRUCTION_K7_STRUCTURAL_RANK_PREREGISTRATION_V75R4_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V75r4 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: StructuralRankPreregistrationV75R4 | None = None


def freeze_structural_rank_preregistration_v75r4() -> StructuralRankPreregistrationV75R4:
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
        _fail("frozen V75r4 preregistration changed")
    _CACHE = StructuralRankPreregistrationV75R4(_ISSUER, raw, identity)
    return _CACHE


def verify_structural_rank_preregistration_v75r4(
    value: Any,
) -> StructuralRankPreregistrationV75R4:
    if type(value) is not StructuralRankPreregistrationV75R4:
        _fail("V75r4 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_structural_rank_preregistration_v75r4()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V75r4 preregistration differs from frozen output")
    return value


__all__ = (
    "FRESH_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "campaign_config_v75r4",
    "freeze_structural_rank_preregistration_v75r4",
    "verify_structural_rank_preregistration_v75r4",
)
