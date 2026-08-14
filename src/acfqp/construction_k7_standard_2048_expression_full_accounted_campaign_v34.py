"""Rerun the complete registered 2048 campaign under native V9 windows."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import resource
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_commit_reveal_target_kernel_v22 as target
from acfqp import construction_k7_standard_2048_expression_accounted_campaign_v24 as v24_campaign
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v26 as v26
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v27 as v27
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v28 as v28
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v29 as v29
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v30 as v30
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v31 as v31
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v32 as v32
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v33 as v33
from acfqp import construction_k7_standard_2048_expression_full_accounting_artifacts_v34 as artifacts
from acfqp import construction_k7_standard_2048_expression_full_accounting_preregistration_v34 as pre
from acfqp import construction_k7_standard_2048_expression_full_accounting_runtime_v34 as runtime
from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as long_pre
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.accounting_v1 import ReducerEnum, RouteKindEnum, SHARED_AXES
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = pre.PROFILE_KEY
EXPECTED_CAMPAIGN_ID = "f5e83e7cb6eaee01d35b325e83e6b50676843a32af40c21aae237144b5784f05"
EXPECTED_CANONICAL_BYTE_COUNT = 322463
EXPECTED_CANONICAL_SHA256 = "1ec5ae427da041205f4b4ccae23d4bd3dd62cdd5146105a3f4373e62bb9d6630"
FINAL_EPISODE_IDS = (
    "43a946ba2fe68d3ae10a30fd36bf7fc28ff7cacb5c976c5c5febec1bfb04ed8b",
    "2e0b83e1ae2f1e154328b9644d337f43116803189f654f3182e7c60d2100a99f",
    "2a4a05215e21defb6949883af68f59d7af41dc0e56b229776fbb3312a277d089",
    "1c03b5d5bff535a2359b437a2cfad8d91c35af8c5c69282ba90b31f924e2f229",
)


class ConstructionK7Standard2048ExpressionFullAccountedCampaignV34Error(
    RuntimeError
):
    """A native segment, exact predecessor join, or accounting bundle changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionFullAccountedCampaignV34Error(message)


@dataclass(frozen=True, slots=True)
class _CheckpointSpecV34:
    profile: str
    preregistration_id: str
    schema_version: str
    future_domains: Mapping[str, str]
    source_episode_ids: tuple[str, ...]
    boards: tuple[tuple[int, ...], ...]
    statuses: tuple[str, ...]
    source_counts: tuple[int, ...]
    decision_limit: int
    cold_indices: tuple[int, ...]
    expected_output_episode_ids: tuple[str, ...]
    expected_new_decision_count: int


def _checkpoint_specs() -> tuple[_CheckpointSpecV34, ...]:
    modules = (v26, v27, v28, v29, v30, v31, v32, v33)
    next_ids = (
        v27.CHECKPOINT_EPISODE_IDS,
        v28.CHECKPOINT_EPISODE_IDS,
        v29.CHECKPOINT_EPISODE_IDS,
        v30.CHECKPOINT_EPISODE_IDS,
        v31.CHECKPOINT_EPISODE_IDS,
        v32.CHECKPOINT_EPISODE_IDS,
        v33.CHECKPOINT_EPISODE_IDS,
        FINAL_EPISODE_IDS,
    )
    expected = (128, 128, 128, 256, 512, 938, 765, 204)
    result = []
    for module, outputs, expected_count in zip(
        modules, next_ids, expected, strict=True
    ):
        starts = tuple(
            module.SOURCE_DECISION_COUNTS
            if hasattr(module, "SOURCE_DECISION_COUNTS")
            else (module.GLOBAL_DECISION_START,) * 4
        )
        statuses = tuple(getattr(module, "CHECKPOINT_STATUSES", ("ACTIVE",) * 4))
        result.append(
            _CheckpointSpecV34(
                module.PROFILE_KEY.removeprefix(
                    "construction_k7_standard_2048_expression_exact_checkpoint_"
                ).upper(),
                module.PREREGISTRATION_ID,
                module.SCHEMA_VERSION,
                module.FUTURE_DOMAINS,
                tuple(module.CHECKPOINT_EPISODE_IDS),
                tuple(module.CHECKPOINT_BOARDS),
                statuses,
                starts,
                module.SEGMENT_DECISION_LIMIT,
                tuple(module.LOCAL_COLD_CHECKPOINTS),
                tuple(outputs),
                expected_count,
            )
        )
    return tuple(result)


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _add_mapping(
    counters: runtime.NativeCounterSetV34, values: Mapping[str, int]
) -> None:
    registry = registry_v9.official_counter_registry_v9()
    if set(values) != set(registry.by_path):
        _fail("worker native counter mapping changed")
    for path, value in values.items():
        if value:
            counters.add(path, value)


