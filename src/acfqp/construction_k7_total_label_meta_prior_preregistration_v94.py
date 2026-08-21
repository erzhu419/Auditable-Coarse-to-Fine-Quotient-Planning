"""Outcome-free preregistration for the fresh V94 total-label Gate."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v94 as domains
from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as source_pre
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
from acfqp.construction_k7_terminal_overlay_target_campaign_v93 import (
    CAMPAIGN_ID as V93_FAILED_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V93_FAILED_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_terminal_overlay_target_independent_verifier_v93 import (
    EXPECTED_CANONICAL_SHA256 as V93_FAILED_VERIFICATION_SHA256,
    VERIFICATION_ID as V93_FAILED_VERIFICATION_ID,
)
from acfqp.generic_low_label_residual_applicability_v73 import (
    acquire_low_label_residual_applicability_v73,
)
from acfqp.generic_total_label_residual_transfer_ablation_v75 import (
    run_total_label_residual_transfer_ablation_v75,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.total_label_meta_prior_campaign_core_v94 import (
    build_total_label_meta_prior_campaign_document_v94,
)


IMPLEMENTATION_COMMIT = "d3e054e"
PREREGISTRATION_ID = (
    "c3b9e3e8b5ea76bb347afdc6d5ebcb07f4c974f4fbbad013ef188e24d5173018"
)
EXPECTED_CANONICAL_BYTE_COUNT = 7_414
EXPECTED_CANONICAL_SHA256 = (
    "42c613a419f48a1e41e1bf634056556b402b6db7826f566acdfc2a98aa0fdecf"
)
TARGET_FAMILY = "COUPLED_EXCHANGE"
TARGET_SEEDS = (971_101, 971_102)
TARGET_EPISODE_INDEX = 4
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_META_PRIOR_ODDS = 16
CONFIDENCE_DENOMINATOR = 4
MAXIMUM_APPLICABILITY_GROUND_SUPPORT_LABELS = 40
MAXIMUM_INCREMENTAL_CERTIFICATE_GROUND_SUPPORT_LABELS = 10_000
MAXIMUM_ABSTRACT_DEPTH = 5
MAXIMUM_EXECUTION_STEPS = 12
MAXIMUM_ROBUST_STATE_DEPTH_EVALUATIONS = 1
MAXIMUM_ABSTRACT_SUPPORT_BRANCH_EVALUATIONS = 1_000_000
ABSTRACT_SUPPORT_FEASIBLE_BEAM_WIDTH = 8
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v94.py",
    "src/acfqp/generic_low_label_residual_applicability_v73.py",
    "src/acfqp/generic_preloaded_certificate_receding_engine_v74.py",
    "src/acfqp/generic_total_label_residual_transfer_ablation_v75.py",
    "src/acfqp/total_label_meta_prior_campaign_core_v94.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
)
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v94.py", 1922, "2f94effaca2f65de53574d2b0c684262dff6c71fbfc8296e19aafa08f40acfe6"),
    ("src/acfqp/generic_low_label_residual_applicability_v73.py", 14763, "5dd1343ffd103f9334f2922354ac55a7810230b4b3a7084eaa8a1287006163f3"),
    ("src/acfqp/generic_preloaded_certificate_receding_engine_v74.py", 12503, "a470ec2d750353c7d951d7d82494b307be61fb99eb3ca3bd8b2023880d7392c3"),
    ("src/acfqp/generic_total_label_residual_transfer_ablation_v75.py", 6168, "a4af552f49972f4ceb7c047ab77fd78404342c21e8e56c075559402ec7b34ded"),
    ("src/acfqp/total_label_meta_prior_campaign_core_v94.py", 17181, "07a47e61fa435e39b4379839a1ac3d80a7780fa5d3334d47d68e8ef66787a5ac"),
    ("src/acfqp/generic_joint_successor_version_space_planner_v42.py", 36033, "d4b99c0f96688fc4d4dc4fae01a1d6896d254f166881ad5611c1e755c8bc1005"),
    ("src/acfqp/generic_layout_factorized_world_model_v5.py", 36010, "83d0f1505b039b705f44646662d69311a52aeb9c785ad45976014406a0b252ad"),
)


class ConstructionK7TotalLabelMetaPriorPreregistrationV94Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TotalLabelMetaPriorPreregistrationV94Error(message)


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
    if not FROZEN_SOURCE_FACTS:
        return _source_facts()
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


def campaign_config_v94() -> dict[str, Any]:
    config = copy.deepcopy(source_pre.campaign_config_v91r2())
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        source_meta_prior_odds=SOURCE_META_PRIOR_ODDS,
        confidence_denominator=CONFIDENCE_DENOMINATOR,
        maximum_applicability_ground_support_labels=(
            MAXIMUM_APPLICABILITY_GROUND_SUPPORT_LABELS
        ),
        maximum_incremental_certificate_ground_support_labels=(
            MAXIMUM_INCREMENTAL_CERTIFICATE_GROUND_SUPPORT_LABELS
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
        "schema": "acfqp.total_label_meta_prior_preregistration.v94",
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
            "v93_failed_campaign_id": V93_FAILED_CAMPAIGN_ID,
            "v93_failed_campaign_sha256": V93_FAILED_CAMPAIGN_SHA256,
            "v93_failed_verification_id": V93_FAILED_VERIFICATION_ID,
            "v93_failed_verification_sha256": V93_FAILED_VERIFICATION_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v94_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V94),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "applicability_callable": _callable_fact(
                acquire_low_label_residual_applicability_v73
            ),
            "total_label_ablation_callable": _callable_fact(
                run_total_label_residual_transfer_ablation_v75
            ),
            "campaign_builder_callable": _callable_fact(
                build_total_label_meta_prior_campaign_document_v94
            ),
            "frozen_before_any_registered_v94_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_v91r2_source": set(TARGET_SEEDS).isdisjoint(
                source_pre.SOURCE_POOL_SEEDS
            ),
            "target_seeds_disjoint_from_v92_and_v93_targets": set(
                TARGET_SEEDS
            ).isdisjoint({951_101, 951_102, 961_101, 961_102}),
            "target_episode_index": TARGET_EPISODE_INDEX,
            "target_identities_cannot_be_selected_after_outcomes": True,
        },
        "construction_contract": {
            "same_applicability_synthesizer_and_stop_rule_in_prior_on_off_arms": True,
            "only_source_meta_prior_odds_differs_between_acquisition_arms": True,
            "source_meta_prior_odds": SOURCE_META_PRIOR_ODDS,
            "source_meta_prior_strength_is_preregistered_empirical_hyperparameter": True,
            "source_meta_prior_strength_not_claimed_universal": True,
            "source_terminal_program_is_fallible_action_ordering_heuristic": True,
            "source_terminal_applicability_not_required": True,
            "acquisition_rows_paid_once_then_reused_as_exact_evidence": True,
            "strict_cold_direct_receives_no_free_target_rows": True,
            "same_exact_certificate_engine_in_all_arms": True,
            "every_incremental_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "incompatible_source_model_must_reject_before_target_observation": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_target_must_complete_meta_prior_no_prior_and_direct_arms": True,
            "execution_steps_per_meta_prior_arm_must_be_at_least_two": True,
            "at_least_two_executed_actions_per_target_must_match_abstract_proposals": True,
            "abstract_proposal_match_must_cover_at_least_half_of_execution": True,
            "meta_prior_total_labels_must_not_exceed_direct_on_any_target": True,
            "meta_prior_total_labels_must_be_strictly_lower_than_direct_in_aggregate": True,
            "meta_prior_total_labels_must_be_strictly_lower_than_no_prior_on_every_target_and_aggregate": True,
            "strict_incompatible_model_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "maximum_applicability_labels_per_arm_occurrence": (
                MAXIMUM_APPLICABILITY_GROUND_SUPPORT_LABELS
            ),
            "maximum_incremental_certificate_labels_per_episode": (
                MAXIMUM_INCREMENTAL_CERTIFICATE_GROUND_SUPPORT_LABELS
            ),
            "maximum_execution_steps_per_arm": MAXIMUM_EXECUTION_STEPS,
            "maximum_abstract_depth": MAXIMUM_ABSTRACT_DEPTH,
            "maximum_abstract_support_branch_evaluations_per_plan": (
                MAXIMUM_ABSTRACT_SUPPORT_BRANCH_EVALUATIONS
            ),
            "abstract_support_feasible_beam_width": (
                ABSTRACT_SUPPORT_FEASIBLE_BEAM_WIDTH
            ),
        },
        "accounting_contract": {
            "inherited_source_labels_separate": True,
            "meta_prior_and_no_prior_acquisition_labels_separate": True,
            "incremental_certificate_labels_separate_by_arm": True,
            "total_target_labels_include_acquisition_and_incremental_certificate_labels": True,
            "execution_steps_separate_by_arm": True,
            "derivation_certificate_and_abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v94_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "sample_tax_reduction_verified_on_registered_target_workload": False,
            "sample_tax_reduction_generalized_beyond_registered_workload": False,
            "complete_world_model_synthesized": False,
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
        "preregistration_id": domains.extension_content_id_v94(
            domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_PREREGISTRATION_V94_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TotalLabelMetaPriorPreregistrationV94:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v94(
                domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_PREREGISTRATION_V94_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V94 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TotalLabelMetaPriorPreregistrationV94 | None = None


def freeze_total_label_meta_prior_preregistration_v94(
) -> TotalLabelMetaPriorPreregistrationV94:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if FROZEN_SOURCE_FACTS and _source_facts() != _frozen_source_facts():
        _fail("V94 preregistered source closure changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V94 frozen preregistration changed")
    _CACHE = TotalLabelMetaPriorPreregistrationV94(_ISSUER, raw, identity)
    return _CACHE


def verify_total_label_meta_prior_preregistration_v94(
    value: Any,
) -> TotalLabelMetaPriorPreregistrationV94:
    if type(value) is not TotalLabelMetaPriorPreregistrationV94:
        _fail("V94 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_total_label_meta_prior_preregistration_v94()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V94 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v94",
    "freeze_total_label_meta_prior_preregistration_v94",
    "verify_total_label_meta_prior_preregistration_v94",
)
