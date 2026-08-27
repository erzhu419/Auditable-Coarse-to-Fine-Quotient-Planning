"""Build the registered V42 fresh-board standard-2048 step chains.

The public campaign entrypoint requires an already committed source identity.
It performs no publication; the one-shot runner owns all filesystem effects.
The development fixture helper uses a separate board and seed and can exercise
short chains without evaluating either registered formal episode.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp import construction_k7_standard_2048_adaptive_expression_target_v35 as target
from acfqp import construction_k7_standard_2048_execution_authority_v42 as authority
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
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
PROFILE_KEY = "construction_k7_standard_2048_fresh_terminal_campaign_v42"
MAXIMUM_CONCURRENT_EPISODES = 2
DEVELOPMENT_FIXTURE_BOARD = (
    1, 0, 0, 0,
    0, 0, 0, 0,
    0, 0, 2, 0,
    0, 0, 0, 0,
)
DEVELOPMENT_FIXTURE_SEED = "standard-2048-v42-development-fixture-not-formal"


class ConstructionK7Standard2048FreshTerminalCampaignV42Error(ValueError):
    """The registered start, plan certificate, transition, or chain changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FreshTerminalCampaignV42Error(message)


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _run_episode(task: tuple[str, int, tuple[int, ...], str, int]) -> dict[str, Any]:
    execution_kind, episode_index, initial_board, seed, decision_limit = task
    if execution_kind not in {"FORMAL_REGISTERED", "DEVELOPMENT_FIXTURE"}:
        _fail("V42 episode execution kind changed")
    if (
        type(episode_index) is not int
        or episode_index < 0
        or type(initial_board) is not tuple
        or len(initial_board) != 16
        or sum(rank != 0 for rank in initial_board) != 2
        or any(rank not in (0, 1, 2) for rank in initial_board)
        or type(seed) is not str
        or not seed
        or type(decision_limit) is not int
        or not 1 <= decision_limit <= pre.MAXIMUM_DECISIONS_PER_EPISODE
    ):
        _fail("V42 episode configuration changed")
    if execution_kind == "FORMAL_REGISTERED" and (
        episode_index >= len(pre.INITIAL_BOARDS)
        or initial_board != pre.INITIAL_BOARDS[episode_index]
        or seed != pre.EPISODE_SEEDS[episode_index]
        or decision_limit != pre.MAXIMUM_DECISIONS_PER_EPISODE
    ):
        _fail("formal V42 episode differs from preregistration")
    if execution_kind == "DEVELOPMENT_FIXTURE" and (
        initial_board in pre.INITIAL_BOARDS or seed in pre.EPISODE_SEEDS
    ):
        _fail("development fixture may not consume a registered V42 outcome tape")

    state = state_from_board_v1(initial_board)
    if state.status is not Swipe2048Status.ACTIVE:
        _fail("V42 must start at an active fresh board")
    initial_state = _state_document(state)
    session = planner.create_expression_planning_session_v1(
        expression_ast={
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 2,
        },
        threshold=1,
        base_probability=Fraction(1, 10),
        override_probability=Fraction(1, 4),
        horizon=pre.PLANNING_HORIZON,
    )
    steps: list[dict[str, Any]] = []
    previous_step_id: str | None = None
    for decision_index in range(decision_limit):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = session.plan_root(state)
        if model.get("target_transition_accessed") is not False:
            _fail("V42 planner accessed target before certificate freeze")
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
            "root_action_exact_values": model["root_action_exact_values"],
            "selected_action": model["selected_action"],
            "selected_expected_merge_score": model["selected_expected_merge_score"],
            "selected_loss_probability_within_horizon": model[
                "selected_loss_probability_within_horizon"
            ],
            "factored_action_row_evaluation_count": model[
                "factored_action_row_evaluation_count"
            ],
            "factored_support_outcome_evaluation_count": model[
                "factored_support_outcome_evaluation_count"
            ],
            "subproof_cache_hit_count": model["subproof_cache_hit_count"],
            "subproof_cache_miss_count": model["subproof_cache_miss_count"],
            "cross_decision_subproof_cache_hit_count": model[
                "cross_decision_subproof_cache_hit_count"
            ],
            "persistent_subproof_cache_entry_count": model[
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
        selected_action = Swipe2048Action(model["selected_action"])
        outcome, tape = select_seeded_outcome_v1(
            target.target_outcomes_v35(state, selected_action),
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
            "selected_action": selected_action.value,
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
        step = {
            **step_payload,
            "transition_step_id": domains.extension_content_id_v42(
                domains.CONSTRUCTION_K7_TRANSITION_STEP_V42_DOMAIN, step_payload
            ),
        }
        steps.append(step)
        previous_step_id = step["transition_step_id"]
        state = outcome.next_state

    if state.status is Swipe2048Status.ACTIVE:
        closure_reason = "DECISION_CAP_REACHED_WITH_ACTIVE_STATE"
        fail_closed = True
    else:
        closure_reason = state.status.value
        fail_closed = False
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
        "initial_state": initial_state,
        "steps": steps,
        "decision_count": len(steps),
        "last_transition_step_id": previous_step_id,
        "final_state": _state_document(state),
        "closure_reason": closure_reason,
        "decision_cap_fail_closed": fail_closed,
        "terminal_state_reached": state.status is not Swipe2048Status.ACTIVE,
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
        "maximum_board_tile_rank": max(state.board),
        "model_certificate_count": len(steps),
        "online_target_transition_observation_count": len(steps),
        "additional_model_label_count": 0,
        "world_model_modified_during_episode": False,
        "in_process_subproof_cache_reused": sum(
            step["plan_certificate"]["cross_decision_subproof_cache_hit_count"]
            for step in steps
        )
        > 0,
        "crash_resume_or_cross_process_cache_persistence_claimed": False,
        "factored_action_row_evaluation_count": sum(
            step["plan_certificate"]["factored_action_row_evaluation_count"]
            for step in steps
        ),
        "factored_support_outcome_evaluation_count": sum(
            step["plan_certificate"]["factored_support_outcome_evaluation_count"]
            for step in steps
        ),
        "subproof_cache_hit_count": sum(
            step["plan_certificate"]["subproof_cache_hit_count"] for step in steps
        ),
        "subproof_cache_miss_count": sum(
            step["plan_certificate"]["subproof_cache_miss_count"] for step in steps
        ),
        "cross_decision_subproof_cache_hit_count": sum(
            step["plan_certificate"]["cross_decision_subproof_cache_hit_count"]
            for step in steps
        ),
    }
    return {
        **payload,
        "fresh_terminal_episode_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_EPISODE_V42_DOMAIN, payload
        ),
    }


