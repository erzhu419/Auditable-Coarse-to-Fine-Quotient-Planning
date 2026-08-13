"""Outcome-free preregistration for native-accounted long 2048 episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import construction_k7_standard_2048_long_episode_preregistration_v11 as v11
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_CAMPAIGN_V12_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_COUNTER_BUNDLE_V12_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_DECISION_V12_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_EPISODE_V12_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_MEASUREMENT_V12_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_PREREGISTRATION_V12_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_VERIFICATION_V12_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "12.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.171"
PROFILE_KEY = "construction_k7_standard_2048_accounted_long_episode_v12"
PREREGISTRATION_ID = (
    "c3c3d5ce61e8a247fe9b3c6f35e8d15a735b9d6dd25f881fcd64490af833fd34"
)
V169_LONG_CAMPAIGN_ID = (
    "158dfab7d25c70d46aabc98620d4bccd55ff5f2a39c354aa6ca918346e191fdd"
)
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 64
OFFLINE_OBSERVATION_COUNT = 192
EPISODE_WORKER_COUNT = 4

PREREGISTERED_INITIAL_BOARDS = (
    (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
    (2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
)
PREREGISTERED_EPISODE_SEEDS = tuple(
    f"standard-2048-v171-accounted-long-{index:02d}-20260813"
    for index in range(len(PREREGISTERED_INITIAL_BOARDS))
)

FUTURE_DOMAINS = {
    "preregistration": (
        CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_PREREGISTRATION_V12_DOMAIN
    ),
    "measurement": CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_MEASUREMENT_V12_DOMAIN,
    "counter_bundle": (
        CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_COUNTER_BUNDLE_V12_DOMAIN
    ),
    "decision": CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_DECISION_V12_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_EPISODE_V12_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_CAMPAIGN_V12_DOMAIN,
    "verification": (
        CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_VERIFICATION_V12_DOMAIN
    ),
}


class ConstructionK7Standard2048AccountedPreregistrationV12Error(ValueError):
    """The fresh workload, receipt topology, or locked claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AccountedPreregistrationV12Error(message)


def _profile_binding() -> dict[str, Any]:
    registry = registry_v8.official_counter_registry_v8()
    comparison = registry_v8.official_comparison_profile_v8(registry)
    actual = registry_v8.official_actual_projection_profile_v8(
        registry, comparison
    )
    stage = registry_v8.official_stage_profile_v8(registry)
    return {
        "counter_registry_id": registry.registry_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": actual.actual_projection_profile_id,
        "stage_profile_id": stage.stage_profile_id,
        "required_counter_path_count": len(registry.required_paths),
        "operational_counter_path_count": len(registry.operational_leaves),
    }


def _canonical_orbits(boards: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in boards
    )


