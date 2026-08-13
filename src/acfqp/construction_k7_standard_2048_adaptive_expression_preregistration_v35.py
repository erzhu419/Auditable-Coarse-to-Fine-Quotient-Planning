"""Outcome-free Gate for certificate-triggered 2048 expression repair.

The target rank law is represented only by a content commitment here.  The
registered route may inspect target probabilities solely for raw contexts in a
previously frozen failed H3 certificate frontier.  A persistent version space
of observation-derived depth-one expression programs is reused across later
decisions and episodes; global target-table reads are forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as v12
from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as v13
from acfqp import construction_k7_standard_2048_long_episode_preregistration_v11 as v11
from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_ACQUISITION_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CANDIDATE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_COUNTER_BUNDLE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_EPISODE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_FAILURE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_GROUND_CONTROL_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_OVERLAY_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PREREGISTRATION_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "35.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.193"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_expression_local_repair_v35"
PREREGISTRATION_ID = "d2705f1b310b2f88f41799376a69f55b3355b53a54a2a103ba11e5dbf00491a9"
EXPECTED_CANONICAL_BYTE_COUNT = 8329
EXPECTED_CANONICAL_SHA256 = "3e68f1b7d47e91783a9a00dea50ca9ea1fcbaef7d613a99f78b853d17363388e"
TARGET_KERNEL_COMMITMENT_ID = (
    "e542f25f3929b78c3dd622beaf632df1fee75a775de99bead1232a8a8a936236"
)
V18_LOCAL_REPAIR_CAMPAIGN_ID = (
    "666509cc46b596fb1241fb5d066440e31547cbbd540b79f5bd535acfa3232ede"
)
V18_LOCAL_REPAIR_VERIFICATION_ID = (
    "0529828cc943310226f2643b575a0f0985c7075781630814d4c987b972a1a9db"
)
V21_EXPRESSION_CAMPAIGN_ID = (
    "264749b3f9b4bd44d289476f829b0fc88076828ae7747a2a3b6c12fb6af75d4f"
)
V21_EXPRESSION_VERIFICATION_ID = (
    "a43a70731bbc56c24bef3974256c5e1beb73a2c97aeb04336b8796f2bbe1998b"
)
V34_ACCOUNTING_PREREGISTRATION_ID = (
    "9a02a999b32b3753c4cbfc9dde0baf7b783f661e696875d5bbf97d986bbc3fc5"
)
V34_ACCOUNTED_CAMPAIGN_ID: None = None
V34_ACCOUNTING_VERIFICATION_ID: None = None
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 128
MAXIMUM_TARGET_PROBABILITY_LABELS = 12
MAXIMUM_WORKER_PROCESSES = 2
INITIAL_BOARDS = (
    (2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
EPISODE_SEEDS = tuple(
    f"standard-2048-v193-adaptive-expression-repair-{index:02d}-20260814"
    for index in range(len(INITIAL_BOARDS))
)
FUTURE_DOMAINS = {
    "target": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN,
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PREREGISTRATION_V35_DOMAIN,
    "failure": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_FAILURE_V35_DOMAIN,
    "acquisition": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_ACQUISITION_V35_DOMAIN,
    "candidate": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CANDIDATE_V35_DOMAIN,
    "overlay": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_OVERLAY_V35_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN,
    "ground_control": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_GROUND_CONTROL_V35_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_EPISODE_V35_DOMAIN,
    "counter_bundle": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_COUNTER_BUNDLE_V35_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
}


class ConstructionK7Standard2048AdaptiveExpressionPreregistrationV35Error(
    ValueError
):
    """The commitment, workload, recovery protocol, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveExpressionPreregistrationV35Error(
        message
    )


def _orbit(board: tuple[int, ...]) -> tuple[int, ...]:
    return canonicalize_state_v1(state_from_board_v1(board))[0].board


def _freshness() -> dict[str, Any]:
    old_boards = (
        tuple(v11.PREREGISTERED_INITIAL_BOARDS)
        + tuple(v12.PREREGISTERED_INITIAL_BOARDS)
        + tuple(v13.TARGET_INITIAL_BOARDS)
        + tuple(v23.INITIAL_BOARDS)
    )
    old_orbits = {_orbit(tuple(board)) for board in old_boards}
    new_orbits = tuple(_orbit(board) for board in INITIAL_BOARDS)
    return {
        "comparison_workloads": ["V11", "V12", "V13", "V23"],
        "predecessor_orbit_count": len(old_orbits),
        "target_orbit_count": len(new_orbits),
        "target_orbits_pairwise_distinct": len(set(new_orbits)) == len(new_orbits),
        "target_orbits_disjoint_from_predecessors": not old_orbits.intersection(
            new_orbits
        ),
    }