def _checkpoint_episode(
    spec: _CheckpointSpecV34,
    episode_index: int,
) -> tuple[dict[str, Any], Mapping[str, int], Mapping[str, int], int]:
    state = state_from_board_v1(spec.boards[episode_index])
    if state.status.value != spec.statuses[episode_index]:
        _fail("checkpoint source status changed")
    initial = _state_document(state)
    operational = runtime.NativeCounterSetV34()
    evaluation = runtime.NativeCounterSetV34()
    session = planner.create_expression_planning_session_v1(
        expression_ast={
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 1,
        },
        threshold=2,
        base_probability=Fraction(1, 10),
        override_probability=Fraction(3, 20),
        horizon=3,
    )
    decisions = []
    for local_index in range(spec.decision_limit):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        global_index = spec.source_counts[episode_index] + local_index
        model = session.plan_root(state)
        if model.get("target_transition_accessed") is not False:
            _fail("checkpoint model accessed target before certificate")
        certificate_payload = {
            "schema": f"acfqp.standard_2048_expression_checkpoint_certificate.{spec.profile.lower()}",
            "schema_version": spec.schema_version,
            "expression_checkpoint_preregistration_id": spec.preregistration_id,
            "expression_world_model_id": pre.WORLD_MODEL_ID,
            "source_episode_id": spec.source_episode_ids[episode_index],
            "episode_index": episode_index,
            "local_decision_index": local_index,
            "global_decision_index": global_index,
            "root_state": _state_document(state),
            "planning_horizon": 3,
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
            "operational_target_probability_query_count": 0,
            "operational_ground_state_action_row_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_CHECKPOINT_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "expression_checkpoint_certificate_id": content_id(
                spec.future_domains["certificate"], certificate_payload
            ),
        }
        cold = None
        if local_index in spec.cold_indices:
            cold, values = runtime.evaluate_ground_root_with_native_counters_v34(
                state,
                outcome_provider=target.target_outcomes_v22,
                horizon=3,
            )
            _add_mapping(evaluation, values)
            if (
                cold["root_action_exact_values"]
                != model["root_action_exact_values"]
                or cold["selected_action"] != model["selected_action"]
            ):
                _fail("checkpoint cold replay differs from world model")
        selected = Swipe2048Action(model["selected_action"])
        outcomes = target.target_outcomes_v22(state, selected)
        _add_mapping(
            operational,
            runtime.operational_decision_counter_values_v34(
                model=model, target_outcome_count=len(outcomes)
            ),
        )
        outcome, tape = select_seeded_outcome_v1(
            outcomes,
            seed=long_pre.EPISODE_SEEDS[episode_index],
            decision_index=global_index,
        )
        decisions.append(
            {
                "local_decision_index": local_index,
                "global_decision_index": global_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "CHECKPOINT_EXPRESSION_WORLD_MODEL_CERTIFIED",
                "cold_target_checkpoint": cold,
                "checkpoint_root_values_and_action_exactly_equal": cold is None
                or (
                    cold["root_action_exact_values"]
                    == model["root_action_exact_values"]
                    and cold["selected_action"] == model["selected_action"]
                ),
                "certificate_frozen_before_cold_checkpoint_and_target_transition": True,
                "executed_action": selected.value,
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    checkpoints = [row for row in decisions if row["cold_target_checkpoint"] is not None]
    payload = {
        "schema": f"acfqp.standard_2048_expression_checkpoint_episode.{spec.profile.lower()}",
        "schema_version": spec.schema_version,
        "expression_checkpoint_preregistration_id": spec.preregistration_id,
        "expression_world_model_id": pre.WORLD_MODEL_ID,
        "source_episode_id": spec.source_episode_ids[episode_index],
        "episode_index": episode_index,
        "execution_seed": long_pre.EPISODE_SEEDS[episode_index],
        "global_decision_start_inclusive": spec.source_counts[episode_index],
        "initial_state": initial,
        "decisions": decisions,
        "segment_decision_count": len(decisions),
        "cumulative_decision_count": spec.source_counts[episode_index] + len(decisions),
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_CHECKPOINT_LIMIT"
        ),
        "model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "additional_model_acquisition_label_count": 0,
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoints
        ),
        "factored_action_row_evaluation_count": sum(
            row["certificate"]["factored_action_row_evaluation_count"]
            for row in decisions
        ),
        "factored_support_outcome_evaluation_count": sum(
            row["certificate"]["factored_support_outcome_evaluation_count"]
            for row in decisions
        ),
        "subproof_cache_hit_count": sum(
            row["certificate"]["subproof_cache_hit_count"] for row in decisions
        ),
        "subproof_cache_miss_count": sum(
            row["certificate"]["subproof_cache_miss_count"] for row in decisions
        ),
        "cross_decision_subproof_cache_hit_count": sum(
            row["certificate"]["cross_decision_subproof_cache_hit_count"]
            for row in decisions
        ),
        "final_state": _state_document(state),
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
    }
    episode = {
        **payload,
        "expression_checkpoint_episode_id": content_id(
            spec.future_domains["episode"], payload
        ),
    }
    if (
        episode["expression_checkpoint_episode_id"]
        != spec.expected_output_episode_ids[episode_index]
    ):
        _fail(
            "checkpoint episode identity differs from frozen predecessor chain: "
            + episode["expression_checkpoint_episode_id"]
        )
    return episode, operational.freeze(), evaluation.freeze(), len(checkpoints)


