"""Outcome-free Gate for local repair of a synthesized 2048 world model."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_local_dynamics_kernel_v18 as kernel
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_ACQUISITION_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CERTIFICATE_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_EPISODE_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_FAILURE_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_OVERLAY_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_PREREGISTRATION_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_VERIFICATION_V18_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "18.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.177"
PROFILE_KEY = "construction_k7_standard_2048_certificate_triggered_local_program_repair_v18"
PREREGISTRATION_ID = "d7e0a21868fc53854db8df3818c6cfbb6d10ea504802ed0e784dc69e8b7ad747"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 4
MAXIMUM_GROUND_DISTINCTION_QUERIES = 8
BASE_RATE = Fraction(1, 10)
OVERRIDE_RATE_CANDIDATES = (Fraction(3, 20), Fraction(1, 5), Fraction(1, 4))
THRESHOLD_CANDIDATES = tuple(range(1, 9))
TARGET_INITIAL_BOARDS = (
    (1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6, 2, 2, 1, 1),
    (1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6, 1, 1, 2, 2),
    (1, 2, 3, 4, 1, 2, 3, 4, 2, 3, 4, 5, 2, 3, 4, 5),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v177-local-repair-target-{index:02d}-20260813"
    for index in range(len(TARGET_INITIAL_BOARDS))
)

V16_WORLD_MODEL_ID = "492750c86baf5d53f68b7f470a8d5e3f74a7b088dc5767329a5945a90f01f389"
V16_INDEPENDENT_VERIFICATION_ID = "a6fa6e31d8ee765e4a6c352384baed87ef7a38bba58af7590b85b666e94a8198"
V17_CAMPAIGN_ID = "ef411b84bb88d8084bf9a4b9f65be6200a8459a1e26394a96cc5fa38aeba496e"
V17_INDEPENDENT_VERIFICATION_ID = "fe132b3f4be8f6b83b59e7f04c5e8c963872c233862c6796a242b87f9ced42d8"

FUTURE_DOMAINS = {
    "kernel": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN,
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_PREREGISTRATION_V18_DOMAIN,
    "failure": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_FAILURE_V18_DOMAIN,
    "acquisition": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_ACQUISITION_V18_DOMAIN,
    "overlay": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_OVERLAY_V18_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CERTIFICATE_V18_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_EPISODE_V18_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_VERIFICATION_V18_DOMAIN,
}


class ConstructionK7Standard2048LocalRepairPreregistrationV18Error(ValueError):
    """The frozen base model, grammar, workload, or route changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048LocalRepairPreregistrationV18Error(message)


def candidate_programs_v18() -> tuple[tuple[str, int, Fraction], ...]:
    rows = [("NO_OVERRIDE", 0, BASE_RATE)]
    rows.extend(
        (
            f"EMPTY_COUNT_LE_{threshold}__RANK_TWO_{rate.numerator}_OVER_{rate.denominator}",
            threshold,
            rate,
        )
        for threshold in THRESHOLD_CANDIDATES
        for rate in OVERRIDE_RATE_CANDIDATES
    )
    return tuple(rows)


