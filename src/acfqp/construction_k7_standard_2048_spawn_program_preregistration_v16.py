"""Outcome-free Gate for observation-proposed standard-2048 spawn dynamics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CANDIDATE_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PREREGISTRATION_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PROPOSAL_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_SUPPORT_PROOF_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_VERIFICATION_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_WORLD_MODEL_V16_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "16.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.175"
PROFILE_KEY = "construction_k7_standard_2048_observation_proposed_spawn_v16"
PREREGISTRATION_ID = "9b868b003846c0ad0a966537922ef621ab5c1166533b00cfb02187d78399300a"

V14_PROGRAM_PROPOSAL_ID = "7164a54cad13246a55c891a71a1a879b15be7116fbcb49998e8b7619f9c0ce72"
V14_PROGRAM_LINE_PROOF_ID = "3960ef8c496eb00a81d08bf29243ee7f5cd5f50f5302f2b91cb836618bc322b6"
V14_FACTORED_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
V15_EXACT_FACTOR_CAMPAIGN_ID = "0c9be0ddd9895dd9162b6408493d56a16ae4f9ed70591c41117781701a697645"
V15_INDEPENDENT_VERIFICATION_ID = "33777be770b7ae8eb45c4d22b2a8c5226dde4a443f2381ea402afd09826f7180"
STANDARD_2048_SOURCE_SHA256 = "0fabdec281cc94c53bceef37bdb5336da45c71c7339370d25d7dfa076aa7154c"
STANDARD_2048_SOURCE_BYTE_COUNT = 14739

SOURCE_OBSERVATION_COUNT = 256
VALIDATION_OBSERVATION_COUNT = 128
JOINT_SWIPE_AND_SPAWN_OBSERVATION_COUNT = 768 + 256 + 128
MATCHED_FIXED_OBSERVATION_CONTROL_COUNT = 8192
REGISTERED_OBSERVATION_DIFFERENCE = (
    MATCHED_FIXED_OBSERVATION_CONTROL_COUNT
    - JOINT_SWIPE_AND_SPAWN_OBSERVATION_COUNT
)
SOURCE_STREAM_SEED = "standard-2048-v175-spawn-source-20260813"
VALIDATION_STREAM_SEED = "standard-2048-v175-spawn-validation-20260813"

CELL_LAWS = (
    "UNIFORM_OVER_EMPTY_CELLS",
    "FIRST_EMPTY_CELL_ONLY",
    "LAST_EMPTY_CELL_ONLY",
    "CELL_INDEX_PLUS_ONE_WEIGHTED",
    "CORNER_EMPTY_CELL_DOUBLE_WEIGHTED",
)
RANK_TWO_PROBABILITIES = (
    (0, 1),
    (1, 16),
    (1, 10),
    (1, 8),
    (1, 4),
)
SPAWN_PROGRAM_CANDIDATES = tuple(
    (
        f"{cell_law}__RANK_TWO_{numerator}_OVER_{denominator}",
        cell_law,
        numerator,
        denominator,
    )
    for cell_law in CELL_LAWS
    for numerator, denominator in RANK_TWO_PROBABILITIES
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PREREGISTRATION_V16_DOMAIN,
    "candidate": CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CANDIDATE_V16_DOMAIN,
    "observation_archive": CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V16_DOMAIN,
    "proposal": CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PROPOSAL_V16_DOMAIN,
    "support_proof": CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_SUPPORT_PROOF_V16_DOMAIN,
    "world_model": CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_WORLD_MODEL_V16_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_VERIFICATION_V16_DOMAIN,
}


class ConstructionK7Standard2048SpawnProgramPreregistrationV16Error(ValueError):
    """The fresh streams, candidate grammar, proof, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SpawnProgramPreregistrationV16Error(message)