def _initial_episode(
    episode_index: int,
) -> tuple[dict[str, Any], Mapping[str, int], Mapping[str, int], int]:
    task = v24_campaign._episode_task(  # noqa: SLF001
        episode_index, long_pre.MAXIMUM_DECISIONS_PER_EPISODE
    )
    episode_bytes, _ = v24_campaign._episode_worker(task)  # noqa: SLF001
    episode = loads_canonical_json(episode_bytes)
    if (
        type(episode) is not dict
        or episode.get("expression_accounted_episode_id")
        != v26.CHECKPOINT_EPISODE_IDS[episode_index]
    ):
        _fail("initial accounted episode identity changed")
    operational = runtime.NativeCounterSetV34()
    evaluation = runtime.NativeCounterSetV34()
    checkpoints = 0
    for decision in episode["decisions"]:
        _add_mapping(operational, decision["operational_counter_values"])
        if decision["evaluation_counter_values"] is not None:
            _add_mapping(evaluation, decision["evaluation_counter_values"])
            checkpoints += 1
    return episode, operational.freeze(), evaluation.freeze(), checkpoints


def _task_document(
    *, profile: str, episode_index: int, source_episode_id: str | None
) -> bytes:
    payload = {
        "schema": "acfqp.standard_2048_expression_full_accounting_task.v34",
        "schema_version": SCHEMA_VERSION,
        "expression_full_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "profile": profile,
        "episode_index": episode_index,
        "source_episode_id": source_episode_id,
        "native_counter_window": True,
    }
    identity = content_id(pre.FUTURE_DOMAINS["measurement"], payload)
    return canonical_json_bytes(
        {**payload, "expression_full_accounting_measurement_id": identity}
    )


