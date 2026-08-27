"""Producer-free replay of V42 from each registered fresh initial board.

This module deliberately does not import the V42 campaign or runner.  It
reconstructs every H3 certificate with the independent V35 planner, selects
every deterministic target-kernel outcome from decision index zero, and then
rebuilds the complete previous-step content-ID chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import sys
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp import construction_k7_standard_2048_adaptive_expression_independent_verifier_v35 as v35verify
from acfqp import construction_k7_standard_2048_execution_authority_v42 as authority
from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
VERIFICATION_SCHEMA_VERSION = "42.0.0"
PROFILE_KEY = "construction_k7_standard_2048_fresh_terminal_campaign_v42"
class ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error(
    ValueError
):
    """The V42 bytes differ from independent initial-to-terminal replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error(
        message
    )


def _verify_id(document: Any, id_key: str, domain: str, label: str) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != domains.extension_content_id_v42(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _state(document: Any) -> Any:
    if (
        type(document) is not dict
        or set(document) != {"board_ranks", "status"}
        or type(document.get("board_ranks")) is not list
    ):
        _fail("V42 state shape changed")
    try:
        state = state_from_board_v1(tuple(document["board_ranks"]))
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error(
            "V42 state board changed"
        ) from error
    if state.status.value != document.get("status"):
        _fail("V42 state status changed")
    return state


def _candidate() -> tuple[str, dict[str, Any], int, Fraction, str]:
    return (
        pre.ADAPTIVE_EXPRESSION_MODEL_ID,
        {
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 2,
        },
        1,
        Fraction(1, 4),
        "LE_OVERRIDE",
    )


def _replay_episode(
    episode: Any,
    *,
    execution_kind: str,
    episode_index: int,
    initial_board: tuple[int, ...],
    seed: str,
    decision_limit: int,
) -> dict[str, int | bool]:
    episode = _verify_id(
        episode,
        "fresh_terminal_episode_id",
        domains.CONSTRUCTION_K7_EPISODE_V42_DOMAIN,
        "V42 episode",
    )
    state = state_from_board_v1(initial_board)
    if state.status is not Swipe2048Status.ACTIVE:
        _fail("V42 replay did not start at an active fresh board")
    if (
        episode.get("execution_kind") != execution_kind
        or episode.get("fresh_terminal_preregistration_id") != pre.PREREGISTRATION_ID
        or episode.get("target_kernel_id") != pre.TARGET_KERNEL_ID
        or episode.get("adaptive_expression_overlay_id")
        != pre.ADAPTIVE_EXPRESSION_OVERLAY_ID
        or episode.get("adaptive_expression_proof_id")
        != pre.ADAPTIVE_EXPRESSION_PROOF_ID
        or episode.get("adaptive_expression_model_id")
        != pre.ADAPTIVE_EXPRESSION_MODEL_ID
        or episode.get("planner_id") != pre.PLANNER_ID
        or episode.get("episode_index") != episode_index
        or episode.get("execution_seed") != seed
        or episode.get("initial_decision_index") != 0
        or episode.get("decision_limit") != decision_limit
        or _state(episode.get("initial_state")) != state
    ):
        _fail("V42 episode did not start from its registered initial identity")
    steps = episode.get("steps")
    if (
        type(steps) is not list
        or not steps
        or len(steps) > decision_limit
    ):
        _fail("V42 step inventory changed")
    planning = v35verify._PersistentPlanner(_candidate())  # noqa: SLF001
    expected_steps: list[dict[str, Any]] = []
    previous_step_id: str | None = None
    totals = {"rows": 0, "outcomes": 0, "hits": 0, "misses": 0, "cross": 0}
    for decision_index, observed_step in enumerate(steps):
        if state.status is not Swipe2048Status.ACTIVE:
            _fail("V42 step appeared after a terminal state")
        if (
            type(observed_step) is not dict
            or observed_step.get("decision_index") != decision_index
            or observed_step.get("previous_step_id") != previous_step_id
            or _state(observed_step.get("pre_state")) != state
            or type(observed_step.get("plan_certificate")) is not dict
            or observed_step["plan_certificate"].get("previous_step_id")
            != previous_step_id
        ):
            _fail("V42 previous-step or pre-state chain changed")
        replay = planning.plan_root(state)
        certificate_payload = {
            "schema": "acfqp.standard_2048_fresh_terminal_plan_certificate.v42",
            "schema_version": SCHEMA_VERSION,
            "execution_kind": execution_kind,
            "fresh_terminal_preregistration_id": pre.PREREGISTRATION_ID,
            "target_kernel_id": pre.TARGET_KERNEL_ID,
            "adaptive_expression_overlay_id": pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
            "adaptive_expression_proof_id": pre.ADAPTIVE_EXPRESSION_PROOF_ID,
            "adaptive_expression_model_id": pre.ADAPTIVE_EXPRESSION_MODEL_ID,
            "planner_id": pre.PLANNER_ID,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "previous_step_id": previous_step_id,
            "root_state": _state_document(state),
            "planning_horizon": pre.PLANNING_HORIZON,
            "root_action_exact_values": replay["root_action_exact_values"],
            "selected_action": replay["selected_action"],
            "selected_expected_merge_score": replay["selected_expected_merge_score"],
            "selected_loss_probability_within_horizon": replay[
                "selected_loss_probability_within_horizon"
            ],
            "factored_action_row_evaluation_count": replay[
                "factored_action_row_evaluation_count"
            ],
            "factored_support_outcome_evaluation_count": replay[
                "factored_support_outcome_evaluation_count"
            ],
            "subproof_cache_hit_count": replay["subproof_cache_hit_count"],
            "subproof_cache_miss_count": replay["subproof_cache_miss_count"],
            "cross_decision_subproof_cache_hit_count": replay[
                "cross_decision_subproof_cache_hit_count"
            ],
            "persistent_subproof_cache_entry_count": replay[
                "persistent_subproof_cache_entry_count"
            ],
            "additional_model_label_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_FROZEN_V35_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "plan_certificate_id": domains.extension_content_id_v42(
                domains.CONSTRUCTION_K7_PLAN_CERTIFICATE_V42_DOMAIN,
                certificate_payload,
            ),
        }
        selected = Swipe2048Action(replay["selected_action"])
        outcome, tape = select_seeded_outcome_v1(
            v35verify._target_outcomes(state, selected),  # noqa: SLF001
            seed=seed,
            decision_index=decision_index,
        )
        step_payload = {
            "schema": "acfqp.standard_2048_fresh_terminal_transition_step.v42",
            "schema_version": SCHEMA_VERSION,
            "execution_kind": execution_kind,
            "fresh_terminal_preregistration_id": pre.PREREGISTRATION_ID,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "previous_step_id": previous_step_id,
            "pre_state": _state_document(state),
            "plan_certificate": certificate,
            "selected_action": selected.value,
            "outcome_tape_sha256": tape,
            "outcome_observation": {
                "probability": outcome.probability,
                "merge_score": outcome.merge_score,
                "spawned_cell": outcome.spawned_cell,
                "spawned_rank": outcome.spawned_rank,
            },
            "next_state": _state_document(outcome.next_state),
            "online_target_transition_observation_count": 1,
            "additional_model_label_count": 0,
            "execution_transition_used_to_modify_world_model": False,
            "certificate_frozen_before_target_transition": True,
        }
        expected_step = {
            **step_payload,
            "transition_step_id": domains.extension_content_id_v42(
                domains.CONSTRUCTION_K7_TRANSITION_STEP_V42_DOMAIN, step_payload
            ),
        }
        if observed_step != expected_step:
            _fail("V42 transition step differs from independent exact replay")
        expected_steps.append(expected_step)
        previous_step_id = expected_step["transition_step_id"]
        state = outcome.next_state
        totals["rows"] += replay["factored_action_row_evaluation_count"]
        totals["outcomes"] += replay["factored_support_outcome_evaluation_count"]
        totals["hits"] += replay["subproof_cache_hit_count"]
        totals["misses"] += replay["subproof_cache_miss_count"]
        totals["cross"] += replay["cross_decision_subproof_cache_hit_count"]

    if state.status is Swipe2048Status.ACTIVE and len(steps) != decision_limit:
        _fail("V42 active episode stopped before its registered cap")
    fail_closed = state.status is Swipe2048Status.ACTIVE
    closure_reason = (
        "DECISION_CAP_REACHED_WITH_ACTIVE_STATE" if fail_closed else state.status.value
    )
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_episode.v42",
        "schema_version": SCHEMA_VERSION,
        "execution_kind": execution_kind,
        "fresh_terminal_preregistration_id": pre.PREREGISTRATION_ID,
        "target_kernel_id": pre.TARGET_KERNEL_ID,
        "adaptive_expression_overlay_id": pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
        "adaptive_expression_proof_id": pre.ADAPTIVE_EXPRESSION_PROOF_ID,
        "adaptive_expression_model_id": pre.ADAPTIVE_EXPRESSION_MODEL_ID,
        "planner_id": pre.PLANNER_ID,
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_decision_index": 0,
        "decision_limit": decision_limit,
        "initial_state": _state_document(state_from_board_v1(initial_board)),
        "steps": expected_steps,
        "decision_count": len(expected_steps),
        "last_transition_step_id": previous_step_id,
        "final_state": _state_document(state),
        "closure_reason": closure_reason,
        "decision_cap_fail_closed": fail_closed,
        "terminal_state_reached": state.status is not Swipe2048Status.ACTIVE,
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
        "maximum_board_tile_rank": max(state.board),
        "model_certificate_count": len(expected_steps),
        "online_target_transition_observation_count": len(expected_steps),
        "additional_model_label_count": 0,
        "world_model_modified_during_episode": False,
        "in_process_subproof_cache_reused": totals["cross"] > 0,
        "crash_resume_or_cross_process_cache_persistence_claimed": False,
        "factored_action_row_evaluation_count": totals["rows"],
        "factored_support_outcome_evaluation_count": totals["outcomes"],
        "subproof_cache_hit_count": totals["hits"],
        "subproof_cache_miss_count": totals["misses"],
        "cross_decision_subproof_cache_hit_count": totals["cross"],
    }
    expected_episode = {
        **payload,
        "fresh_terminal_episode_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_EPISODE_V42_DOMAIN, payload
        ),
    }
    if episode != expected_episode:
        _fail("V42 episode aggregate or chain boundary changed")
    return {
        "decision_count": len(expected_steps),
        "terminal": state.status is not Swipe2048Status.ACTIVE,
        "tile_2048": max(state.board) >= GOAL_RANK,
        **totals,
    }