def _document() -> dict[str, Any]:
    candidates = [
        {
            "candidate_ordinal": ordinal,
            "candidate_key": key,
            "base_rank_two_probability": BASE_RATE,
            "override_predicate": (
                "NEVER" if threshold == 0 else "POST_SWIPE_EMPTY_COUNT_LE_THRESHOLD"
            ),
            "override_threshold": threshold,
            "override_rank_two_probability": rate,
        }
        for ordinal, (key, threshold, rate) in enumerate(candidate_programs_v18())
    ]
    payload = {
        "schema": "acfqp.standard_2048_local_repair_preregistration.v18",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_base_model": {
            "v16_synthesized_world_model_id": V16_WORLD_MODEL_ID,
            "v16_independent_verification_id": V16_INDEPENDENT_VERIFICATION_ID,
            "v17_fresh_planning_campaign_id": V17_CAMPAIGN_ID,
            "v17_independent_verification_id": V17_INDEPENDENT_VERIFICATION_ID,
            "base_model_frozen_before_v18_target_identity": True,
        },
        "target_environment_binding": {
            "target_kernel_id": kernel.TARGET_KERNEL_ID,
            "kernel_identity_frozen_before_target_execution": True,
            "target_kernel_semantics_available_to_planner_before_failure": False,
            "target_transition_outcomes_read_before_preregistration": False,
            "candidate_program_is_guaranteed_to_contain_target_law": True,
        },
        "candidate_programs": candidates,
        "candidate_program_count": len(candidates),
        "recovery_protocol": {
            "planning_horizon": PLANNING_HORIZON,
            "base_applicability_audit_uses_support_geometry_only": True,
            "ground_probability_query_before_failed_audit": False,
            "failed_audit_freezes_disagreement_empty_counts": True,
            "adaptive_query_rule": "LARGEST_CURRENT_FRONTIER_CONTEXT_WITH_CANDIDATE_DISAGREEMENT",
            "queries_restricted_to_failed_certificate_frontier": True,
            "candidate_elimination_uses_exact_rational_equality": True,
            "recertification_requires_single_probability_on_every_reachable_frontier_context": True,
            "persistent_version_space_reused_across_decisions_and_episodes": True,
            "maximum_ground_distinction_queries": MAXIMUM_GROUND_DISTINCTION_QUERIES,
            "query_cap_exhaustion_route": "COLD_EXACT_GROUND_FALLBACK",
        },
        "target_workload": {
            "initial_boards": [list(board) for board in TARGET_INITIAL_BOARDS],
            "episode_seeds": list(TARGET_SEEDS),
            "episode_count": len(TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
        },
        "matched_controls": {
            "cold_exact_target_ground_h3_at_every_decision": True,
            "standalone_evaluation_lane_only": True,
            "no_prior_table_queries_every_distinct_first_failed_frontier_context": True,
            "route_or_certificate_authority": False,
        },
        "sample_tax_scope": {
            "v16_joint_model_synthesis_transition_observations": 1152,
            "v16_matched_fixed_observation_control": 8192,
            "v16_registered_observation_difference": 7040,
            "v18_program_prior_queries_reported_against_matched_no_prior_frontier_table": True,
            "exact_program_proof_and_planning_compute_reported_separately": True,
            "broad_or_physical_iid_sample_efficiency_claimed": False,
            "total_operational_work_saving_claimed": False,
        },
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "certificate_failure_count": 0,
        "ground_distinction_query_count": 0,
        "overlay_program_selected": False,
        "recertification_count": 0,
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
        "local_repair_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048LocalRepairPreregistrationV18:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("local-repair preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("local-repair preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "local_repair_preregistration_id"
        }
        if (
            document.get("local_repair_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("local-repair preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("local-repair preregistration is not an object")
        return document


def freeze_standard_2048_local_repair_preregistration_v18(
) -> Standard2048LocalRepairPreregistrationV18:
    kernel.verify_target_kernel_identity_v18()
    document = _document()
    if document["local_repair_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen local-repair preregistration identity changed")
    return Standard2048LocalRepairPreregistrationV18(
        _ISSUER,
        canonical_json_bytes(document),
        document["local_repair_preregistration_id"],
    )


def verify_standard_2048_local_repair_preregistration_v18(
    value: Standard2048LocalRepairPreregistrationV18,
) -> Standard2048LocalRepairPreregistrationV18:
    if type(value) is not Standard2048LocalRepairPreregistrationV18:
        _fail("local-repair preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("local-repair preregistration differs from frozen semantics")
    return value


__all__ = (
    "BASE_RATE",
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "MAXIMUM_GROUND_DISTINCTION_QUERIES",
    "OVERRIDE_RATE_CANDIDATES",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "Standard2048LocalRepairPreregistrationV18",
    "TARGET_INITIAL_BOARDS",
    "TARGET_SEEDS",
    "THRESHOLD_CANDIDATES",
    "candidate_programs_v18",
    "freeze_standard_2048_local_repair_preregistration_v18",
    "verify_standard_2048_local_repair_preregistration_v18",
)
