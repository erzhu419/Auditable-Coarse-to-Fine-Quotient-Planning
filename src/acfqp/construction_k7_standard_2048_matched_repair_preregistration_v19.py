"""Outcome-free matched Gate for active program repair versus a local table."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_local_repair_preregistration_v18 as v18
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_ACQUISITION_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CERTIFICATE_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_EPISODE_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_FAILURE_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_OVERLAY_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_PREREGISTRATION_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_VERIFICATION_V19_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "19.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.178"
PROFILE_KEY = "construction_k7_standard_2048_matched_program_prior_repair_v19"
PREREGISTRATION_ID = "247ad097f7e4b46831cf4bde18193e440a413a579a9613a1359b2f20ecdecc43"
V18_PREREGISTRATION_ID = v18.PREREGISTRATION_ID
V18_CAMPAIGN_ID = "666509cc46b596fb1241fb5d066440e31547cbbd540b79f5bd535acfa3232ede"
V18_INDEPENDENT_VERIFICATION_ID = "0529828cc943310226f2643b575a0f0985c7075781630814d4c987b972a1a9db"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 4
TARGET_INITIAL_BOARDS = (
    (1, 2, 4, 4, 3, 4, 4, 0, 3, 2, 3, 2, 6, 3, 1, 1),
    (3, 0, 5, 1, 5, 3, 1, 2, 4, 5, 0, 2, 4, 6, 5, 2),
    (4, 2, 4, 0, 1, 4, 6, 3, 3, 0, 2, 0, 6, 0, 3, 3),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v178-matched-repair-target-{index:02d}-20260813"
    for index in range(len(TARGET_INITIAL_BOARDS))
)
ARMS = ("PROGRAM_PRIOR_ACTIVE_SPLIT", "STRICT_NO_PRIOR_CONTEXT_TABLE")
FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_PREREGISTRATION_V19_DOMAIN,
    "failure": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_FAILURE_V19_DOMAIN,
    "acquisition": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_ACQUISITION_V19_DOMAIN,
    "overlay": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_OVERLAY_V19_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CERTIFICATE_V19_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_EPISODE_V19_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_VERIFICATION_V19_DOMAIN,
}


class ConstructionK7Standard2048MatchedRepairPreregistrationV19Error(ValueError):
    """The matched arms, workload, stopping rule, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048MatchedRepairPreregistrationV19Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_preregistration.v19",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v18_local_repair_preregistration_id": V18_PREREGISTRATION_ID,
            "v18_local_repair_campaign_id": V18_CAMPAIGN_ID,
            "v18_independent_verification_id": V18_INDEPENDENT_VERIFICATION_ID,
            "v18_results_frozen_before_v19_target_execution": True,
        },
        "target_kernel_id": "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a",
        "target_workload": {
            "initial_boards": [list(board) for board in TARGET_INITIAL_BOARDS],
            "episode_seeds": list(TARGET_SEEDS),
            "episode_count": len(TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "planning_horizon": PLANNING_HORIZON,
            "arm_order_has_no_semantic_authority": True,
        },
        "matched_arms": [
            {
                "arm": "PROGRAM_PRIOR_ACTIVE_SPLIT",
                "initial_candidate_programs": [row[0] for row in v18.candidate_programs_v18()],
                "query_rule": "MINIMIZE_MAXIMUM_VERSION_SPACE_BUCKET_THEN_MIN_EMPTY_COUNT",
                "stopping_rule": "ONE_PROGRAM_REMAINS",
                "persistent_program_reused_across_all_later_frontiers": True,
            },
            {
                "arm": "STRICT_NO_PRIOR_CONTEXT_TABLE",
                "initial_candidate_programs": [],
                "query_rule": "QUERY_EVERY_UNBOUND_EMPTY_COUNT_IN_FAILED_FRONTIER_ASCENDING",
                "stopping_rule": "EVERY_REACHABLE_FRONTIER_CONTEXT_BOUND",
                "persistent_context_rows_reused_across_all_later_frontiers": True,
            },
        ],
        "matching_contract": {
            "same_target_kernel": True,
            "same_initial_boards_and_tapes": True,
            "same_horizon_objective_and_tie_break": True,
            "same_certificate_failure_before_first_query": True,
            "same_exact_ground_query_interface": True,
            "same_query_identity_charged_once_per_arm": True,
            "cold_target_ground_planner_evaluation_only": True,
            "positive_sample_result_requires_strictly_fewer_unique_queries": True,
            "positive_quality_result_requires_all_root_values_and_actions_exact": True,
        },
        "sample_axes": {
            "ground_distinction_queries": "PRIMARY_REGISTERED_SAMPLE_AXIS",
            "target_execution_transitions": "REPORTED_SEPARATELY",
            "program_proof_and_planning_compute": "REPORTED_SEPARATELY",
            "full_state_action_rows": "REPORTED_SEPARATELY",
            "scalar_sum_present": False,
        },
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "program_prior_query_count": 0,
        "no_prior_query_count": 0,
        "strict_query_reduction_observed": False,
        "broad_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "matched_repair_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048MatchedRepairPreregistrationV19:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("matched preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("matched preregistration bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "matched_repair_preregistration_id"
        }
        if (
            document.get("matched_repair_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("matched preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("matched preregistration is not an object")
        return document


def freeze_standard_2048_matched_repair_preregistration_v19(
) -> Standard2048MatchedRepairPreregistrationV19:
    document = _document()
    if document["matched_repair_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen matched preregistration identity changed")
    return Standard2048MatchedRepairPreregistrationV19(
        _ISSUER, canonical_json_bytes(document), document["matched_repair_preregistration_id"]
    )


def verify_standard_2048_matched_repair_preregistration_v19(
    value: Standard2048MatchedRepairPreregistrationV19,
) -> Standard2048MatchedRepairPreregistrationV19:
    if type(value) is not Standard2048MatchedRepairPreregistrationV19:
        _fail("matched preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("matched preregistration differs from frozen semantics")
    return value


__all__ = (
    "ARMS",
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "Standard2048MatchedRepairPreregistrationV19",
    "TARGET_INITIAL_BOARDS",
    "TARGET_SEEDS",
    "freeze_standard_2048_matched_repair_preregistration_v19",
    "verify_standard_2048_matched_repair_preregistration_v19",
)
