"""Outcome-free Gate for long real-start reuse of the V22 expression model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as v12
from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as v13
from acfqp import construction_k7_standard_2048_long_episode_preregistration_v11 as v11
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CAMPAIGN_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CERTIFICATE_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_EPISODE_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_PREREGISTRATION_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_SOURCE_BINDING_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_VERIFICATION_V23_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "23.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.182"
PROFILE_KEY = "construction_k7_standard_2048_expression_long_real_start_v23"
PREREGISTRATION_ID = "267dbb02e3e1b44a59d158b3e0c5351cdf11cb2b0256cd9c51cf459fd7408cfb"
V22_CAMPAIGN_ID = "85a0f59d0751dfcad87517ed8167d66943d4be0ab9159f78aeaaef7f85923c3e"
V22_VERIFICATION_ID = "6b60d2e7d4585716784a6b9a93c7511f96de2f4742ada0d61d6e1ec78aa2e7b2"
V22_PROOF_ID = "06f9585ee717daf391f51a0b36491f2735bc590bb8ed354c2578d86f89856b94"
V22_WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
V22_TARGET_KERNEL_ID = "9c40dc9f4a33d2f8bdb008aad5af3fc43be228c7fb964cf137c53af03e962eb5"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 32
COLD_EVALUATION_CHECKPOINTS = (0, 15, 31)
INITIAL_BOARDS = (
    (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0),
)
EPISODE_SEEDS = tuple(
    f"standard-2048-v182-expression-long-real-start-{index:02d}-20260813"
    for index in range(len(INITIAL_BOARDS))
)
FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_PREREGISTRATION_V23_DOMAIN,
    "source_binding": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_SOURCE_BINDING_V23_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CERTIFICATE_V23_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_EPISODE_V23_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CAMPAIGN_V23_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_VERIFICATION_V23_DOMAIN,
}


class ConstructionK7Standard2048ExpressionLongPreregistrationV23Error(ValueError):
    """The V22 binding, long workload, cache, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionLongPreregistrationV23Error(message)


def _orbit(board: tuple[int, ...]) -> tuple[int, ...]:
    return canonicalize_state_v1(state_from_board_v1(board))[0].board


def _freshness() -> dict[str, Any]:
    predecessor = tuple(v11.PREREGISTERED_INITIAL_BOARDS) + tuple(
        v12.PREREGISTERED_INITIAL_BOARDS
    ) + tuple(v13.TARGET_INITIAL_BOARDS)
    old = {_orbit(tuple(board)) for board in predecessor}
    new = tuple(_orbit(board) for board in INITIAL_BOARDS)
    return {
        "comparison_workloads": ["V11", "V12", "V13"],
        "predecessor_orbit_count": len(old),
        "target_orbit_count": len(new),
        "target_orbits_pairwise_distinct": len(set(new)) == len(new),
        "target_orbits_disjoint_from_v11_v12_v13": not old.intersection(new),
    }