def _document() -> dict[str, Any]:
    profiles = _profile_binding()
    old_orbits = set(_canonical_orbits(v11.PREREGISTERED_INITIAL_BOARDS))
    new_orbits = _canonical_orbits(PREREGISTERED_INITIAL_BOARDS)
    fresh = len(set(new_orbits)) == len(new_orbits) and not (
        old_orbits & set(new_orbits)
    )
    payload = {
        "schema": "acfqp.standard_2048_accounted_preregistration.v12",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v169_long_campaign_id": V169_LONG_CAMPAIGN_ID,
        "v169_is_frozen_predecessor_evidence_only": True,
        "v169_independent_verification_required_before_execution": True,
        "fresh_target_identities_required": True,
        "planning_horizon": PLANNING_HORIZON,
        "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
        "early_terminal_closure_allowed": True,
        "episode_worker_count": EPISODE_WORKER_COUNT,
        "preregistered_initial_boards": [
            list(board) for board in PREREGISTERED_INITIAL_BOARDS
        ],
        "preregistered_initial_board_d4_representatives": [
            list(board) for board in new_orbits
        ],
        "initial_boards_are_fresh_and_d4_disjoint_from_v169": fresh,
        "preregistered_episode_seeds": list(PREREGISTERED_EPISODE_SEEDS),
        "episode_count": len(PREREGISTERED_INITIAL_BOARDS),
        "maximum_decision_count": (
            len(PREREGISTERED_INITIAL_BOARDS)
            * MAXIMUM_DECISIONS_PER_EPISODE
        ),
        "accepted_operator_contract": {
            "accepted_dynamics_identity_id": v11._dynamics_identity_document(  # noqa: SLF001
                "STANDARD_UNIFORM"
            )["dynamics_identity_id"],
            "offline_observation_count": OFFLINE_OBSERVATION_COUNT,
            "additional_model_acquisition_observation_budget": 0,
            "factored_state_action_rows_serialized_or_persisted": False,
            "strict_identity_match_required_before_operator_access": True,
            "identity_match_not_sufficient_for_route_certificate": True,
        },
        "route_protocol": {
            "abstract_route_requires_strict_root_interval_dominance": True,
            "certificate_failure_route": "COLD_EXACT_DIRECT_GROUND_FALLBACK",
            "ground_transition_access_before_certificate_freeze": False,
            "fallback_only_after_certificate_failure": True,
            "matched_cold_direct_for_abstract_route_lane": "EVALUATION_ONLY",
            "selected_action_exact_value_and_loss_equivalence_required": True,
        },
        "accounting_profiles": profiles,
        "native_accounting_topology": {
            "campaign_build_common_vector_count": 1,
            "episode_worker_common_vector_count": EPISODE_WORKER_COUNT,
            "per_decision_certificate_common_vector_count": 1,
            "per_failed_certificate_direct_fallback_vector_count": 1,
            "per_abstract_decision_evaluation_vector_count": 1,
            "failed_certificate_common_and_fallback_vectors_are_distinct": True,
            "all_required_counter_paths_explicit_in_every_work_vector": True,
            "required_native_zero_observed_not_inferred": True,
            "counter_record_to_work_vector_to_comparison_vector_required": True,
            "evaluation_vector_excluded_from_operational_route_sum": True,
            "occurrence_sum_preserves_original_vector_ids": True,
        },
        "shared_resource_receipt_contract": {
            "required_paths": [
                "common.hash_invocations",
                "common.integrity_checks",
                "common.protocol_checks",
                "io.mounted_bytes_peak",
                "io.output_bytes",
                "io.read_bytes",
                "io.staged_bytes",
                "memory.working_bytes_peak",
                "process.launches",
            ],
            "same_window_owner_bound_measurement_required": True,
            "process_launches_charged_to_episode_worker_common_vectors": True,
            "worker_launch_allocation_rule": "ONE_LAUNCH_PER_EPISODE_WORKER",
            "read_and_staged_bytes_use_exact_wrapped_traffic": True,
            "output_bytes_use_exact_fixed_point": True,
            "mounted_and_working_bytes_use_verified_peak_or_preregistered_upper": True,
            "hash_invocations_count_each_actual_content_or_tape_hash": True,
        },
        "fallback_counter_semantics": {
            "fallback.states_expanded": (
                "UNIQUE_BOARD_STATUS_REMAINING_NONTERMINAL_SUBPROBLEMS_SOLVED"
            ),
            "fallback.actions_evaluated": (
                "EXACT_STATE_ACTION_STAGE_EVALUATION_INVOCATIONS"
            ),
            "fallback.ground_steps": (
                "ACTUAL_GROUND_STEP_CALLS_PER_STATE_ACTION_STAGE_EVALUATION"
            ),
            "fallback.outcome_rows": (
                "ACTUAL_EXACT_GROUND_OUTCOMES_ITERATED_ACROSS_ALL_CALLS"
            ),
            "fallback.bellman_backups": (
                "EXACT_STATE_ACTION_STAGE_BELLMAN_BACKUP_INVOCATIONS"
            ),
            "unique_ground_row_summary_is_diagnostic_not_actual_call_count": True,
        },
        "abstract_counter_semantics": {
            "common.abstract_bellman_backups": (
                "FACTORED_STATE_ACTION_INTERVAL_BELLMAN_BACKUPS"
            ),
            "common.abstract_audit_obligations": (
                "STRICT_ROOT_DOMINANCE_AUDIT_OBLIGATIONS"
            ),
            "closed_subproof_cache_hits_are_diagnostic_only": True,
        },
        "required_gates": {
            "producer_free_semantic_verifier": True,
            "counter_record_schema_verifier": True,
            "work_vector_completeness_verifier": True,
            "actual_projection_verifier": True,
            "shared_receipt_verifier": True,
            "output_fixed_point_verifier": True,
        },
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "native_counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "accounted_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AccountedPreregistrationV12:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("accounted preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("accounted preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "accounted_preregistration_id"
        }
        if (
            document.get("accounted_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("accounted preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("accounted preregistration is not an object")
        return document


def freeze_standard_2048_accounted_preregistration_v12(
) -> Standard2048AccountedPreregistrationV12:
    document = _document()
    if document["accounted_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen accounted preregistration identity changed")
    return Standard2048AccountedPreregistrationV12(
        _ISSUER,
        canonical_json_bytes(document),
        document["accounted_preregistration_id"],
    )


def verify_standard_2048_accounted_preregistration_v12(
    value: Standard2048AccountedPreregistrationV12,
) -> Standard2048AccountedPreregistrationV12:
    if type(value) is not Standard2048AccountedPreregistrationV12:
        _fail("verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("accounted preregistration differs from frozen semantics")
    return value


__all__ = (
    "ConstructionK7Standard2048AccountedPreregistrationV12Error",
    "EPISODE_WORKER_COUNT",
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "OFFLINE_OBSERVATION_COUNT",
    "PLANNING_HORIZON",
    "PREREGISTERED_EPISODE_SEEDS",
    "PREREGISTERED_INITIAL_BOARDS",
    "PREREGISTRATION_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "Standard2048AccountedPreregistrationV12",
    "freeze_standard_2048_accounted_preregistration_v12",
    "verify_standard_2048_accounted_preregistration_v12",
)