def build_development_fixture_episode_v42(*, decision_limit: int = 2) -> dict[str, Any]:
    """Return a short, explicitly non-formal chain for tests only."""

    if type(decision_limit) is not int or not 1 <= decision_limit <= 8:
        _fail("V42 development fixture cap must be in [1, 8]")
    return _run_episode(
        (
            "DEVELOPMENT_FIXTURE",
            0,
            DEVELOPMENT_FIXTURE_BOARD,
            DEVELOPMENT_FIXTURE_SEED,
            decision_limit,
        )
    )


def _run_formal_episode(
    task: tuple[tuple[str, int, tuple[int, ...], str, int], str, dict[str, Any]]
) -> dict[str, Any]:
    episode_task, repository_root, source_manifest = task
    authority.install_runtime_repository_import_guard_v42(
        Path(repository_root), source_manifest
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        Path(repository_root), source_manifest
    )
    episode = _run_episode(episode_task)
    authority.verify_runtime_repository_modules_in_manifest_v42(
        Path(repository_root), source_manifest
    )
    return episode


_FORMAL_AUTHORITY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _FormalExecutionAuthorityV42:
    _issuer: object = field(repr=False, compare=False)
    prepare_receipt: dict[str, Any]
    runner_attempt: dict[str, Any]
    worker_start: dict[str, Any]
    authority_consumption: dict[str, Any]
    source_binding: dict[str, Any]
    repository_root: str
    _unused: list[bool] = field(
        default_factory=lambda: [True], repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._issuer is not _FORMAL_AUTHORITY_ISSUER or self._unused != [True]:
            _fail("formal V42 execution authority is not worker-issued")


def _issue_formal_execution_authority_v42(
    *,
    repository_root: Path,
    worker_authorization_secret: bytes,
) -> _FormalExecutionAuthorityV42:
    """Consume the fixed durable supervisor claim and issue one capability."""

    history_manifest = pre._freshness()  # noqa: SLF001
    receipt, attempt, worker_start, consumption = (
        authority.consume_supervisor_worker_authorization_v42(
        repository_root,
        worker_authorization_secret=worker_authorization_secret,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=history_manifest[
            "history_freshness_manifest_id"
        ],
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
        )
    )
    source_binding = authority.build_campaign_source_binding_v42(
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=worker_start,
        authority_consumption=consumption,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        target_kernel_id=pre.TARGET_KERNEL_ID,
        adaptive_expression_overlay_id=pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
        adaptive_expression_proof_id=pre.ADAPTIVE_EXPRESSION_PROOF_ID,
        adaptive_expression_model_id=pre.ADAPTIVE_EXPRESSION_MODEL_ID,
        planner_id=pre.PLANNER_ID,
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        repository_root, receipt["source_manifest"]
    )
    return _FormalExecutionAuthorityV42(
        _FORMAL_AUTHORITY_ISSUER,
        receipt,
        attempt,
        worker_start,
        consumption,
        source_binding,
        str(repository_root.resolve()),
    )


def _campaign_document(formal_authority: _FormalExecutionAuthorityV42) -> dict[str, Any]:
    if type(formal_authority) is not _FormalExecutionAuthorityV42:
        _fail("formal V42 campaign requires one worker-issued authority")
    formal_authority.__post_init__()
    history_manifest = pre._freshness()  # noqa: SLF001
    authority.verify_consumed_formal_authority_v42(
        Path(formal_authority.repository_root),
        prepare_receipt=formal_authority.prepare_receipt,
        runner_attempt=formal_authority.runner_attempt,
        worker_start=formal_authority.worker_start,
        authority_consumption=formal_authority.authority_consumption,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=history_manifest[
            "history_freshness_manifest_id"
        ],
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
    )
    formal_authority._unused[0] = False  # noqa: SLF001
    preregistration = pre.verify_standard_2048_fresh_terminal_preregistration_v42(
        pre.freeze_standard_2048_fresh_terminal_preregistration_v42()
    )
    source_binding = formal_authority.source_binding
    tasks = tuple(
        (
            "FORMAL_REGISTERED",
            episode_index,
            pre.INITIAL_BOARDS[episode_index],
            pre.EPISODE_SEEDS[episode_index],
            pre.MAXIMUM_DECISIONS_PER_EPISODE,
        )
        for episode_index in range(len(pre.INITIAL_BOARDS))
    )
    isolated_tasks = tuple(
        (task, formal_authority.repository_root, formal_authority.prepare_receipt["source_manifest"])
        for task in tasks
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_CONCURRENT_EPISODES) as executor:
        episodes = list(executor.map(_run_formal_episode, isolated_tasks, chunksize=1))
    episodes.sort(key=lambda episode: episode["episode_index"])
    decision_count = sum(episode["decision_count"] for episode in episodes)
    all_terminal = all(episode["terminal_state_reached"] for episode in episodes)
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_campaign.v42",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "fresh_terminal_preregistration": preregistration.to_document(),
        "source_binding": source_binding,
        "execution_schedule": {
            "maximum_concurrent_episode_processes": MAXIMUM_CONCURRENT_EPISODES,
            "episode_count": len(tasks),
            "one_process_task_per_episode": True,
            "each_episode_has_an_independent_in_process_cache": True,
        },
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
        "any_tile_2048_reached": any(
            episode["tile_2048_reached"] for episode in episodes
        ),
        "all_decision_caps_fail_closed": all(
            episode["terminal_state_reached"]
            or episode["decision_cap_fail_closed"]
            for episode in episodes
        ),
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
    return {
        **payload,
        "fresh_terminal_campaign_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048FreshTerminalCampaignV42:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V42 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V42 campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "fresh_terminal_campaign_id"
        }
        if (
            document.get("fresh_terminal_campaign_id") != self.campaign_id
            or domains.extension_content_id_v42(
                domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN, payload
            )
            != self.campaign_id
        ):
            _fail("V42 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("V42 campaign is not an object")
        return document


def _run_standard_2048_fresh_terminal_campaign_v42(
    *, formal_authority: _FormalExecutionAuthorityV42
) -> Standard2048FreshTerminalCampaignV42:
    """Worker-only formal entry; development callers cannot mint its capability."""

    document = _campaign_document(formal_authority)
    raw = canonical_json_bytes(document)
    return Standard2048FreshTerminalCampaignV42(
        _ISSUER, raw, document["fresh_terminal_campaign_id"]
    )


def verify_standard_2048_fresh_terminal_campaign_v42(
    value: Standard2048FreshTerminalCampaignV42,
) -> Standard2048FreshTerminalCampaignV42:
    if type(value) is not Standard2048FreshTerminalCampaignV42:
        _fail("V42 campaign verifier rejects foreign values")
    value.__post_init__()
    return value


__all__ = (
    "DEVELOPMENT_FIXTURE_BOARD",
    "DEVELOPMENT_FIXTURE_SEED",
    "Standard2048FreshTerminalCampaignV42",
    "build_development_fixture_episode_v42",
    "verify_standard_2048_fresh_terminal_campaign_v42",
)