def _document() -> dict[str, Any]:
    freshness = _freshness()
    if not (
        freshness["target_orbits_pairwise_distinct"]
        and freshness["target_orbits_disjoint_from_predecessors"]
    ):
        _fail("adaptive-expression initial-board identities are not fresh")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_preregistration.v35",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v18_local_repair_campaign_id": V18_LOCAL_REPAIR_CAMPAIGN_ID,
            "v18_local_repair_verification_id": V18_LOCAL_REPAIR_VERIFICATION_ID,
            "v21_expression_campaign_id": V21_EXPRESSION_CAMPAIGN_ID,
            "v21_expression_verification_id": V21_EXPRESSION_VERIFICATION_ID,
            "v34_accounting_preregistration_id": V34_ACCOUNTING_PREREGISTRATION_ID,
            "v34_accounted_campaign_id": {
                "kind": "PENDING_PREEXECUTION_BINDING",
                "reason": "V34_REGISTERED_RUN_ACTIVE_AT_V35_PREREGISTRATION_FREEZE",
            },
            "v34_accounting_verification_id": {
                "kind": "PENDING_PREEXECUTION_BINDING",
                "reason": "V34_INDEPENDENT_VERIFICATION_MUST_PRECEDE_TARGET_EXECUTION",
            },
            "v34_full_accounting_must_verify_before_target_execution": True,
        },
        "target_commitment": {
            "target_domain": FUTURE_DOMAINS["target"],
            "target_kernel_commitment_id": TARGET_KERNEL_COMMITMENT_ID,
            "target_semantics_document_present": False,
            "target_source_present": False,
            "target_probability_table_present": False,
            "commitment_precedes_reveal_in_git_history": True,
            "reveal_must_recompute_exact_commitment": True,
            "experimenter_cognitive_blinding_claimed": False,
        },
        "fresh_long_segment": {
            "initial_boards": [list(board) for board in INITIAL_BOARDS],
            "episode_seeds": list(EPISODE_SEEDS),
            "episode_count": len(INITIAL_BOARDS),
            "planning_horizon": PLANNING_HORIZON,
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_decision_count": (
                len(INITIAL_BOARDS) * MAXIMUM_DECISIONS_PER_EPISODE
            ),
            "exactly_two_initial_tiles": True,
            "initial_ranks_within_observed_spawn_support": True,
            "early_terminal_closure_allowed": True,
            "identity_bound_checkpoint_continuation_allowed": True,
            "freshness_evidence": freshness,
        },
        "observation_derived_structural_prior": {
            "spawn_support_and_position_program_source": "V2_V3_OBSERVATION_ARCHIVES",
            "support_program_and_position_law_reused_without_target_labels": True,
            "generic_expression_grammar_source": "V21_VERIFIED_RAW_CONTEXT_GRAMMAR",
            "raw_vector_sources": [
                "PRE_BOARD_RANKS",
                "POST_SWIPE_BOARD_RANKS",
            ],
            "vector_reducers": [
                "COUNT_EQ_OBSERVED_CELL_VALUE",
                "MAX",
                "SUM",
                "DISTINCT_NONZERO_COUNT",
                "ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT",
            ],
            "raw_scalar_sources": ["MERGE_SCORE", "ACTION_ORDINAL"],
            "expression_composition_depth": 1,
            "constants_generated_only_from_frozen_raw_context_values": True,
            "thresholds_generated_only_from_frozen_expression_values": True,
            "nonbase_probabilities_generated_only_from_acquired_labels": True,
            "named_target_feature_supplied": False,
            "target_specific_program_candidate_supplied": False,
        },
        "certificate_triggered_recovery": {
            "provisional_model_may_plan_but_cannot_certify_uncovered_contexts": True,
            "h3_raw_frontier_frozen_before_any_target_probability_query": True,
            "failure_artifact_required_before_acquisition": True,
            "query_context_must_belong_to_failed_certificate_frontier": True,
            "query_selection_rule": (
                "MINIMIZE_MAXIMUM_REMAINING_LOCAL_PREDICTION_BUCKET_"
                "THEN_CANONICAL_CONTEXT"
            ),
            "candidate_elimination_uses_exact_rational_equality": True,
            "candidate_universe_frozen_at_first_failed_frontier": True,
            "later_frontiers_may_filter_but_not_expand_candidate_universe": True,
            "local_certificate_rule": (
                "ALL_SURVIVING_PROGRAMS_PREDICT_IDENTICAL_PROBABILITY_ON_"
                "EVERY_REACHABLE_H3_FRONTIER_CONTEXT"
            ),
            "global_unique_program_required": False,
            "persistent_overlay_reused_across_decisions_and_episodes": True,
            "new_frontier_disagreement_triggers_new_failure_before_query": True,
            "maximum_target_probability_labels": MAXIMUM_TARGET_PROBABILITY_LABELS,
            "label_cap_exhaustion_route": "COLD_EXACT_GROUND_FALLBACK",
            "global_target_table_read_allowed": False,
        },
        "matched_controls": {
            "no_prior_ground_table_queries_every_distinct_first_failed_h3_context": True,
            "no_prior_control_scope": "FIRST_OPERATIONAL_CERTIFICATE_FAILURE_FRONTIER",
            "cold_exact_ground_planning_at_registered_checkpoints": True,
            "same_boards_seeds_horizon_and_terminal_rules": True,
            "control_target_labels_never_feed_operational_overlay": True,
            "control_and_cold_ground_are_evaluation_lane_only": True,
        },
        "postproposal_reveal_and_proof": {
            "preproposal_target_access_limited_to_black_box_probability_labels": True,
            "target_semantics_document_or_formula_read_before_first_overlay_proposal_freeze": False,
            "target_commitment_recomputed_before_semantic_proof": True,
            "selected_program_compared_to_revealed_exact_semantics": True,
            "proof_failure_prevents_world_model_authority": True,
            "proof_work_reported_separately_from_probability_labels": True,
            "proved_world_model_reused_without_further_target_table_reads": True,
            "later_plan_certificates_bind_exact_program_proof_id": True,
        },
        "sample_tax_contract": {
            "adaptive_target_probability_label_cap": MAXIMUM_TARGET_PROBABILITY_LABELS,
            "positive_condition": (
                "ALL_OPERATIONAL_CERTIFICATES_REPLAY_AND_ADAPTIVE_LABEL_COUNT_"
                "STRICTLY_LESS_THAN_MATCHED_NO_PRIOR_LABEL_COUNT"
            ),
            "model_labels_execution_transitions_and_planning_compute_separate": True,
            "meta_prior_may_select_grammar_and_query_order_only": True,
            "meta_prior_may_not_supply_target_program_or_certificate": True,
            "ood_or_empty_version_space_forces_cold_ground_fallback": True,
            "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
            "scalar_total_work_saving_claimed": False,
        },
        "native_accounting_contract": {
            "counter_registry": "CONSTRUCTION_COUNTER_REGISTRY_V9",
            "counter_record_to_work_vector_to_comparison_vector_required": True,
            "all_required_operational_leaves_emit_native_zero": True,
            "nine_shared_resource_paths_measured": True,
            "evaluation_lane_excluded_from_operational_comparison": True,
            "failure_acquisition_overlay_certificate_and_execution_separate": True,
            "maximum_worker_processes": MAXIMUM_WORKER_PROCESSES,
        },
        "required_positive_conditions": [
            "V34_FULL_ACCOUNTING_VERIFIES_BEFORE_EXECUTION",
            "EVERY_TARGET_QUERY_HAS_A_PRECEDING_FAILED_FRONTIER_CERTIFICATE",
            "EVERY_OPERATIONAL_PLAN_HAS_A_LOCAL_EXACT_CERTIFICATE",
            "FIRST_OVERLAY_PROPOSAL_PRECEDES_TARGET_REVEAL_AND_EXACT_PROOF",
            "PERSISTENT_OVERLAY_IS_REUSED_WITHOUT_TARGET_TABLE_ACCESS",
            "MATCHED_NO_PRIOR_AND_COLD_GROUND_CONTROLS_REPLAY",
            "ALL_OPERATIONAL_AND_EVALUATION_WORK_IS_NATIVELY_ACCOUNTED",
        ],
        "outcome_fields_present": False,
        "target_revealed": False,
        "target_execution_performed": False,
        "target_probability_label_count": 0,
        "certificate_failure_count": 0,
        "overlay_program_count": 0,
        "certificate_count": 0,
        "full_standard_2048_game_claimed": False,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "adaptive_expression_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveExpressionPreregistrationV35:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("adaptive-expression preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("adaptive-expression preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_expression_preregistration_id"
        }
        if (
            document.get("adaptive_expression_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("adaptive-expression preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive-expression preregistration is not an object")
        return document


def freeze_standard_2048_adaptive_expression_preregistration_v35(
) -> Standard2048AdaptiveExpressionPreregistrationV35:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["adaptive_expression_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen adaptive-expression preregistration changed")
    return Standard2048AdaptiveExpressionPreregistrationV35(
        _ISSUER, raw, identity
    )


def verify_standard_2048_adaptive_expression_preregistration_v35(
    value: Standard2048AdaptiveExpressionPreregistrationV35,
) -> Standard2048AdaptiveExpressionPreregistrationV35:
    if type(value) is not Standard2048AdaptiveExpressionPreregistrationV35:
        _fail("adaptive-expression verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("adaptive-expression preregistration semantics changed")
    return value


__all__ = (
    "EPISODE_SEEDS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "INITIAL_BOARDS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "MAXIMUM_TARGET_PROBABILITY_LABELS",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "Standard2048AdaptiveExpressionPreregistrationV35",
    "TARGET_KERNEL_COMMITMENT_ID",
    "freeze_standard_2048_adaptive_expression_preregistration_v35",
    "verify_standard_2048_adaptive_expression_preregistration_v35",
)