def _worker(task_bytes: bytes) -> tuple[bytes, int, int]:
    task = loads_canonical_json(task_bytes)
    if type(task) is not dict or set(task) != {
        "schema",
        "schema_version",
        "expression_full_accounting_preregistration_id",
        "profile",
        "episode_index",
        "source_episode_id",
        "native_counter_window",
        "expression_full_accounting_measurement_id",
    }:
        _fail("full accounting task is not canonical")
    payload = {
        key: value
        for key, value in task.items()
        if key != "expression_full_accounting_measurement_id"
    }
    if (
        content_id(pre.FUTURE_DOMAINS["measurement"], payload)
        != task.get("expression_full_accounting_measurement_id")
        or task.get("expression_full_accounting_preregistration_id")
        != pre.PREREGISTRATION_ID
    ):
        _fail("full accounting task identity changed")
    profile = task["profile"]
    episode_index = task["episode_index"]
    if (
        task.get("schema")
        != "acfqp.standard_2048_expression_full_accounting_task.v34"
        or task.get("schema_version") != SCHEMA_VERSION
        or task.get("native_counter_window") is not True
        or type(episode_index) is not int
        or not 0 <= episode_index < 4
    ):
        _fail("full accounting task semantics changed")
    if profile == "V24_INITIAL_32":
        if task.get("source_episode_id") is not None:
            _fail("initial segment gained a source episode")
        episode, operational, evaluation, checkpoints = _initial_episode(
            episode_index
        )
    else:
        specs = {row.profile: row for row in _checkpoint_specs()}
        if profile not in specs:
            _fail("unknown full accounting segment profile")
        if (
            task.get("source_episode_id")
            != specs[profile].source_episode_ids[episode_index]
        ):
            _fail("checkpoint task source episode changed")
        episode, operational, evaluation, checkpoints = _checkpoint_episode(
            specs[profile], episode_index
        )
    reply_payload = {
        "schema": "acfqp.standard_2048_expression_full_accounting_worker_reply.v34",
        "schema_version": SCHEMA_VERSION,
        "expression_full_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "task_id": task["expression_full_accounting_measurement_id"],
        "profile": profile,
        "episode_index": episode_index,
        "episode": episode,
        "operational_counter_values": dict(operational),
        "evaluation_counter_values": dict(evaluation),
        "cold_evaluation_checkpoint_count": checkpoints,
        "summary_to_counter_translation_used": False,
    }
    reply_id = content_id(pre.FUTURE_DOMAINS["segment"], reply_payload)
    raw = canonical_json_bytes(
        {**reply_payload, "expression_full_accounting_segment_id": reply_id}
    )
    return raw, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, os.getpid()


@dataclass(frozen=True, slots=True)
class _WorkerReplyV34:
    task_bytes: bytes
    reply_bytes: bytes
    reply: Mapping[str, Any]
    observed_working_peak: int
    worker_pid: int


def _run_segment_workers(
    profile: str, active_rows: tuple[tuple[int, str | None], ...]
) -> tuple[_WorkerReplyV34, ...]:
    tasks = tuple(
        _task_document(
            profile=profile,
            episode_index=episode_index,
            source_episode_id=source_id,
        )
        for episode_index, source_id in active_rows
    )
    if not tasks:
        return ()
    results_list = []
    for start in range(0, len(tasks), pre.MAXIMUM_WORKER_PROCESSES):
        batch = tasks[start : start + pre.MAXIMUM_WORKER_PROCESSES]
        executors = [ProcessPoolExecutor(max_workers=1) for _ in batch]
        try:
            futures = [
                executor.submit(_worker, task)
                for executor, task in zip(executors, batch, strict=True)
            ]
            results_list.extend(future.result() for future in futures)
        finally:
            for executor in executors:
                executor.shutdown(wait=True, cancel_futures=True)
    results = tuple(results_list)
    replies = []
    for task_bytes, (reply_bytes, observed_peak, worker_pid) in zip(
        tasks, results, strict=True
    ):
        reply = loads_canonical_json(reply_bytes)
        if (
            type(reply) is not dict
            or type(observed_peak) is not int
            or observed_peak < 0
            or observed_peak > pre.WORKER_WORKING_BYTES_PEAK_UPPER
            or type(worker_pid) is not int
            or worker_pid <= 1
        ):
            _fail("full accounting worker reply changed")
        replies.append(
            _WorkerReplyV34(
                task_bytes, reply_bytes, reply, observed_peak, worker_pid
            )
        )
    return tuple(replies)


def _subject_id(role: str, evidence: Mapping[str, Any]) -> str:
    payload = {
        "schema": "acfqp.standard_2048_expression_full_accounting_subject.v34",
        "schema_version": SCHEMA_VERSION,
        "expression_full_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "role": role,
        "evidence": dict(evidence),
    }
    return content_id(pre.FUTURE_DOMAINS["measurement"], payload)