def _document() -> dict[str, Any]:
    freshness = _freshness()
    if not (
        freshness["target_orbits_pairwise_distinct"]
        and freshness["target_orbits_disjoint_from_v11_v12_v13"]
    ):
        _fail("long real-start board identities are not fresh")
    payload = {
        "schema": "acfqp.standard_2048_expression_long_preregistration.v23",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_v22_predecessor": {
            "campaign_id": V22_CAMPAIGN_ID,
            "independent_verification_id": V22_VERIFICATION_ID,
            "exact_expression_proof_id": V22_PROOF_ID,
            "world_model_id": V22_WORLD_MODEL_ID,
            "target_kernel_id": V22_TARGET_KERNEL_ID,
            "expression_ast": {
                "operator": "COUNT_EQ",
                "vector_source": "POST_SWIPE_BOARD_RANKS",
                "constant": 1,
            },
            "threshold": 2,
            "base_probability": {"numerator": 1, "denominator": 10},
            "override_probability": {"numerator": 3, "denominator": 20},
            "world_model_immutable_during_long_workload": True,
        },
        "long_real_start_workload": {
            "initial_boards": [list(board) for board in INITIAL_BOARDS],
            "episode_seeds": list(EPISODE_SEEDS),
            "episode_count": len(INITIAL_BOARDS),
            "planning_horizon": PLANNING_HORIZON,
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_decision_count": len(INITIAL_BOARDS) * MAXIMUM_DECISIONS_PER_EPISODE,
            "exactly_two_initial_tiles": True,
            "initial_tile_ranks_within_standard_spawn_support": True,
            "early_terminal_closure_allowed": True,
            "freshness_evidence": freshness,
        },
        "persistent_proof_protocol": {
            "one_bellman_subproof_cache_per_episode": True,
            "cache_reused_across_receding_horizon_decisions": True,
            "cache_key": ["D4_CANONICAL_BOARD", "STATUS", "REMAINING_HORIZON"],
            "approximation_or_precision_reduction_allowed": False,
            "target_transition_or_probability_label_in_cache_key": False,
            "cold_evaluation_checkpoint_indices": list(COLD_EVALUATION_CHECKPOINTS),
            "cold_evaluation_lane": "STANDALONE_EVALUATION_ONLY",
        },
        "sample_tax_contract": {
            "inherited_target_probability_label_count": 4,
            "additional_model_acquisition_label_budget": 0,
            "strict_no_prior_context_label_count": 8,
            "online_execution_transitions_reported_separately": True,
            "proof_and_planning_compute_reported_separately": True,
            "labels_per_certified_decision_reported_as_exact_rational": True,
            "scalar_total_work_combination_forbidden": True,
        },
        "required_positive_conditions": [
            "ALL_REGISTERED_DECISIONS_USE_IMMUTABLE_V22_EXPRESSION_MODEL",
            "ZERO_ADDITIONAL_MODEL_ACQUISITION_LABELS",
            "ALL_CERTIFICATES_FROZEN_BEFORE_TARGET_EXECUTION",
            "ALL_CHECKPOINT_ROOT_VALUES_MATCH_COLD_TARGET_GROUND",
            "PERSISTENT_CACHE_PRESERVES_EXACT_RATIONAL_BELLMAN_VALUES",
        ],
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "long_episode_implementation_present": False,
        "additional_model_acquisition_label_count": 0,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "expression_long_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionLongPreregistrationV23:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("long expression preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("long expression preregistration bytes changed")
        payload = {
            key: value for key, value in document.items()
            if key != "expression_long_preregistration_id"
        }
        if (
            document.get("expression_long_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("long expression preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("long expression preregistration is not an object")
        return document


def freeze_standard_2048_expression_long_preregistration_v23(
) -> Standard2048ExpressionLongPreregistrationV23:
    document = _document()
    if PREREGISTRATION_ID != "0" * 64 and document["expression_long_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen long expression preregistration identity changed")
    return Standard2048ExpressionLongPreregistrationV23(
        _ISSUER,
        canonical_json_bytes(document),
        document["expression_long_preregistration_id"],
    )


def verify_standard_2048_expression_long_preregistration_v23(
    value: Standard2048ExpressionLongPreregistrationV23,
) -> Standard2048ExpressionLongPreregistrationV23:
    if type(value) is not Standard2048ExpressionLongPreregistrationV23:
        _fail("long expression preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("long expression preregistration differs from frozen semantics")
    return value


__all__ = (
    "COLD_EVALUATION_CHECKPOINTS",
    "EPISODE_SEEDS",
    "FUTURE_DOMAINS",
    "INITIAL_BOARDS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "Standard2048ExpressionLongPreregistrationV23",
    "freeze_standard_2048_expression_long_preregistration_v23",
    "verify_standard_2048_expression_long_preregistration_v23",
)
