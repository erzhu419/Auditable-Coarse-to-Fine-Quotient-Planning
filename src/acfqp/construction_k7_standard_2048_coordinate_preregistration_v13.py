"""Outcome-free Gate for observation-derived 2048 planning coordinates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as v12
from acfqp import construction_k7_standard_2048_long_episode_preregistration_v11 as v11
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CAMPAIGN_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CANDIDATE_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_PREREGISTRATION_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_VERIFICATION_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PARTIAL_QUOTIENT_MODEL_V13_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "13.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.172"
PROFILE_KEY = "construction_k7_standard_2048_observation_derived_coordinates_v13"
PREREGISTRATION_ID = (
    "568b748cde1ae75c36e66cf6883c012ee83cf3c316930e21d0e95b8f65224680"
)
PLANNING_HORIZON = 3
SOURCE_TRANSITION_OBSERVATION_COUNT = 512
VALIDATION_TRANSITION_OBSERVATION_COUNT = 256
MAXIMUM_DECISIONS_PER_EPISODE = 16
MAXIMUM_EXACT_LOCAL_ROWS_PER_DECISION = 4
MAXIMUM_EXACT_LOCAL_ROWS_CAMPAIGN = 256

SOURCE_STREAM_SEED = "standard-2048-v172-coordinate-source-20260813"
VALIDATION_STREAM_SEED = "standard-2048-v172-coordinate-validation-20260813"
TARGET_EPISODE_SEEDS = tuple(
    f"standard-2048-v172-coordinate-target-{index:02d}-20260813"
    for index in range(4)
)

TARGET_INITIAL_BOARDS = (
    (2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)

# Expressions are compiled from the public board/grid/action/transition
# relations.  The compatibility names are not supplied as learned labels.
COORDINATE_META_OPERATORS = (
    "ADJACENT_EQUAL_COUNT",
    "BOARD_D4_CANONICALIZE",
    "CARDINALITY",
    "CORNER_CLASS",
    "HISTOGRAM",
    "LEGAL_ACTION_SET",
    "MAXIMUM",
    "ORDERED_GRID_LINE_SCAN",
    "RANK_MASS",
    "ZERO_COUNT",
)
COORDINATE_CANDIDATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("empty_cell_count", ("ZERO_COUNT", "BOARD_RANKS")),
    ("rank_histogram", ("HISTOGRAM", "BOARD_RANKS")),
    ("maximum_rank", ("MAXIMUM", "BOARD_RANKS")),
    (
        "maximum_rank_corner_class",
        ("CORNER_CLASS", "MAXIMUM", "BOARD_RANKS", "GRID_RELATION"),
    ),
    (
        "adjacent_equal_pair_count",
        ("ADJACENT_EQUAL_COUNT", "BOARD_RANKS", "GRID_RELATION"),
    ),
    (
        "ordered_line_rank_signature",
        ("ORDERED_GRID_LINE_SCAN", "BOARD_RANKS", "GRID_RELATION"),
    ),
    ("legal_action_mask", ("LEGAL_ACTION_SET", "BOARD_RANKS")),
    ("rank_mass", ("RANK_MASS", "BOARD_RANKS")),
    (
        "exact_d4_board_fallback_coordinate",
        ("BOARD_D4_CANONICALIZE", "BOARD_RANKS", "GRID_RELATION"),
    ),
)

FUTURE_DOMAINS = {
    "preregistration": (
        CONSTRUCTION_K7_STANDARD_2048_COORDINATE_PREREGISTRATION_V13_DOMAIN
    ),
    "candidate": CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CANDIDATE_V13_DOMAIN,
    "basis": CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN,
    "partial_model": CONSTRUCTION_K7_STANDARD_2048_PARTIAL_QUOTIENT_MODEL_V13_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CAMPAIGN_V13_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_COORDINATE_VERIFICATION_V13_DOMAIN,
}


class ConstructionK7Standard2048CoordinatePreregistrationV13Error(ValueError):
    """The coordinate grammar, workload, or exact-recovery rule changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048CoordinatePreregistrationV13Error(message)


def _orbits(boards: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in boards
    )


def _accounting_profile_binding() -> dict[str, Any]:
    registry = registry_v8.official_counter_registry_v8()
    comparison = registry_v8.official_comparison_profile_v8(registry)
    actual = registry_v8.official_actual_projection_profile_v8(
        registry, comparison
    )
    return {
        "counter_registry_id": registry.registry_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": actual.actual_projection_profile_id,
        "required_counter_path_count": len(registry.required_paths),
        "operational_counter_path_count": len(registry.operational_leaves),
    }