def verify_development_fixture_episode_independently_v42(
    episode: dict[str, Any],
    *,
    initial_board: tuple[int, ...],
    seed: str,
    decision_limit: int,
) -> dict[str, int | bool]:
    """Replay an explicitly non-formal short fixture for unit tests."""

    if initial_board in pre.INITIAL_BOARDS or seed in pre.EPISODE_SEEDS:
        _fail("development verification may not consume a formal V42 tape")
    if not 1 <= decision_limit <= 8:
        _fail("development verification cap must be in [1, 8]")
    return _replay_episode(
        episode,
        execution_kind="DEVELOPMENT_FIXTURE",
        episode_index=0,
        initial_board=initial_board,
        seed=seed,
        decision_limit=decision_limit,
    )


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048FreshTerminalIndependentVerificationV42:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V42 verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V42 verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "fresh_terminal_verification_id"
        }
        if (
            document.get("fresh_terminal_verification_id") != self.verification_id
            or document.get("fresh_terminal_campaign_id") != self.campaign_id
            or domains.extension_content_id_v42(
                domains.CONSTRUCTION_K7_VERIFICATION_V42_DOMAIN, payload
            )
            != self.verification_id
        ):
            _fail("V42 verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("V42 verification is not an object")
        return document


def verify_standard_2048_fresh_terminal_bytes_independently_v42(
    campaign_bytes: bytes,
    *,
    prepare_receipt_bytes: bytes,
    runner_attempt_bytes: bytes,
    worker_start_bytes: bytes,
    authority_consumption_bytes: bytes,
) -> Standard2048FreshTerminalIndependentVerificationV42:
    forbidden_loaded_modules = sorted(
        name
        for name in sys.modules
        if name
        in {
            "acfqp.construction_k7_standard_2048_fresh_terminal_campaign_v42",
            "acfqp.construction_k7_standard_2048_adaptive_expression_target_v35",
            "acfqp.construction_k7_standard_2048_observation_proposed_program_v14",
            "acfqp.construction_k7_standard_2048_expression_planner_v1",
            "scripts.run_v42_standard_2048_fresh_terminal_campaign",
            "scripts.supervise_v42_standard_2048_fresh_terminal_campaign",
        }
    )
    if forbidden_loaded_modules:
        _fail("V42 independent verifier process imported producer or runner modules")
    try:
        campaign = loads_canonical_json(campaign_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error(
            "V42 campaign is not canonical"
        ) from error
    if type(campaign) is not dict or canonical_json_bytes(campaign) != campaign_bytes:
        _fail("V42 campaign canonical bytes changed")
    _verify_id(
        campaign,
        "fresh_terminal_campaign_id",
        domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN,
        "V42 campaign",
    )
    campaign_id = campaign["fresh_terminal_campaign_id"]
    preregistration = pre.freeze_standard_2048_fresh_terminal_preregistration_v42()
    if campaign.get("fresh_terminal_preregistration") != preregistration.to_document():
        _fail("V42 campaign preregistration binding changed")
    history_manifest = pre._freshness()  # noqa: SLF001
    prepare_receipt = authority.verify_prepare_receipt_v42(
        prepare_receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=history_manifest[
            "history_freshness_manifest_id"
        ],
    )
    runner_attempt = authority.verify_runner_attempt_v42(
        runner_attempt_bytes,
        prepare_receipt=prepare_receipt,
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
    )
    try:
        worker_start_document = loads_canonical_json(worker_start_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error(
            "V42 worker start is not canonical"
        ) from error
    if type(worker_start_document) is not dict:
        _fail("V42 worker start is not an object")
    worker_start = authority.verify_worker_start_v42(
        worker_start_bytes,
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_authorization_secret_sha256=worker_start_document.get(
            "worker_authorization_secret_sha256"
        ),
    )
    authority_consumption = authority.verify_authority_consumption_v42(
        authority_consumption_bytes,
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_start=worker_start,
    )
    expected_source_binding = authority.build_campaign_source_binding_v42(
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_start=worker_start,
        authority_consumption=authority_consumption,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        target_kernel_id=pre.TARGET_KERNEL_ID,
        adaptive_expression_overlay_id=pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
        adaptive_expression_proof_id=pre.ADAPTIVE_EXPRESSION_PROOF_ID,
        adaptive_expression_model_id=pre.ADAPTIVE_EXPRESSION_MODEL_ID,
        planner_id=pre.PLANNER_ID,
    )
    source_binding = authority.verify_campaign_source_binding_v42(
        campaign.get("source_binding"), expected=expected_source_binding
    )
    if campaign.get("execution_schedule") != {
        "maximum_concurrent_episode_processes": 2,
        "episode_count": len(pre.INITIAL_BOARDS),
        "one_process_task_per_episode": True,
        "each_episode_has_an_independent_in_process_cache": True,
    }:
        _fail("V42 execution schedule changed")
    episodes = campaign.get("episodes")
    if type(episodes) is not list or len(episodes) != len(pre.INITIAL_BOARDS):
        _fail("V42 formal episode inventory changed")
    totals = [
        _replay_episode(
            episode,
            execution_kind="FORMAL_REGISTERED",
            episode_index=episode_index,
            initial_board=pre.INITIAL_BOARDS[episode_index],
            seed=pre.EPISODE_SEEDS[episode_index],
            decision_limit=pre.MAXIMUM_DECISIONS_PER_EPISODE,
        )
        for episode_index, episode in enumerate(episodes)
    ]
    decision_count = sum(int(row["decision_count"]) for row in totals)
    all_terminal = all(bool(row["terminal"]) for row in totals)
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_campaign.v42",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "fresh_terminal_preregistration": preregistration.to_document(),
        "source_binding": source_binding,
        "execution_schedule": campaign["execution_schedule"],
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": decision_count,
        "model_certificate_count": decision_count,
        "online_target_transition_observation_count": decision_count,
        "inherited_target_probability_label_count": pre.INHERITED_TARGET_PROBABILITY_LABEL_COUNT,
        "additional_model_label_count": 0,
        "all_episodes_started_from_registered_two_tile_initial_board": True,
        "all_episode_decision_indices_started_at_zero": True,
        "all_step_chains_content_addressed": True,
        "all_certificates_bound_to_single_v35_model_and_planner": True,
        "all_registered_episodes_terminal": all_terminal,
        "any_tile_2048_reached": any(bool(row["tile_2048"]) for row in totals),
        "all_decision_caps_fail_closed": True,
        "fresh_from_initial_to_terminal_claim_allowed": all_terminal,
        "broad_iid_sample_efficiency_claimed": False,
        "cross_domain_transfer_claimed": False,
        "total_operational_work_saving_claimed": False,
        "crash_resume_or_cross_process_cache_persistence_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    expected_campaign = {
        **payload,
        "fresh_terminal_campaign_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN, payload
        ),
    }
    if campaign != expected_campaign:
        _fail("V42 campaign aggregate or claim boundary changed")
    verification_payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_independent_verification.v42",
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "fresh_terminal_preregistration_id": pre.PREREGISTRATION_ID,
        "fresh_terminal_campaign_id": campaign_id,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "authority_consumption_id": authority_consumption[
            "authority_consumption_id"
        ],
        "source_binding_id": source_binding["source_binding_id"],
        "source_commit": source_binding["source_commit"],
        "source_tree": source_binding["source_tree"],
        "source_manifest_id": source_binding["source_manifest_id"],
        "producer_or_runner_module_imported": bool(forbidden_loaded_modules),
        "registered_fresh_initial_board_count": len(episodes),
        "replayed_decision_count": decision_count,
        "replayed_plan_certificate_count": decision_count,
        "replayed_target_kernel_transition_count": decision_count,
        "all_decision_indices_replayed_from_zero": True,
        "all_previous_step_id_chains_rebuilt": True,
        "all_v35_model_certificates_independently_rebuilt": True,
        "all_target_kernel_outcome_tapes_independently_replayed": True,
        "zero_additional_model_labels_verified": True,
        "all_registered_episodes_terminal_verified": all_terminal,
        "any_tile_2048_reached_verified": any(
            bool(row["tile_2048"]) for row in totals
        ),
        "fresh_from_initial_to_terminal_verified": all_terminal,
        "active_decision_cap_failure_preserved": not all_terminal,
        "broad_iid_or_total_work_claim_verified": False,
        "crash_resume_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = domains.extension_content_id_v42(
        domains.CONSTRUCTION_K7_VERIFICATION_V42_DOMAIN, verification_payload
    )
    raw = canonical_json_bytes(
        {
            **verification_payload,
            "fresh_terminal_verification_id": verification_id,
        }
    )
    return Standard2048FreshTerminalIndependentVerificationV42(
        _ISSUER, raw, verification_id, campaign_id
    )


__all__ = (
    "ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error",
    "Standard2048FreshTerminalIndependentVerificationV42",
    "verify_development_fixture_episode_independently_v42",
    "verify_standard_2048_fresh_terminal_bytes_independently_v42",
)
