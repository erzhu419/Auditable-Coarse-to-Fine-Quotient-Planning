"""Outcome-free preregistration for fresh V92 target planning."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v92 as domains
from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as previous
from acfqp.construction_k7_prior_only_occurrence_source_campaign_v91r2 import (
    CAMPAIGN_ID as V91R2_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V91R2_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_prior_only_occurrence_source_independent_verifier_v91r2 import (
    EXPECTED_CANONICAL_SHA256 as V91R2_VERIFICATION_SHA256,
    VERIFICATION_ID as V91R2_VERIFICATION_ID,
)
from acfqp.construction_k7_source_model_acceptance_independent_verifier_v91r3 import (
    EXPECTED_CANONICAL_SHA256 as V91R3_VERIFICATION_SHA256,
    VERIFICATION_ID as V91R3_VERIFICATION_ID,
)
from acfqp.construction_k7_source_model_acceptance_v91r3 import (
    ACCEPTANCE_ID as V91R3_ACCEPTANCE_ID,
    EXPECTED_CANONICAL_SHA256 as V91R3_ACCEPTANCE_SHA256,
)
from acfqp.generic_version_space_target_planner_v68 import (
    align_version_space_target_inputs_v68,
    run_matched_version_space_target_ablation_v68,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.version_space_target_campaign_core_v92 import (
    build_version_space_target_campaign_document_v92,
)


IMPLEMENTATION_COMMIT = "0856e1d"
PREREGISTRATION_ID = (
    "ad0aeffa3d80a0542a3fcc3bd2dc4207aedd86f2fec7ed20427f8260e6e834d7"
)
EXPECTED_CANONICAL_BYTE_COUNT = 6_201
EXPECTED_CANONICAL_SHA256 = (
    "d07eff7b1b12935321e5637f622248c92d7423b9384b150b1c08a2d43ce9a516"
)
TARGET_FAMILY = "COUPLED_EXCHANGE"
TARGET_SEEDS = (951_101, 951_102)
TARGET_EPISODE_INDEX = 2
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
TARGET_PARTIAL_ACQUISITION_MAXIMUM_GROUND_LABELS = 160
MAXIMUM_TARGET_GROUND_SUPPORT_LABELS = 10_000
MAXIMUM_ABSTRACT_DEPTH = 5
MAXIMUM_EXECUTION_STEPS = 12
MAXIMUM_ROBUST_STATE_DEPTH_EVALUATIONS = 1
MAXIMUM_ABSTRACT_SUPPORT_BRANCH_EVALUATIONS = 1_000_000
ABSTRACT_SUPPORT_FEASIBLE_BEAM_WIDTH = 8
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v92.py",
    "src/acfqp/generic_version_space_target_planner_v68.py",
    "src/acfqp/version_space_target_campaign_core_v92.py",
    "src/acfqp/generic_prior_only_partial_acquisition_v67.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
)
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v92.py",
        1875,
        "876ab33bd3e7d1509802ad64eb307dbae4cca7ecd82e63053b8bc250d46e0954",
    ),
    (
        "src/acfqp/generic_version_space_target_planner_v68.py",
        30779,
        "cfe59e61ea8e0c60a2895d9f2dbc72e1b1129b2c082ab735274ae5ac5bc47cab",
    ),
    (
        "src/acfqp/version_space_target_campaign_core_v92.py",
        13117,
        "a0d7721fcb2053c76e13dd76d552b0c2ad4a272bb67feaa797ebb153ba8abaab",
    ),
    (
        "src/acfqp/generic_prior_only_partial_acquisition_v67.py",
        7077,
        "bea4c52c4250435e4366fcc7b0f34a19bbb9f1373cf2decfc0b26f2fab7977bd",
    ),
    (
        "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
        36033,
        "d4b99c0f96688fc4d4dc4fae01a1d6896d254f166881ad5611c1e755c8bc1005",
    ),
)


class ConstructionK7VersionSpaceTargetPreregistrationV92Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7VersionSpaceTargetPreregistrationV92Error(message)


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": relative,
            "byte_count": len((SOURCE_ROOT / relative).read_bytes()),
            "sha256": hashlib.sha256(
                (SOURCE_ROOT / relative).read_bytes()
            ).hexdigest(),
        }
        for relative in BOUND_SOURCE_PATHS
    ]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v92() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v91r2())
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        target_partial_acquisition_maximum_ground_labels=(
            TARGET_PARTIAL_ACQUISITION_MAXIMUM_GROUND_LABELS
        ),
        maximum_target_ground_support_labels=(
            MAXIMUM_TARGET_GROUND_SUPPORT_LABELS
        ),
        maximum_abstract_depth=MAXIMUM_ABSTRACT_DEPTH,
        maximum_execution_steps=MAXIMUM_EXECUTION_STEPS,
        maximum_robust_state_depth_evaluations=(
            MAXIMUM_ROBUST_STATE_DEPTH_EVALUATIONS
        ),
        maximum_abstract_support_branch_evaluations=(
            MAXIMUM_ABSTRACT_SUPPORT_BRANCH_EVALUATIONS
        ),
        abstract_support_feasible_beam_width=(
            ABSTRACT_SUPPORT_FEASIBLE_BEAM_WIDTH
        ),
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.version_space_target_preregistration.v92",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v91r2_campaign_id": V91R2_CAMPAIGN_ID,
            "v91r2_campaign_sha256": V91R2_CAMPAIGN_SHA256,
            "v91r2_verification_id": V91R2_VERIFICATION_ID,
            "v91r2_verification_sha256": V91R2_VERIFICATION_SHA256,
            "v91r3_acceptance_id": V91R3_ACCEPTANCE_ID,
            "v91r3_acceptance_sha256": V91R3_ACCEPTANCE_SHA256,
            "v91r3_verification_id": V91R3_VERIFICATION_ID,
            "v91r3_verification_sha256": V91R3_VERIFICATION_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v92_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V92),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "alignment_callable": _callable_fact(
                align_version_space_target_inputs_v68
            ),
            "matched_episode_callable": _callable_fact(
                run_matched_version_space_target_ablation_v68
            ),
            "campaign_builder_callable": _callable_fact(
                build_version_space_target_campaign_document_v92
            ),
            "frozen_before_any_registered_v92_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_v91r2_source": set(TARGET_SEEDS).isdisjoint(
                previous.SOURCE_POOL_SEEDS
            ),
            "target_episode_index": TARGET_EPISODE_INDEX,
            "target_identities_cannot_be_selected_after_outcomes": True,
        },
        "construction_contract": {
            "accepted_complete_actual_version_space_consumed": True,
            "singleton_version_space_propagated_without_synthetic_uncertainty": True,
            "coordinate_projection_derived_only_from_target_common_partial_prefix": True,
            "source_model_and_alignment_frozen_before_target_episode": True,
            "same_exact_certificate_engine_in_both_arms": True,
            "only_world_model_availability_differs_between_episode_arms": True,
            "every_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "incompatible_schema_must_reject_before_target_episode": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_target_must_complete_both_arms": True,
            "execution_steps_per_model_arm_must_be_at_least_three": True,
            "at_least_two_executed_actions_per_target_must_match_abstract_proposals": True,
            "abstract_proposal_match_must_cover_at_least_half_of_execution": True,
            "every_actual_residual_and_terminal_candidate_must_be_jointly_propagated": True,
            "aggregate_strict_certificate_labels_must_exceed_model_labels": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "maximum_target_partial_acquisition_labels_per_occurrence": (
                TARGET_PARTIAL_ACQUISITION_MAXIMUM_GROUND_LABELS
            ),
            "maximum_certificate_local_labels_per_arm": (
                MAXIMUM_TARGET_GROUND_SUPPORT_LABELS
            ),
            "maximum_execution_steps_per_arm": MAXIMUM_EXECUTION_STEPS,
            "maximum_abstract_depth": MAXIMUM_ABSTRACT_DEPTH,
            "maximum_robust_state_depth_evaluations_per_plan": (
                MAXIMUM_ROBUST_STATE_DEPTH_EVALUATIONS
            ),
            "maximum_abstract_support_branch_evaluations_per_plan": (
                MAXIMUM_ABSTRACT_SUPPORT_BRANCH_EVALUATIONS
            ),
            "abstract_support_feasible_beam_width": (
                ABSTRACT_SUPPORT_FEASIBLE_BEAM_WIDTH
            ),
        },
        "accounting_contract": {
            "inherited_source_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "derived_and_strict_certificate_labels_separate": True,
            "execution_steps_separate_by_arm": True,
            "alignment_and_abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v92_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "multi_step_planning_primarily_in_abstract_model_verified": False,
            "sample_tax_reduction_verified_on_registered_target_workload": False,
            "second_domain_transfer_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v92_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v92(
            domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_PREREGISTRATION_V92_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class VersionSpaceTargetPreregistrationV92:
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
            or domains.extension_content_id_v92(
                domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_PREREGISTRATION_V92_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V92 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: VersionSpaceTargetPreregistrationV92 | None = None


def freeze_version_space_target_preregistration_v92(
) -> VersionSpaceTargetPreregistrationV92:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V92 frozen source facts changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V92 preregistration changed")
    _CACHE = VersionSpaceTargetPreregistrationV92(_ISSUER, raw, identity)
    return _CACHE


def verify_version_space_target_preregistration_v92(
    value: Any,
) -> VersionSpaceTargetPreregistrationV92:
    if type(value) is not VersionSpaceTargetPreregistrationV92:
        _fail("V92 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_version_space_target_preregistration_v92()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V92 preregistration differs from frozen bytes")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v92",
    "freeze_version_space_target_preregistration_v92",
    "verify_version_space_target_preregistration_v92",
)