def _bundle_summary(
    bundle: artifacts.MaterializedOperationalBundleV34
    | artifacts.MaterializedEvaluationBundleV34,
    *,
    output_root: Path,
) -> dict[str, Any]:
    document = bundle.to_document()
    comparison = document["comparison_vector"]
    return {
        "counter_bundle_id": bundle.bundle_id,
        "window_role": document["window_role"],
        "work_vector_id": document["work_vector"]["work_vector_id"],
        "comparison_vector_id": (
            None if comparison is None else comparison["comparison_vector_id"]
        ),
        "actual_projection_proof_id": (
            None
            if document["actual_projection_proof"] is None
            else document["actual_projection_proof"]["actual_projection_proof_id"]
        ),
        "native_zero_attestation_id": document["native_zero_attestation"][
            "native_zero_attestation_id"
        ],
        "output_key": bundle.output_path.relative_to(output_root).as_posix(),
        "canonical_byte_count": len(bundle.canonical_bytes),
        "canonical_sha256": hashlib.sha256(bundle.canonical_bytes).hexdigest(),
        "charged_output_bytes": document["output_bytes_fixed_point"],
    }


def _accumulate_comparison(
    current: dict[str, int], values: tuple[tuple[str, int], ...]
) -> dict[str, int]:
    reducers = {
        row.name: row.reducer
        for row in registry_v9.official_comparison_profile_v9().axes
    }
    result = dict(current)
    for axis, value in values:
        if reducers[axis] is ReducerEnum.SUM:
            result[axis] += value
        else:
            result[axis] = max(result[axis], value)
    return result