def _document() -> dict[str, Any]:
    old_orbits = set(
        _orbits(
            tuple(v11.PREREGISTERED_INITIAL_BOARDS)
            + tuple(v12.PREREGISTERED_INITIAL_BOARDS)
        )
    )
    target_orbits = _orbits(TARGET_INITIAL_BOARDS)
    targets_are_fresh = (
        len(set(target_orbits)) == len(target_orbits)
        and not old_orbits.intersection(target_orbits)
    )
    payload = {
        "schema": "acfqp.standard_2048_coordinate_preregistration.v13",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v171_accounting_preregistration_id": v12.PREREGISTRATION_ID,
        "v171_outcome_or_route_counts_read_before_freeze": False,
        "source_stream_seed": SOURCE_STREAM_SEED,
        "validation_stream_seed": VALIDATION_STREAM_SEED,
        "source_and_validation_streams_are_disjoint": True,
        "source_transition_observation_count": (
            SOURCE_TRANSITION_OBSERVATION_COUNT
        ),
        "validation_transition_observation_count": (
            VALIDATION_TRANSITION_OBSERVATION_COUNT
        ),
        "source_board_generator": {
            "board_shape": [4, 4],
            "occupied_cell_count_support": [2, 12],
            "occupied_cell_count_law": "UNIFORM_INTEGER",
            "occupied_positions_law": "UNIFORM_WITHOUT_REPLACEMENT",
            "rank_support": [1, 6],
            "rank_law": "UNIFORM_INTEGER",
            "action_law": "UNIFORM_OVER_LEGAL_ACTIONS",
            "outcome_law": "STANDARD_2048_EXACT_SPAWN_LAW",
            "generator_law_or_probability_not_available_to_learner": True,
            "inactive_or_no_legal_action_board_rejected": True,
            "all_random_choices_content_addressed": True,
        },
        "coordinate_meta_operators": list(COORDINATE_META_OPERATORS),
        "coordinate_candidates": [
            {
                "candidate_ordinal": ordinal,
                "candidate_key": key,
                "compiled_expression": list(expression),
            }
            for ordinal, (key, expression) in enumerate(COORDINATE_CANDIDATES)
        ],
        "coordinate_selection_rule": {
            "enumeration_order": (
                "INCREASING_SUBSET_CARDINALITY_THEN_CANDIDATE_ORDINAL"
            ),
            "source_objective": (
                "MINIMUM_BASIS_WITH_NO_OBSERVED_TRANSITION_CONGRUENCE_"
                "CONTRADICTION"
            ),
            "heldout_acceptance": (
                "NO_VALIDATION_TRANSITION_CONGRUENCE_CONTRADICTION"
            ),
            "query_reward_value_or_policy_access_allowed": False,
            "target_episode_access_allowed": False,
            "exact_d4_coordinate_forced_into_initial_basis": False,
            "empty_basis_allowed": False,
        },
        "partial_dynamics_contract": {
            "same_coordinate_action_rows_pool_observed_successor_coordinates": True,
            "unobserved_successor_mass_retained_as_unknown": True,
            "statistical_interval_can_guide_acquisition": True,
            "statistical_interval_alone_can_issue_sound_plan_certificate": False,
            "sound_plan_certificate_requires_exact_local_obligation_closure": True,
            "exact_ground_kernel_not_read_during_basis_selection": True,
        },
        "local_refinement_protocol": {
            "initial_overlay_empty": True,
            "refinement_only_after_certificate_failure": True,
            "refinement_target": (
                "LEXICOGRAPHIC_FIRST_UNCLOSED_FAILED_BELLMAN_OBLIGATION"
            ),
            "refinement_payload": (
                "EXACT_D4_BOARD_ACTION_SUCCESSOR_SUPPORT_AND_PROBABILITY_ROW"
            ),
            "maximum_exact_local_rows_per_decision": (
                MAXIMUM_EXACT_LOCAL_ROWS_PER_DECISION
            ),
            "maximum_exact_local_rows_campaign": (
                MAXIMUM_EXACT_LOCAL_ROWS_CAMPAIGN
            ),
            "immutable_overlay_reused_across_decisions_and_episodes": True,
            "unaffected_abstract_rows_not_invalidated": True,
            "cap_exhaustion_route": "COLD_EXACT_DIRECT_GROUND_FALLBACK",
            "fallback_not_classified_as_infeasible": True,
        },
        "planning_protocol": {
            "planning_horizon": PLANNING_HORIZON,
            "primary_planning_space": "SELECTED_COORDINATE_QUOTIENT_PLUS_OVERLAY",
            "abstract_plan_attempted_before_local_ground_recovery": True,
            "local_ground_recovery_only_after_certificate_failure": True,
            "target_transition_after_route_freeze_only": True,
            "matched_cold_direct_evaluation_required": True,
            "selected_action_exact_value_and_loss_equivalence_required": True,
        },
        "target_workload": {
            "initial_boards": [list(board) for board in TARGET_INITIAL_BOARDS],
            "initial_board_d4_representatives": [
                list(board) for board in target_orbits
            ],
            "fresh_and_d4_disjoint_from_v169_and_v171": targets_are_fresh,
            "episode_seeds": list(TARGET_EPISODE_SEEDS),
            "episode_count": len(TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_decision_count": (
                len(TARGET_INITIAL_BOARDS) * MAXIMUM_DECISIONS_PER_EPISODE
            ),
            "early_terminal_closure_allowed": True,
        },
        "sample_tax_controls": {
            "matched_fixed_control_source_observation_count": 6144,
            "matched_fixed_control_validation_observation_count": 2048,
            "matched_fixed_control_total_observation_count": 8192,
            "historical_147456_observation_control_is_diagnostic_only": True,
            "strict_no_prior_control_required": True,
            "coordinate_source_and_validation_count": (
                SOURCE_TRANSITION_OBSERVATION_COUNT
                + VALIDATION_TRANSITION_OBSERVATION_COUNT
            ),
            "local_exact_rows_charged_separately": True,
            "target_transitions_charged_separately": True,
            "sample_count_not_combined_with_compute_or_bytes_as_scalar": True,
            "positive_sample_tax_result_requires_exact_action_equivalence": True,
        },
        "accounting_profile_binding": _accounting_profile_binding(),
        "required_outcome_classification": (
            "POSITIVE_OR_NEGATIVE_REGISTERED_COORDINATE_SYNTHESIS_RESULT"
        ),
        "outcome_fields_present": False,
        "source_or_validation_observations_materialized": False,
        "coordinate_basis_selected": False,
        "partial_quotient_model_constructed": False,
        "target_execution_performed": False,
        "ground_refinement_performed": False,
        "sample_tax_reduction_claimed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_world_model_synthesis_claimed": False,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "coordinate_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048CoordinatePreregistrationV13:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("coordinate preregistration is not issuer-created")
        try:
            document = loads_canonical_json(self.canonical_bytes)
        except (TypeError, ValueError) as error:
            raise ConstructionK7Standard2048CoordinatePreregistrationV13Error(
                "coordinate preregistration is not canonical JSON"
            ) from error
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("coordinate preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "coordinate_preregistration_id"
        }
        if (
            document.get("coordinate_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("coordinate preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("coordinate preregistration is not an object")
        return document


def freeze_standard_2048_coordinate_preregistration_v13(
) -> Standard2048CoordinatePreregistrationV13:
    document = _document()
    if document["coordinate_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen coordinate preregistration identity changed")
    return Standard2048CoordinatePreregistrationV13(
        _ISSUER,
        canonical_json_bytes(document),
        document["coordinate_preregistration_id"],
    )


def verify_standard_2048_coordinate_preregistration_v13(
    value: Standard2048CoordinatePreregistrationV13,
) -> Standard2048CoordinatePreregistrationV13:
    if type(value) is not Standard2048CoordinatePreregistrationV13:
        _fail("coordinate preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("coordinate preregistration differs from frozen semantics")
    return value


__all__ = (
    "COORDINATE_CANDIDATES",
    "COORDINATE_META_OPERATORS",
    "ConstructionK7Standard2048CoordinatePreregistrationV13Error",
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "PREREGISTRATION_ID",
    "Standard2048CoordinatePreregistrationV13",
    "TARGET_INITIAL_BOARDS",
    "freeze_standard_2048_coordinate_preregistration_v13",
    "verify_standard_2048_coordinate_preregistration_v13",
)
