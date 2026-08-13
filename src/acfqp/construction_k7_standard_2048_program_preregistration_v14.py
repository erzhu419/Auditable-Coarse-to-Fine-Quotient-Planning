"""Outcome-free Gate for observation-proposed, proof-checked 2048 programs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as v13
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CAMPAIGN_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CANDIDATE_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PREREGISTRATION_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PROGRAM_VERIFICATION_V14_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "14.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.173"
PROFILE_KEY = "construction_k7_standard_2048_observation_proposed_program_v14"
PREREGISTRATION_ID = "948020ab2f6ef639899a0913ce68b7cb2573eb8e8d4b6edd07c7550ff08aa62e"

V13_COORDINATE_BASIS_ID = "920eb108ddfc9a5ecefe3c8d38629534667ae740f908c376fbd419ae6cd943ea"
V13_PARTIAL_QUOTIENT_MODEL_ID = "9534055b61a93984f8066e3eee2dc0018847c6b3ca4c946ac731ab86ef94f081"
V10_META_PRIOR_ROUTE_CAMPAIGN_ID = "6838c6ed5764d1f514247eee98f2d6d7a3992e3a29c0a4ac85ba8182b0afdcd0"
LINE_RANK_MINIMUM = 0
LINE_RANK_MAXIMUM = 19
EXHAUSTIVE_LINE_INPUT_COUNT = (LINE_RANK_MAXIMUM + 1) ** 4

PROGRAM_CANDIDATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "COMPACT_NONZERO_WITHOUT_MERGE",
        ("ORIENT_ACTION_LINES", "COMPACT_NONZERO", "ZERO_PAD", "RECOMBINE"),
    ),
    (
        "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP",
        (
            "ORIENT_ACTION_LINES",
            "COMPACT_NONZERO",
            "LEFT_GREEDY_EQUAL_ADJACENT_MERGE",
            "SKIP_MERGED_PAIR",
            "ZERO_PAD",
            "RECOMBINE",
        ),
    ),
    (
        "COMPACT_THEN_CASCADE_EQUAL_MERGES_TO_FIXED_POINT",
        (
            "ORIENT_ACTION_LINES",
            "COMPACT_NONZERO",
            "CASCADE_EQUAL_ADJACENT_MERGE_TO_FIXED_POINT",
            "ZERO_PAD",
            "RECOMBINE",
        ),
    ),
    (
        "MERGE_ONLY_ORIGINALLY_ADJACENT_THEN_COMPACT",
        (
            "ORIENT_ACTION_LINES",
            "LEFT_GREEDY_ORIGINALLY_ADJACENT_NONZERO_MERGE",
            "SKIP_MERGED_PAIR",
            "COMPACT_NONZERO",
            "ZERO_PAD",
            "RECOMBINE",
        ),
    ),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PREREGISTRATION_V14_DOMAIN,
    "candidate": CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CANDIDATE_V14_DOMAIN,
    "proposal": CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN,
    "line_proof": CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN,
    "world_model": CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CAMPAIGN_V14_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_PROGRAM_VERIFICATION_V14_DOMAIN,
}


class ConstructionK7Standard2048ProgramPreregistrationV14Error(ValueError):
    """The program grammar, proof obligation, workload, or Gate changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ProgramPreregistrationV14Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_program_preregistration.v14",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v13_coordinate_preregistration_id": v13.PREREGISTRATION_ID,
        "v13_coordinate_basis_id": V13_COORDINATE_BASIS_ID,
        "v13_partial_quotient_model_id": V13_PARTIAL_QUOTIENT_MODEL_ID,
        "v10_meta_prior_route_campaign_id": V10_META_PRIOR_ROUTE_CAMPAIGN_ID,
        "v10_line_factoring_is_frozen_predecessor_grammar_only": True,
        "v13_target_transition_or_route_outcomes_read_before_freeze": False,
        "observation_evidence": {
            "source_archive_id": "4347a3cd4782ed9c3f23dc46551cde2d686d24d1b1715df67349489afc6a3f5e",
            "validation_archive_id": "f24ab566a50cc73d4c89fb84941913ce2205e05a9947987f53adad2f0b8d927c",
            "source_observation_count": 512,
            "validation_observation_count": 256,
            "new_observations_acquired_for_program_proposal": 0,
            "spawned_cell_and_rank_removed_before_swipe_program_scoring": True,
            "source_selects_program": True,
            "validation_can_accept_or_reject_but_not_reselect": True,
        },
        "program_candidates": [
            {
                "candidate_ordinal": ordinal,
                "candidate_key": key,
                "instruction_sequence": list(instructions),
            }
            for ordinal, (key, instructions) in enumerate(PROGRAM_CANDIDATES)
        ],
        "program_selection_rule": {
            "source_objective": "MINIMUM_MISMATCH_COUNT_THEN_CANDIDATE_ORDINAL",
            "required_unique_zero_mismatch_source_candidate": True,
            "required_zero_mismatch_heldout_validation": True,
            "target_episode_reward_value_policy_access_allowed": False,
            "proposal_has_certificate_authority": False,
        },
        "exhaustive_deterministic_proof": {
            "line_length": 4,
            "line_rank_minimum": LINE_RANK_MINIMUM,
            "line_rank_maximum": LINE_RANK_MAXIMUM,
            "exhaustive_line_input_count": EXHAUSTIVE_LINE_INPUT_COUNT,
            "reference": "PUBLIC_STANDARD_2048_SWIPE_BOARD_V1_ISOLATED_LEFT_LINE",
            "required_candidate_mismatch_count": 0,
            "proof_cached_and_reused_across_all_target_decisions": True,
            "proof_evaluations_are_compute_not_transition_observation_samples": True,
            "proof_scope_is_bounded_standard_4X4_RANK_0_THROUGH_19": True,
        },
        "factored_world_model_contract": {
            "verified_component": "DETERMINISTIC_WHOLE_BOARD_SWIPE",
            "unverified_component": "STOCHASTIC_SPAWN_SUPPORT_AND_PROBABILITY",
            "spawn_component_retained_as_unknown_until_exact_local_closure": True,
            "program_proof_alone_can_issue_sound_plan_certificate": False,
            "exact_local_obligation_closure_still_required": True,
            "immutable_exact_overlay_reused_across_decisions_and_episodes": True,
        },
        "target_workload": {
            "initial_boards": [list(board) for board in v13.TARGET_INITIAL_BOARDS],
            "episode_seeds": list(v13.TARGET_EPISODE_SEEDS),
            "episode_count": len(v13.TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": v13.MAXIMUM_DECISIONS_PER_EPISODE,
            "planning_horizon": v13.PLANNING_HORIZON,
            "target_execution_performed": False,
        },
        "local_recovery_contract": {
            "only_after_certificate_failure": True,
            "exact_row_payload": "D4_BOARD_ACTION_SPAWN_SUPPORT_AND_PROBABILITY",
            "maximum_exact_rows_per_decision": v13.MAXIMUM_EXACT_LOCAL_ROWS_PER_DECISION,
            "maximum_exact_rows_campaign": v13.MAXIMUM_EXACT_LOCAL_ROWS_CAMPAIGN,
            "cap_exhaustion_route": "COLD_EXACT_DIRECT_GROUND_FALLBACK",
            "fallback_cap_exhaustion_is_not_infeasibility": True,
        },
        "sample_tax_comparison": {
            "program_arm_offline_transition_observation_count": 768,
            "matched_fixed_control_offline_transition_observation_count": 8192,
            "registered_offline_observation_difference": 7424,
            "exhaustive_line_compute_evaluations": EXHAUSTIVE_LINE_INPUT_COUNT,
            "compute_and_observation_counts_reported_separately": True,
            "positive_sample_tax_claim_requires_target_action_equivalence": True,
            "total_operational_work_saving_claimed": False,
        },
        "outcome_fields_present": False,
        "program_selected": False,
        "exhaustive_line_proof_run": False,
        "factored_world_model_constructed": False,
        "target_execution_performed": False,
        "sample_tax_reduction_claimed": False,
        "open_ended_program_invention_claimed": False,
        "broad_world_model_synthesis_claimed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "program_preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ProgramPreregistrationV14:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("program preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("program preregistration bytes changed")
        payload = {key: value for key, value in document.items() if key != "program_preregistration_id"}
        if (
            document.get("program_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("program preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("program preregistration is not an object")
        return document


def freeze_standard_2048_program_preregistration_v14(
) -> Standard2048ProgramPreregistrationV14:
    document = _document()
    if document["program_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen program preregistration identity changed")
    return Standard2048ProgramPreregistrationV14(
        _ISSUER,
        canonical_json_bytes(document),
        document["program_preregistration_id"],
    )


def verify_standard_2048_program_preregistration_v14(
    value: Standard2048ProgramPreregistrationV14,
) -> Standard2048ProgramPreregistrationV14:
    if type(value) is not Standard2048ProgramPreregistrationV14:
        _fail("program preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("program preregistration differs from frozen semantics")
    return value


__all__ = (
    "EXHAUSTIVE_LINE_INPUT_COUNT",
    "FUTURE_DOMAINS",
    "LINE_RANK_MAXIMUM",
    "LINE_RANK_MINIMUM",
    "PREREGISTRATION_ID",
    "PROGRAM_CANDIDATES",
    "Standard2048ProgramPreregistrationV14",
    "freeze_standard_2048_program_preregistration_v14",
    "verify_standard_2048_program_preregistration_v14",
)
