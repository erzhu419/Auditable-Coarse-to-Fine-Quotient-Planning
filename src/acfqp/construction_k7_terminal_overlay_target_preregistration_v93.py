"""Outcome-free preregistration for the fresh V93 target campaign."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v93 as domains
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
from acfqp.construction_k7_version_space_target_campaign_v92 import (
    CAMPAIGN_ID as V92_FAILED_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V92_FAILED_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_version_space_target_independent_verifier_v92 import (
    EXPECTED_CANONICAL_SHA256 as V92_FAILED_VERIFICATION_SHA256,
    VERIFICATION_ID as V92_FAILED_VERIFICATION_ID,
)
from acfqp.generic_joint_partial_terminal_acquisition_v70 import (
    acquire_joint_partial_terminal_prefix_v70,
)
from acfqp.generic_terminal_overlay_target_ablation_v72 import (
    run_matched_terminal_overlay_target_ablation_v72,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.terminal_overlay_target_campaign_core_v93 import (
    build_terminal_overlay_target_campaign_document_v93,
)


IMPLEMENTATION_COMMIT = "8dc1962"
PREREGISTRATION_ID = (
    "5e31d0c75c20f4d8c4408cbf7d91d83c194fd439fdf50cdfaff7e0b79852da88"
)
EXPECTED_CANONICAL_BYTE_COUNT = 7_926
EXPECTED_CANONICAL_SHA256 = (
    "f57c4f54427be24a14106d5be64e0925f85bfe8f7d9b4e30cad747cacee07e5c"
)
TARGET_FAMILY = "COUPLED_EXCHANGE"
TARGET_SEEDS = (961_101, 961_102)
TARGET_EPISODE_INDEX = 3
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
TARGET_JOINT_ACQUISITION_MAXIMUM_GROUND_LABELS = 160
TERMINAL_CONFIDENCE_DENOMINATOR = 4
MAXIMUM_TERMINAL_PROGRAM_CANDIDATES = 128
MAXIMUM_TARGET_GROUND_SUPPORT_LABELS = 10_000
MAXIMUM_ABSTRACT_DEPTH = 5
MAXIMUM_EXECUTION_STEPS = 12
MAXIMUM_ROBUST_STATE_DEPTH_EVALUATIONS = 1
MAXIMUM_ABSTRACT_SUPPORT_BRANCH_EVALUATIONS = 1_000_000
ABSTRACT_SUPPORT_FEASIBLE_BEAM_WIDTH = 8
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v93.py",
    "src/acfqp/generic_terminal_overlay_version_space_planner_v69.py",
    "src/acfqp/generic_joint_partial_terminal_acquisition_v70.py",
    "src/acfqp/generic_certificate_local_receding_engine_v71.py",
    "src/acfqp/generic_terminal_overlay_target_ablation_v72.py",
    "src/acfqp/terminal_overlay_target_campaign_core_v93.py",
    "src/acfqp/generic_prior_only_partial_acquisition_v67.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_relational_terminal_program_v28.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
)
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v93.py", 1946, "19e8b5e030d2caba3183027deaf0b2e9fb8d040f2eb758e9ef83ebeea9d3819c"),
    ("src/acfqp/generic_terminal_overlay_version_space_planner_v69.py", 33770, "24942c7579a64024bf8d9ec5b0ecfa5d8f651e28205ae89f2ba946b761d018da"),
    ("src/acfqp/generic_joint_partial_terminal_acquisition_v70.py", 7771, "7070fdfb843c5203c814c2a81735ff5e162eca905b8495eeac6a7cd2bb8fe3b5"),
    ("src/acfqp/generic_certificate_local_receding_engine_v71.py", 11698, "11ce7156662b5f6893c65a28eab41b919ac3e58100cf6c8e47205d5b96a0645a"),
    ("src/acfqp/generic_terminal_overlay_target_ablation_v72.py", 5991, "cb99373fcf5c46bb2aea4eef3965df07daf61748dbe1dd1ef303c50532a18d76"),
    ("src/acfqp/terminal_overlay_target_campaign_core_v93.py", 15425, "4ca6b13ccc34c1c83f30cffa03472a56f3e697d9b254741ae9f757d173320274"),
    ("src/acfqp/generic_prior_only_partial_acquisition_v67.py", 7077, "bea4c52c4250435e4366fcc7b0f34a19bbb9f1373cf2decfc0b26f2fab7977bd"),
    ("src/acfqp/generic_joint_successor_version_space_planner_v42.py", 36033, "d4b99c0f96688fc4d4dc4fae01a1d6896d254f166881ad5611c1e755c8bc1005"),
    ("src/acfqp/generic_relational_terminal_program_v28.py", 13906, "e69fcfb8697c20e044949b23b20b60b268fd762ec9306e2be3eaea37ce6a1c64"),
    ("src/acfqp/generic_layout_factorized_world_model_v5.py", 36010, "83d0f1505b039b705f44646662d69311a52aeb9c785ad45976014406a0b252ad"),
)


class ConstructionK7TerminalOverlayTargetPreregistrationV93Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TerminalOverlayTargetPreregistrationV93Error(message)


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


def campaign_config_v93() -> dict[str, Any]:
    config = copy.deepcopy(source_pre.campaign_config_v91r2())
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        target_joint_acquisition_maximum_ground_labels=(
            TARGET_JOINT_ACQUISITION_MAXIMUM_GROUND_LABELS
        ),
        terminal_confidence_denominator=TERMINAL_CONFIDENCE_DENOMINATOR,
        maximum_terminal_program_candidates=(
            MAXIMUM_TERMINAL_PROGRAM_CANDIDATES
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
        "schema": "acfqp.terminal_overlay_target_preregistration.v93",
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
            "v92_failed_campaign_id": V92_FAILED_CAMPAIGN_ID,
            "v92_failed_campaign_sha256": V92_FAILED_CAMPAIGN_SHA256,
            "v92_failed_verification_id": V92_FAILED_VERIFICATION_ID,
            "v92_failed_verification_sha256": V92_FAILED_VERIFICATION_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v93_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V93),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "joint_acquisition_callable": _callable_fact(
                acquire_joint_partial_terminal_prefix_v70
            ),
            "matched_episode_callable": _callable_fact(
                run_matched_terminal_overlay_target_ablation_v72
            ),
            "campaign_builder_callable": _callable_fact(
                build_terminal_overlay_target_campaign_document_v93
            ),
            "frozen_before_any_registered_v93_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_v91r2_source": set(TARGET_SEEDS).isdisjoint(
                source_pre.SOURCE_POOL_SEEDS
            ),
            "target_seeds_disjoint_from_v92_targets": set(TARGET_SEEDS).isdisjoint(
                {951_101, 951_102}
            ),
            "target_episode_index": TARGET_EPISODE_INDEX,
            "target_identities_cannot_be_selected_after_outcomes": True,
        },
        "construction_contract": {
            "accepted_complete_actual_source_version_space_consumed": True,
            "source_partial_and_residual_programs_reused": True,
            "source_terminal_program_not_assumed_transferable": True,
            "target_terminal_status_overlay_synthesized_prequentially": True,
            "alignment_frozen_at_partial_factor_stop": True,
            "witness_blind_joint_acquisition_only": True,
            "no_fixed_label_floor_or_confirmation_block": True,
            "source_residual_overlay_and_alignment_frozen_before_episode": True,
            "same_exact_certificate_engine_in_both_arms": True,
            "only_abstract_action_orderer_availability_differs_between_arms": True,
            "every_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "incompatible_schema_must_reject_before_target_episode": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_target_must_complete_both_arms": True,
            "execution_steps_per_model_arm_must_be_at_least_two": True,
            "at_least_two_executed_actions_per_target_must_match_abstract_proposals": True,
            "abstract_proposal_match_must_cover_at_least_half_of_execution": True,
            "every_actual_residual_and_target_terminal_candidate_must_be_propagated": True,
            "every_target_strict_certificate_labels_must_exceed_model_labels": True,
            "aggregate_strict_certificate_labels_must_exceed_model_labels": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_raw_joint_acquisition_rows_and_action_catalogues_must_be_embedded": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "maximum_joint_acquisition_labels_per_occurrence": (
                TARGET_JOINT_ACQUISITION_MAXIMUM_GROUND_LABELS
            ),
            "terminal_confidence_denominator": TERMINAL_CONFIDENCE_DENOMINATOR,
            "maximum_terminal_program_candidates": (
                MAXIMUM_TERMINAL_PROGRAM_CANDIDATES
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
            "target_partial_and_terminal_incremental_labels_separate": True,
            "derived_and_strict_certificate_labels_separate": True,
            "execution_steps_separate_by_arm": True,
            "derivation_certificate_and_abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v93_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "multi_step_planning_primarily_in_abstract_model_verified": False,
            "sample_tax_reduction_verified_on_registered_target_workload": False,
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
        "preregistration_id": domains.extension_content_id_v93(
            domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_PREREGISTRATION_V93_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TerminalOverlayTargetPreregistrationV93:
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
            or domains.extension_content_id_v93(
                domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_PREREGISTRATION_V93_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V93 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TerminalOverlayTargetPreregistrationV93 | None = None


def freeze_terminal_overlay_target_preregistration_v93(
) -> TerminalOverlayTargetPreregistrationV93:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if FROZEN_SOURCE_FACTS and _source_facts() != _frozen_source_facts():
        _fail("V93 preregistered source closure changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V93 frozen preregistration changed")
    _CACHE = TerminalOverlayTargetPreregistrationV93(_ISSUER, raw, identity)
    return _CACHE


def verify_terminal_overlay_target_preregistration_v93(
    value: Any,
) -> TerminalOverlayTargetPreregistrationV93:
    if type(value) is not TerminalOverlayTargetPreregistrationV93:
        _fail("V93 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_terminal_overlay_target_preregistration_v93()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V93 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v93",
    "freeze_terminal_overlay_target_preregistration_v93",
    "verify_terminal_overlay_target_preregistration_v93",
)