def _tree_file_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _materialize_campaign(output_root: Path) -> dict[str, Any]:
    preregistration = pre.verify_standard_2048_expression_full_accounting_preregistration_v34(
        pre.freeze_standard_2048_expression_full_accounting_preregistration_v34()
    )
    if output_root.exists():
        _fail("full accounting output root must be absent")
    output_root.mkdir(mode=0o700, parents=False)
    model_dir = output_root / "model"
    model_dir.mkdir(mode=0o700)

    operational_trace, acquisition_values, proof_values = (
        v24_campaign._instrumented_model_synthesis("OPERATIONAL")  # noqa: SLF001
    )
    evaluation_trace, model_evaluation_values, empty_proof_values = (
        v24_campaign._instrumented_model_synthesis("EVALUATION")  # noqa: SLF001
    )
    if any(empty_proof_values.values()):
        _fail("model evaluation unexpectedly split stages")
    acquisition_evidence = {
        "structural_pool": operational_trace["structural_pool"],
        "acquisitions": operational_trace["acquisitions"],
        "proposal": operational_trace["proposal"],
        "actual_target_probability_query_invocations": 4,
        "duplicate_label_query_for_artifact_recording": False,
    }
    acquisition_bundle = artifacts.materialize_operational_bundle_v34(
        subject_id=_subject_id("MODEL_ACQUISITION_AND_SELECTION", acquisition_evidence),
        window_role="MODEL_ACQUISITION_AND_SELECTION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=acquisition_values,
        evidence_document=acquisition_evidence,
        output_path=model_dir / "operational-acquisition.json",
    )
    proof_evidence = {
        "proposal_id": operational_trace["proposal"]["blind_expression_proposal_id"],
        "proof": operational_trace["proof"],
        "world_model": operational_trace["world_model"],
    }
    proof_bundle = artifacts.materialize_operational_bundle_v34(
        subject_id=_subject_id("MODEL_PROOF_AND_FREEZE", proof_evidence),
        window_role="MODEL_PROOF_AND_FREEZE",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=proof_values,
        evidence_document=proof_evidence,
        output_path=model_dir / "operational-proof.json",
    )
    model_eval_evidence = {
        "proposal_id": evaluation_trace["proposal"]["blind_expression_proposal_id"],
        "proof_id": evaluation_trace["proof"]["blind_expression_proof_id"],
        "world_model_id": evaluation_trace["world_model"]["blind_expression_world_model_id"],
    }
    model_evaluation_bundle = artifacts.materialize_evaluation_bundle_v34(
        subject_id=_subject_id("MODEL_SYNTHESIS_STANDALONE_REPLAY", model_eval_evidence),
        window_role="MODEL_SYNTHESIS_STANDALONE_REPLAY",
        base_values=model_evaluation_values,
        evidence_document=evaluation_trace,
        output_path=model_dir / "evaluation-replay.json",
    )
    operational_bundles = [acquisition_bundle, proof_bundle]
    evaluation_bundles = [model_evaluation_bundle]
    segment_summaries = []

    segment_rows: list[
        tuple[
            str,
            tuple[tuple[int, str | None], ...],
            tuple[dict[str, Any], ...],
            int,
        ]
    ] = [
        (
            "V24_INITIAL_32",
            tuple((index, None) for index in range(4)),
            (),
            128,
        )
    ]
    for spec in _checkpoint_specs():
        terminal_rows = []
        for index, status in enumerate(spec.statuses):
            if status == "ACTIVE":
                continue
            terminal_episode, operational, evaluation, checkpoints = (
                _checkpoint_episode(spec, index)
            )
            if (
                any(operational.values())
                or any(evaluation.values())
                or checkpoints
                or terminal_episode["segment_decision_count"] != 0
            ):
                _fail("terminal carry-forward emitted route work")
            terminal_rows.append(
                {
                    "episode_index": index,
                    "source_episode_id": spec.source_episode_ids[index],
                    "output_episode_id": terminal_episode[
                        "expression_checkpoint_episode_id"
                    ],
                    "source_status": status,
                    "source_board_ranks": list(spec.boards[index]),
                    "cumulative_decision_count": spec.source_counts[index],
                    "decision_count": 0,
                    "route_work_vector_id": None,
                    "zero_decision_work": True,
                    "retained_in_campaign_denominator": True,
                }
            )
        segment_rows.append(
            (
                spec.profile,
                tuple(
                    (index, spec.source_episode_ids[index])
                    for index, status in enumerate(spec.statuses)
                    if status == "ACTIVE"
                ),
                tuple(terminal_rows),
                spec.expected_new_decision_count,
            )
        )

    terminal_carry_forward_count = 0
    for segment_ordinal, (
        profile,
        active_rows,
        terminal_rows,
        expected_count,
    ) in enumerate(
        segment_rows
    ):
        segment_dir = output_root / f"segment-{segment_ordinal:02d}-{profile.lower()}"
        segment_dir.mkdir(mode=0o700)
        replies = _run_segment_workers(profile, active_rows)
        episode_rows = []
        segment_decisions = 0
        segment_cold = 0
        worker_pids = set()
        for reply in replies:
            episode = reply.reply["episode"]
            episode_index = reply.reply["episode_index"]
            segment_decision_count = len(episode["decisions"])
            segment_decisions += segment_decision_count
            segment_cold += reply.reply["cold_evaluation_checkpoint_count"]
            worker_pids.add(reply.worker_pid)
            values = runtime.NativeCounterSetV34()
            _add_mapping(values, reply.reply["operational_counter_values"])
            values.add("common.hash_invocations", 2)
            values.add("common.integrity_checks", 2)
            values.add("common.protocol_checks", 2)
            values.add("io.staged_bytes", len(reply.task_bytes))
            values.add("io.read_bytes", len(reply.task_bytes) + len(reply.reply_bytes))
            values.maximum("memory.working_bytes_peak", pre.WORKER_WORKING_BYTES_PEAK_UPPER)
            episode_id = episode.get("expression_accounted_episode_id") or episode.get(
                "expression_checkpoint_episode_id"
            )
            bundle = artifacts.materialize_operational_bundle_v34(
                subject_id=episode_id,
                window_role="SEGMENT_EPISODE_PLANNING_AND_TARGET_EXECUTION",
                route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
                work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
                base_values=values.freeze(),
                evidence_document={
                    "task": loads_canonical_json(reply.task_bytes),
                    "worker_reply": reply.reply,
                    "worker_reply_sha256": hashlib.sha256(reply.reply_bytes).hexdigest(),
                    "worker_reply_byte_count": len(reply.reply_bytes),
                    "observed_worker_ru_maxrss_within_preregistered_cap": True,
                },
                output_path=segment_dir / f"episode-{episode_index:04d}-operational.json",
                external_output_bytes=len(reply.reply_bytes),
            )
            operational_bundles.append(bundle)
            evaluation_summary = None
            if reply.reply["cold_evaluation_checkpoint_count"]:
                eval_bundle = artifacts.materialize_evaluation_bundle_v34(
                    subject_id=episode_id,
                    window_role="SEGMENT_COLD_CHECKPOINT_STANDALONE_REPLAY",
                    base_values=reply.reply["evaluation_counter_values"],
                    evidence_document={
                        "profile": profile,
                        "episode_index": episode_index,
                        "episode_id": episode_id,
                        "cold_evaluation_checkpoint_count": reply.reply[
                            "cold_evaluation_checkpoint_count"
                        ],
                    },
                    output_path=segment_dir / f"episode-{episode_index:04d}-evaluation.json",
                )
                evaluation_bundles.append(eval_bundle)
                evaluation_summary = _bundle_summary(eval_bundle, output_root=output_root)
            episode_rows.append(
                {
                    "episode_index": episode_index,
                    "episode_id": episode_id,
                    "source_episode_id": reply.reply.get("task_id"),
                    "decision_count": segment_decision_count,
                    "closure_reason": episode["closure_reason"],
                    "final_state": episode["final_state"],
                    "tile_2048_reached": episode["tile_2048_reached"],
                    "operational_bundle": _bundle_summary(bundle, output_root=output_root),
                    "evaluation_bundle": evaluation_summary,
                }
            )
        expected_process_count = len(replies)
        maximum_concurrent_process_count = min(
            pre.MAXIMUM_WORKER_PROCESSES, len(replies)
        )
        if len(worker_pids) != expected_process_count:
            _fail("worker process launch cardinality changed")
        process_summary = None
        if replies:
            process_values = runtime.NativeCounterSetV34()
            process_values.add("process.launches", expected_process_count)
            process_values.add("process.exit_successes", expected_process_count)
            process_values.add("common.protocol_checks", expected_process_count)
            process_values.add("common.integrity_checks", expected_process_count)
            process_values.add("common.hash_invocations")
            process_evidence = {
                "profile": profile,
                "task_count": len(replies),
                "worker_process_count": expected_process_count,
                "maximum_concurrent_worker_process_count": (
                    maximum_concurrent_process_count
                ),
                "maximum_tasks_per_worker_process": (
                    pre.MAXIMUM_TASKS_PER_WORKER_PROCESS
                ),
                "all_worker_replies_received": True,
            }
            process_bundle = artifacts.materialize_operational_bundle_v34(
                subject_id=_subject_id(
                    "SEGMENT_PROCESS_SUPERVISION", process_evidence
                ),
                window_role="SEGMENT_PROCESS_SUPERVISION",
                route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
                work_scope=ActualWorkScope.COMMON_PREFIX,
                base_values=process_values.freeze(),
                evidence_document=process_evidence,
                output_path=segment_dir / "process-supervision.json",
            )
            operational_bundles.append(process_bundle)
            process_summary = _bundle_summary(
                process_bundle, output_root=output_root
            )
        if segment_decisions != expected_count:
            _fail("full accounting segment decision total changed")
        segment_summaries.append(
            {
                "segment_ordinal": segment_ordinal,
                "profile": profile,
                "active_worker_count": len(replies),
                "terminal_carry_forward_count": len(terminal_rows),
                "terminal_carry_forward": list(terminal_rows),
                "decision_count": segment_decisions,
                "cold_evaluation_checkpoint_count": segment_cold,
                "process_bundle": process_summary,
                "episodes": sorted(episode_rows, key=lambda row: row["episode_index"]),
            }
        )
        terminal_carry_forward_count += len(terminal_rows)

    complete_decision_count = sum(row["decision_count"] for row in segment_summaries)
    if complete_decision_count != pre.EXPECTED_COMPLETE_DECISION_COUNT:
        _fail("complete native decision count changed")
    mounted_before = _tree_file_bytes(output_root)
    if mounted_before > pre.MAXIMUM_ACCOUNTING_OUTPUT_BYTES:
        _fail("accounting output exceeded preregistered cap")
    campaign_evidence = {
        "segment_profiles": [row["profile"] for row in segment_summaries],
        "segment_decision_counts": [row["decision_count"] for row in segment_summaries],
        "complete_decision_count": complete_decision_count,
        "final_episode_ids": list(FINAL_EPISODE_IDS),
        "won_occurrence_count": 2,
        "lost_occurrence_count": 2,
    }
    campaign_values = runtime.NativeCounterSetV34()
    campaign_values.add("common.hash_invocations", 3 + terminal_carry_forward_count)
    campaign_values.add("common.integrity_checks", 4 + terminal_carry_forward_count)
    campaign_values.add("common.protocol_checks", 4 + terminal_carry_forward_count)
    campaign_values.maximum("io.mounted_bytes_peak", mounted_before)
    campaign_values.maximum("memory.working_bytes_peak", pre.PARENT_WORKING_BYTES_PEAK_UPPER)
    campaign_bundle = artifacts.materialize_operational_bundle_v34(
        subject_id=_subject_id("CAMPAIGN_AGGREGATION_AND_TERMINALIZATION", campaign_evidence),
        window_role="CAMPAIGN_AGGREGATION_AND_TERMINALIZATION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=campaign_values.freeze(),
        evidence_document=campaign_evidence,
        output_path=output_root / "campaign.json",
    )
    operational_bundles.append(campaign_bundle)

    totals = {axis: 0 for axis in SHARED_AXES}
    prefix = []
    for sequence_index, bundle in enumerate(operational_bundles):
        totals = _accumulate_comparison(totals, bundle.chain.comparison_vector.values)
        prefix.append(
            {
                "sequence_index": sequence_index,
                "work_vector_id": bundle.chain.work_vector.work_vector_id,
                "comparison_vector_id": bundle.chain.comparison_vector.comparison_vector_id,
                "subject_id": bundle.chain.work_vector.subject_id,
                "route_kind": bundle.chain.work_vector.route_kind.value,
                "cumulative_axis_values": [
                    {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
                ],
            }
        )
    registry = registry_v9.official_counter_registry_v9()
    evaluation_totals = {
        path: sum(bundle.work_vector.value(path) for bundle in evaluation_bundles)
        for path in registry.by_path
        if path.startswith("evaluation.")
    }
    payload = {
        "schema": "acfqp.standard_2048_expression_full_accounted_campaign.v34",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "expression_full_accounting_preregistration": preregistration.to_document(),
        "model_operational_bundles": [
            _bundle_summary(acquisition_bundle, output_root=output_root),
            _bundle_summary(proof_bundle, output_root=output_root),
        ],
        "model_evaluation_bundle": _bundle_summary(
            model_evaluation_bundle, output_root=output_root
        ),
        "segments": segment_summaries,
        "segment_count": len(segment_summaries),
        "logical_occurrence_count": 4,
        "complete_decision_count": complete_decision_count,
        "model_certificate_count": complete_decision_count,
        "won_occurrence_count": 2,
        "lost_occurrence_count": 2,
        "terminal_occurrence_count": 4,
        "operational_work_vector_count": len(operational_bundles),
        "evaluation_work_vector_count": len(evaluation_bundles),
        "campaign_bundle": _bundle_summary(campaign_bundle, output_root=output_root),
        "vector_prefix_totals": prefix,
        "final_operational_comparison_totals": [
            {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
        ],
        "evaluation_lane_totals": evaluation_totals,
        "operational_target_probability_label_query_count": 4,
        "unique_operational_target_probability_label_count": 4,
        "additional_operational_target_probability_label_count": 0,
        "strict_no_prior_target_probability_label_count": 8,
        "target_probability_label_fraction_of_no_prior": Fraction(1, 2),
        "certified_decisions_per_acquired_target_label": Fraction(
            complete_decision_count, 4
        ),
        "all_3187_decisions_rerun_under_native_counter_windows": True,
        "all_required_counter_leaves_have_explicit_native_records": True,
        "all_nine_shared_resource_paths_have_measurement_receipts": True,
        "evaluation_replay_excluded_from_operational_comparison": True,
        "terminal_occurrences_retained_in_denominator": True,
        "summary_to_counter_translation_used": False,
        "registered_profile_counter_completeness_candidate": True,
        "full_standard_2048_campaign_terminalized": True,
        "tile_2048_reached": True,
        "sample_tax_reduced_on_registered_label_axis": True,
        "broad_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "expression_full_accounted_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionFullAccountedCampaignV34:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    output_root: Path = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.canonical_bytes) is not bytes
            or not isinstance(self.output_root, Path)
        ):
            _fail("full accounted campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("full accounted campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_full_accounted_campaign_id"
        }
        if (
            document.get("expression_full_accounted_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("full accounted campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("full accounted campaign is not an object")
        return document


def run_standard_2048_expression_full_accounted_campaign_v34(
    output_root: Path,
) -> Standard2048ExpressionFullAccountedCampaignV34:
    if not isinstance(output_root, Path):
        _fail("full accounted campaign output root must be one Path")
    document = _materialize_campaign(output_root)
    raw = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["expression_full_accounted_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen full accounted campaign changed")
    return Standard2048ExpressionFullAccountedCampaignV34(
        _ISSUER,
        raw,
        document["expression_full_accounted_campaign_id"],
        output_root,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048ExpressionFullAccountedCampaignV34",
    "run_standard_2048_expression_full_accounted_campaign_v34",
)