def _document() -> dict[str, Any]:
    candidates = [
        {
            "candidate_ordinal": ordinal,
            "candidate_key": key,
            "cell_probability_law": cell_law,
            "rank_one_probability": {
                "numerator": denominator - numerator,
                "denominator": denominator,
            },
            "rank_two_probability": {
                "numerator": numerator,
                "denominator": denominator,
            },
            "rank_independent_of_cell_given_candidate": True,
            "outcome_order": "ASCENDING_CELL_THEN_ASCENDING_RANK",
        }
        for ordinal, (key, cell_law, numerator, denominator) in enumerate(
            SPAWN_PROGRAM_CANDIDATES
        )
    ]
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_preregistration.v16",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v14_program_proposal_id": V14_PROGRAM_PROPOSAL_ID,
        "v14_program_line_proof_id": V14_PROGRAM_LINE_PROOF_ID,
        "v14_factored_world_model_id": V14_FACTORED_WORLD_MODEL_ID,
        "v15_exact_factor_campaign_id": V15_EXACT_FACTOR_CAMPAIGN_ID,
        "v15_independent_verification_id": V15_INDEPENDENT_VERIFICATION_ID,
        "v15_result_frozen_before_v16_observation_streams": True,
        "v16_observation_or_selection_outcomes_read_before_freeze": False,
        "fresh_observation_protocol": {
            "source_stream_seed": SOURCE_STREAM_SEED,
            "validation_stream_seed": VALIDATION_STREAM_SEED,
            "source_observation_count": SOURCE_OBSERVATION_COUNT,
            "validation_observation_count": VALIDATION_OBSERVATION_COUNT,
            "streams_are_content_addressed_and_disjoint": True,
            "board_shape": [4, 4],
            "occupied_cell_count_support": [2, 12],
            "occupied_cell_count_law": "UNIFORM_INTEGER",
            "occupied_positions_law": "UNIFORM_WITHOUT_REPLACEMENT",
            "rank_support": [1, 6],
            "rank_law": "UNIFORM_INTEGER",
            "action_law": "UNIFORM_OVER_LEGAL_ACTIONS",
            "observed_fields": [
                "PRE_STATE",
                "ACTION",
                "POST_SWIPE_BOARD_FROM_PROVED_V14_PROGRAM",
                "SPAWNED_CELL",
                "SPAWNED_RANK",
                "POST_STATE",
                "SHA256_TAPE",
            ],
            "spawn_probability_or_source_rule_available_to_learner": False,
            "target_policy_reward_or_rollout_available_to_learner": False,
        },
        "spawn_program_candidates": candidates,
        "selection_protocol": {
            "source_score": "EXACT_SEEDED_OUTCOME_MISMATCH_COUNT",
            "selected_candidate": (
                "UNIQUE_LEXICOGRAPHIC_MINIMUM_MISMATCH_CANDIDATE"
            ),
            "source_acceptance_requires_zero_mismatch": True,
            "validation_read_only_after_source_selection": True,
            "heldout_acceptance_requires_zero_mismatch": True,
            "nonunique_or_nonzero_source_result": "NEGATIVE_NO_PROGRAM_SELECTED",
            "validation_mismatch_result": "NEGATIVE_HELDOUT_REJECTION",
            "candidate_grammar_training_observation_count": 0,
        },
        "exact_postselection_proof": {
            "source_access_allowed_only_after_proposal_freeze": True,
            "source_path": "src/acfqp/domains/standard_2048.py",
            "source_sha256": STANDARD_2048_SOURCE_SHA256,
            "source_byte_count": STANDARD_2048_SOURCE_BYTE_COUNT,
            "proof_reduction": (
                "SPAWN_ROWS_FACTOR_THROUGH_POST_SWIPE_EMPTY_CELL_SUBSET"
            ),
            "nonempty_proper_empty_cell_subsets": 65534,
            "all_candidate_rank_rows_use_exact_rational_arithmetic": True,
            "required_result": (
                "SELECTED_PROGRAM_ROWS_EQUAL_SOURCE_CLOSED_STANDARD_2048_"
                "SPAWN_ROWS_FOR_EVERY_REGISTERED_EMPTY_SUBSET"
            ),
            "proof_compute_is_not_counted_as_transition_observation": True,
            "proof_failure_prevents_world_model_authority": True,
        },
        "world_model_successor": {
            "deterministic_swipe_component": (
                "V14_OBSERVATION_PROPOSED_EXHAUSTIVELY_PROVED_PROGRAM"
            ),
            "stochastic_spawn_component": (
                "V16_OBSERVATION_PROPOSED_EXHAUSTIVELY_PROVED_PROGRAM"
            ),
            "full_state_action_rows_materialized": False,
            "successors_generated_by_composed_factored_programs": True,
            "future_multistep_plan_certificate_requires_exact_model_identity": True,
            "certificate_failure_route": "LOCAL_GROUND_DISTINCTION_THEN_FALLBACK",
            "ground_access_before_certificate_failure": False,
        },
        "sample_tax_gate": {
            "v14_swipe_observation_count": 768,
            "v16_spawn_observation_count": (
                SOURCE_OBSERVATION_COUNT + VALIDATION_OBSERVATION_COUNT
            ),
            "joint_swipe_and_spawn_observation_count": (
                JOINT_SWIPE_AND_SPAWN_OBSERVATION_COUNT
            ),
            "matched_fixed_observation_control_count": (
                MATCHED_FIXED_OBSERVATION_CONTROL_COUNT
            ),
            "registered_observation_difference": REGISTERED_OBSERVATION_DIFFERENCE,
            "proof_compute_reported_separately": True,
            "target_transition_count_reported_separately": True,
            "positive_result_requires_unique_source_and_heldout_acceptance": True,
            "positive_result_requires_exact_postselection_proof": True,
            "broad_or_physical_iid_sample_efficiency_claimed": False,
            "total_operational_work_saving_claimed": False,
        },
        "outcome_fields_present": False,
        "observation_archives_materialized": False,
        "program_selection_executed": False,
        "exact_support_proof_executed": False,
        "synthesized_world_model_issued": False,
        "target_planning_or_execution_performed": False,
        "sample_tax_reduction_claimed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "broad_world_model_synthesis_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "spawn_program_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SpawnProgramPreregistrationV16:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("spawn-program preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("spawn-program preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "spawn_program_preregistration_id"
        }
        if (
            document.get("spawn_program_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("spawn-program preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("spawn-program preregistration is not an object")
        return document


def freeze_standard_2048_spawn_program_preregistration_v16(
) -> Standard2048SpawnProgramPreregistrationV16:
    document = _document()
    if document["spawn_program_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen spawn-program preregistration identity changed")
    return Standard2048SpawnProgramPreregistrationV16(
        _ISSUER,
        canonical_json_bytes(document),
        document["spawn_program_preregistration_id"],
    )


def verify_standard_2048_spawn_program_preregistration_v16(
    value: Standard2048SpawnProgramPreregistrationV16,
) -> Standard2048SpawnProgramPreregistrationV16:
    if type(value) is not Standard2048SpawnProgramPreregistrationV16:
        _fail("spawn-program preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("spawn-program preregistration differs from frozen semantics")
    return value


__all__ = (
    "FUTURE_DOMAINS",
    "JOINT_SWIPE_AND_SPAWN_OBSERVATION_COUNT",
    "PREREGISTRATION_ID",
    "REGISTERED_OBSERVATION_DIFFERENCE",
    "SOURCE_OBSERVATION_COUNT",
    "SPAWN_PROGRAM_CANDIDATES",
    "Standard2048SpawnProgramPreregistrationV16",
    "VALIDATION_OBSERVATION_COUNT",
    "freeze_standard_2048_spawn_program_preregistration_v16",
    "verify_standard_2048_spawn_program_preregistration_v16",
)
