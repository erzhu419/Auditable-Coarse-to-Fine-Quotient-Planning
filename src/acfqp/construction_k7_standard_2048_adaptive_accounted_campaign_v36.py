"""Rerun the V35 adaptive workload under V9 native counter windows."""

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
from acfqp import construction_k7_standard_2048_adaptive_accounting_artifacts_v36 as artifacts
from acfqp import construction_k7_standard_2048_adaptive_accounting_preregistration_v36 as pre
from acfqp import construction_k7_standard_2048_adaptive_accounting_runtime_v36 as runtime
from acfqp import construction_k7_standard_2048_adaptive_expression_campaign_v35 as v35
from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35_pre
from acfqp import construction_k7_standard_2048_adaptive_expression_target_v35 as target
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.accounting_v1 import RouteKindEnum, SHARED_AXES
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_adaptive_expression_accounted_campaign_v36"
V35_CAMPAIGN_ID = "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
V35_VERIFICATION_ID = "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"
EXPECTED_CAMPAIGN_ID = "758f01ac78789d25512b218ed16b8ca4bfaa95a08dc52e81fc15601b42662693"
EXPECTED_CANONICAL_BYTE_COUNT = 250414
EXPECTED_CANONICAL_SHA256 = "da3432bf18e4aa94091456f9ab09b1809258fa60dae9cd89aec93daa5dee6030"
COLD_CHECKPOINTS = (0, 63, 127)


class ConstructionK7Standard2048AdaptiveAccountedCampaignV36Error(RuntimeError):
    """The V35 replay, native window, bundle, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveAccountedCampaignV36Error(message)


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _fraction(value: Any) -> Fraction:
    if type(value) is Fraction:
        return value
    if type(value) is not dict or set(value) != {"numerator", "denominator"}:
        _fail("adaptive-accounting rational document changed")
    return Fraction(value["numerator"], value["denominator"])


def _add_mapping(
    counters: runtime.NativeCounterSetV36, values: Mapping[str, int]
) -> None:
    counters.merge(values)


def _subject_id(role: str, evidence: Mapping[str, Any]) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["measurement"],
        {"window_role": role, "evidence": dict(evidence)},
    )


def _directory_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _bundle_summary(bundle: Any, *, output_root: Path) -> dict[str, Any]:
    document = bundle.to_document()
    vector = document["work_vector"]
    comparison = document["comparison_vector"]
    return {
        "counter_bundle_id": bundle.bundle_id,
        "output_key": bundle.output_path.relative_to(output_root).as_posix(),
        "canonical_byte_count": len(bundle.canonical_bytes),
        "canonical_sha256": hashlib.sha256(bundle.canonical_bytes).hexdigest(),
        "subject_id": vector["subject_id"],
        "work_vector_id": vector["work_vector_id"],
        "comparison_vector_id": (
            None if comparison is None else comparison["comparison_vector_id"]
        ),
        "lane": document["measurement"]["lane"],
    }


def _verify_v35_inputs(
    campaign_bytes: bytes, verification_bytes: bytes
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        V35_CAMPAIGN_ID == "0" * 64
        or V35_VERIFICATION_ID == "0" * 64
    ):
        _fail("V35 semantic predecessor has not been frozen")
    campaign = loads_canonical_json(campaign_bytes)
    verification = loads_canonical_json(verification_bytes)
    if (
        type(campaign) is not dict
        or type(verification) is not dict
        or canonical_json_bytes(campaign) != campaign_bytes
        or canonical_json_bytes(verification) != verification_bytes
    ):
        _fail("V35 predecessor bytes are not canonical")
    campaign_payload = {
        key: value
        for key, value in campaign.items()
        if key != "adaptive_expression_campaign_id"
    }
    verification_payload = {
        key: value
        for key, value in verification.items()
        if key != "adaptive_expression_verification_id"
    }
    if (
        campaign.get("adaptive_expression_campaign_id") != V35_CAMPAIGN_ID
        or content_id(v35_pre.FUTURE_DOMAINS["campaign"], campaign_payload)
        != V35_CAMPAIGN_ID
        or verification.get("adaptive_expression_verification_id")
        != V35_VERIFICATION_ID
        or content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
            verification_payload,
        )
        != V35_VERIFICATION_ID
        or verification.get("adaptive_expression_campaign_id") != V35_CAMPAIGN_ID
        or verification.get("campaign_replay_result") != "PASS"
    ):
        _fail("V35 campaign or independent verification binding changed")
    return campaign, verification


def _worker_task_v36(
    *,
    episode_index: int,
    initial_board: tuple[int, ...],
    execution_seed: str,
    overlay: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.standard_2048_adaptive_accounting_worker_task.v36",
        "schema_version": SCHEMA_VERSION,
        "adaptive_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode_index,
        "initial_board_ranks": list(initial_board),
        "execution_seed": execution_seed,
        "overlay": overlay,
        "candidate": candidate,
    }


def _domain_board_from_worker_task_v36(task: dict[str, Any]) -> tuple[int, ...]:
    values = task.get("initial_board_ranks")
    if (
        type(values) is not list
        or len(values) != 16
        or any(type(value) is not int for value in values)
    ):
        _fail("V36 worker board representation changed")
    return tuple(values)


def _accounted_episode(
    task: dict[str, Any],
) -> tuple[bytes, int, int]:
    if (
        type(task) is not dict
        or set(task)
        != {
            "schema",
            "schema_version",
            "adaptive_accounting_preregistration_id",
            "episode_index",
            "initial_board_ranks",
            "execution_seed",
            "overlay",
            "candidate",
        }
        or task["schema"]
        != "acfqp.standard_2048_adaptive_accounting_worker_task.v36"
        or task["schema_version"] != SCHEMA_VERSION
        or task["adaptive_accounting_preregistration_id"]
        != pre.PREREGISTRATION_ID
        or type(task["episode_index"]) is not int
        or type(task["initial_board_ranks"]) is not list
        or len(task["initial_board_ranks"]) != 16
        or any(type(value) is not int for value in task["initial_board_ranks"])
        or type(task["execution_seed"]) is not str
        or type(task["overlay"]) is not dict
        or type(task["candidate"]) is not dict
    ):
        _fail("V36 worker task schema changed")
    episode_index = task["episode_index"]
    initial_board = _domain_board_from_worker_task_v36(task)
    seed = task["execution_seed"]
    overlay = task["overlay"]
    candidate_document = task["candidate"]
    state = state_from_board_v1(initial_board)
    initial = _state_document(state)
    planning_operational = runtime.NativeCounterSetV36()
    execution_operational = runtime.NativeCounterSetV36()
    evaluation = runtime.NativeCounterSetV36()
    session = planner.create_expression_planning_session_v1(
        expression_ast=candidate_document["expression_ast"],
        threshold=candidate_document["threshold"],
        base_probability=_fraction(candidate_document["base_rank_two_probability"]),
        override_probability=_fraction(
            candidate_document["override_rank_two_probability"]
        ),
        horizon=v35_pre.PLANNING_HORIZON,
    )
    decisions = []
    for decision_index in range(v35_pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = session.plan_root(state)
        _add_mapping(
            planning_operational,
            runtime.planning_decision_counter_values_v36(model=model),
        )
        certificate_payload = {
            "schema": "acfqp.standard_2048_adaptive_expression_certificate.v35",
            "schema_version": v35.SCHEMA_VERSION,
            "adaptive_expression_preregistration_id": v35_pre.PREREGISTRATION_ID,
            "adaptive_expression_overlay_id": overlay[
                "adaptive_expression_overlay_id"
            ],
            "adaptive_expression_proof_id": overlay[
                "adaptive_expression_proof_id"
            ],
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": v35_pre.PLANNING_HORIZON,
            "root_action_exact_values": model["root_action_exact_values"],
            "selected_action": model["selected_action"],
            "selected_expected_merge_score": model[
                "selected_expected_merge_score"
            ],
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
            "operational_target_probability_query_count_after_overlay_freeze": 0,
            "operational_ground_state_action_row_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_PROVED_ADAPTIVE_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "adaptive_expression_certificate_id": content_id(
                CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN,
                certificate_payload,
            ),
        }
        cold = None
        if decision_index in COLD_CHECKPOINTS:
            cold, values = runtime.evaluate_ground_root_with_native_counters_v36(
                state,
                outcome_provider=target.target_outcomes_v35,
                horizon=v35_pre.PLANNING_HORIZON,
            )
            _add_mapping(evaluation, values)
            if (
                cold["root_action_exact_values"] != model["root_action_exact_values"]
                or cold["selected_action"] != model["selected_action"]
            ):
                _fail("V36 cold ground replay differs from adaptive model")
        selected = Swipe2048Action(model["selected_action"])
        outcomes = target.target_outcomes_v35(state, selected)
        _add_mapping(
            execution_operational,
            runtime.execution_transition_counter_values_v36(
                target_outcome_count=len(outcomes)
            ),
        )
        outcome, tape = select_seeded_outcome_v1(
            outcomes, seed=seed, decision_index=decision_index
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "PROVED_ADAPTIVE_EXPRESSION_WORLD_MODEL",
                "cold_target_checkpoint": cold,
                "checkpoint_root_values_and_action_exactly_equal": cold is None
                or (
                    cold["root_action_exact_values"]
                    == model["root_action_exact_values"]
                    and cold["selected_action"] == model["selected_action"]
                ),
                "certificate_frozen_before_cold_checkpoint_and_target_transition": True,
                "executed_action": model["selected_action"],
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    checkpoints = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_episode.v35",
        "schema_version": v35.SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": v35_pre.PREREGISTRATION_ID,
        "adaptive_expression_overlay_id": overlay[
            "adaptive_expression_overlay_id"
        ],
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial,
        "decisions": decisions,
        "decision_count": len(decisions),
        "maximum_registered_decision_count": v35_pre.MAXIMUM_DECISIONS_PER_EPISODE,
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "model_certificate_count": len(decisions),
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
        "adaptive_expression_episode_id": content_id(
            v35_pre.FUTURE_DOMAINS["episode"], payload
        ),
    }
    reply = {
        "schema": "acfqp.standard_2048_adaptive_accounting_worker_reply.v36",
        "schema_version": SCHEMA_VERSION,
        "adaptive_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "episode": episode,
        "planning_operational_counter_values": dict(
            planning_operational.freeze()
        ),
        "execution_operational_counter_values": dict(
            execution_operational.freeze()
        ),
        "evaluation_counter_values": dict(evaluation.freeze()),
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "summary_to_counter_translation_used": False,
    }
    return (
        canonical_json_bytes(reply),
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        os.getpid(),
    )


@dataclass(frozen=True, slots=True)
class _WorkerReplyV36:
    task_bytes: bytes
    reply_bytes: bytes
    reply: dict[str, Any]
    observed_working_peak: int
    worker_pid: int


def _run_episode_workers(
    tasks: tuple[dict[str, Any], ...]
) -> tuple[_WorkerReplyV36, ...]:
    results = []
    for start in range(0, len(tasks), pre.MAXIMUM_WORKER_PROCESSES):
        batch = tasks[start : start + pre.MAXIMUM_WORKER_PROCESSES]
        task_bytes = tuple(canonical_json_bytes(task) for task in batch)
        executors = [ProcessPoolExecutor(max_workers=1) for _ in batch]
        try:
            futures = [
                executor.submit(_accounted_episode, task)
                for executor, task in zip(executors, batch, strict=True)
            ]
            for raw_task, future in zip(task_bytes, futures, strict=True):
                reply_bytes, peak, pid = future.result()
                if peak > pre.WORKER_WORKING_BYTES_PEAK_UPPER:
                    _fail("V36 worker exceeded preregistered working-set cap")
                reply = loads_canonical_json(reply_bytes)
                if type(reply) is not dict:
                    _fail("V36 worker reply is not an object")
                results.append(
                    _WorkerReplyV36(raw_task, reply_bytes, reply, peak, pid)
                )
        finally:
            for executor in executors:
                executor.shutdown(wait=True, cancel_futures=True)
    results.sort(key=lambda row: row.reply["episode"]["episode_index"])
    return tuple(results)


def _accumulate(
    total: dict[str, int], values: tuple[tuple[str, int], ...]
) -> dict[str, int]:
    result = dict(total)
    for axis, value in values:
        if axis in {"peak_mounted_bytes", "peak_working_bytes"}:
            result[axis] = max(result[axis], value)
        else:
            result[axis] += value
    return result


def _materialize_campaign(
    *,
    v35_campaign: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    preregistration = pre.verify_standard_2048_adaptive_accounting_preregistration_v36(
        pre.freeze_standard_2048_adaptive_accounting_preregistration_v36()
    )
    if output_root.exists():
        _fail("V36 output root must be absent")
    output_root.mkdir(mode=0o700, parents=False)
    model_dir = output_root / "model"
    episode_dir = output_root / "episodes"
    model_dir.mkdir(mode=0o700)
    episode_dir.mkdir(mode=0o700)

    acquired = v35._acquire_model()  # noqa: SLF001
    def materialize_model_stage(
        *, stage: str, role: str, evidence: Mapping[str, Any], filename: str
    ) -> artifacts.MaterializedOperationalBundleV36:
        values = runtime.NativeCounterSetV36()
        _add_mapping(
            values,
            runtime.model_stage_counter_values_v36(
                acquired.operational_counts, stage=stage
            ),
        )
        values.maximum(
            "memory.working_bytes_peak", pre.PARENT_WORKING_BYTES_PEAK_UPPER
        )
        return artifacts.materialize_operational_bundle_v36(
            subject_id=_subject_id(role, evidence),
            window_role=role,
            route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            work_scope=ActualWorkScope.COMMON_PREFIX,
            base_values=values.freeze(),
            evidence_document=evidence,
            output_path=model_dir / filename,
        )

    failure_bundle = materialize_model_stage(
        stage="FAILURE_FRONTIER",
        role="CERTIFICATE_FAILURE_FRONTIER_FREEZE",
        evidence=acquired.failure,
        filename="operational-failure-frontier.json",
    )
    acquisition_evidence = {
        "adaptive_expression_failure_id": acquired.failure[
            "adaptive_expression_failure_id"
        ],
        "expression_acquisitions": list(acquired.acquisitions),
        "actual_target_probability_query_invocations": len(acquired.acquisitions),
        "duplicate_label_query_for_artifact_recording": False,
    }
    acquisition_bundle = materialize_model_stage(
        stage="ACQUISITION",
        role="ADAPTIVE_LABEL_ACQUISITION_AND_CANDIDATE_ELIMINATION",
        evidence=acquisition_evidence,
        filename="operational-acquisition.json",
    )
    proposal_bundle = materialize_model_stage(
        stage="PROPOSAL",
        role="EXPRESSION_PROPOSAL_FREEZE",
        evidence=acquired.proposal,
        filename="operational-proposal.json",
    )
    proof_bundle = materialize_model_stage(
        stage="PROOF",
        role="EXACT_PROGRAM_PROOF",
        evidence=acquired.proof,
        filename="operational-proof.json",
    )
    overlay_bundle = materialize_model_stage(
        stage="OVERLAY",
        role="PROVED_OVERLAY_FREEZE",
        evidence=acquired.overlay,
        filename="operational-overlay.json",
    )

    control_values = runtime.NativeCounterSetV36()
    _add_mapping(
        control_values,
        runtime.no_prior_control_counter_values_v36(
            acquired.control["distinct_context_probability_label_count"]
        ),
    )
    control_bundle = artifacts.materialize_evaluation_bundle_v36(
        subject_id=acquired.control["adaptive_expression_ground_control_id"],
        window_role="MATCHED_FIRST_FRONTIER_NO_PRIOR_CONTROL",
        base_values=control_values.freeze(),
        evidence_document=acquired.control,
        output_path=model_dir / "evaluation-no-prior-control.json",
    )

    candidate_document = acquired.candidate.to_document()
    tasks = tuple(
        _worker_task_v36(
            episode_index=index,
            initial_board=board,
            execution_seed=v35_pre.EPISODE_SEEDS[index],
            overlay=acquired.overlay,
            candidate=candidate_document,
        )
        for index, board in enumerate(v35_pre.INITIAL_BOARDS)
    )
    replies = _run_episode_workers(tasks)
    episode_documents = [reply.reply["episode"] for reply in replies]
    replayed_v35 = v35._assemble_campaign_document(  # noqa: SLF001
        v35_pre.freeze_standard_2048_adaptive_expression_preregistration_v35().to_document(),
        acquired,
        episode_documents,
    )
    replayed_bytes = canonical_json_bytes(replayed_v35)
    if (
        replayed_v35["adaptive_expression_campaign_id"] != V35_CAMPAIGN_ID
        or replayed_bytes != canonical_json_bytes(v35_campaign)
    ):
        _fail("V36 native replay differs from frozen V35 semantic campaign")

    operational_bundles = [
        failure_bundle,
        acquisition_bundle,
        proposal_bundle,
        proof_bundle,
        overlay_bundle,
    ]
    evaluation_bundles = [control_bundle]
    episode_rows = []
    worker_pids = set()
    for reply in replies:
        episode = reply.reply["episode"]
        episode_index = episode["episode_index"]
        episode_id = episode["adaptive_expression_episode_id"]
        worker_pids.add(reply.worker_pid)
        planning_values = runtime.NativeCounterSetV36()
        _add_mapping(
            planning_values,
            reply.reply["planning_operational_counter_values"],
        )
        planning_values.add("common.hash_invocations", 2)
        planning_values.add("common.integrity_checks", 2)
        planning_values.add("common.protocol_checks", 2)
        planning_values.add("io.staged_bytes", len(reply.task_bytes))
        planning_values.add(
            "io.read_bytes", len(reply.task_bytes) + len(reply.reply_bytes)
        )
        planning_values.maximum(
            "memory.working_bytes_peak", pre.WORKER_WORKING_BYTES_PEAK_UPPER
        )
        planning_bundle = artifacts.materialize_operational_bundle_v36(
            subject_id=episode_id,
            window_role="EPISODE_ABSTRACT_PLANNING_AND_CERTIFICATION",
            route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
            base_values=planning_values.freeze(),
            evidence_document={
                "task_sha256": hashlib.sha256(reply.task_bytes).hexdigest(),
                "task_byte_count": len(reply.task_bytes),
                "worker_reply": reply.reply,
                "worker_reply_sha256": hashlib.sha256(
                    reply.reply_bytes
                ).hexdigest(),
                "worker_reply_byte_count": len(reply.reply_bytes),
                "observed_worker_ru_maxrss_within_preregistered_cap": True,
            },
            output_path=episode_dir
            / f"episode-{episode_index:04d}-planning-operational.json",
            external_output_bytes=len(reply.reply_bytes),
        )
        operational_bundles.append(planning_bundle)

        execution_values = runtime.NativeCounterSetV36()
        _add_mapping(
            execution_values,
            reply.reply["execution_operational_counter_values"],
        )
        execution_values.maximum(
            "memory.working_bytes_peak", pre.WORKER_WORKING_BYTES_PEAK_UPPER
        )
        execution_bundle = artifacts.materialize_operational_bundle_v36(
            subject_id=episode_id,
            window_role="EPISODE_SELECTED_TARGET_EXECUTION",
            route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
            base_values=execution_values.freeze(),
            evidence_document={
                "episode_id": episode_id,
                "worker_reply_sha256": hashlib.sha256(
                    reply.reply_bytes
                ).hexdigest(),
                "worker_reply_byte_count": len(reply.reply_bytes),
                "decision_count": episode["decision_count"],
                "execution_counter_values": reply.reply[
                    "execution_operational_counter_values"
                ],
            },
            output_path=episode_dir
            / f"episode-{episode_index:04d}-execution-operational.json",
        )
        operational_bundles.append(execution_bundle)
        evaluation_summary = None
        if reply.reply["cold_evaluation_checkpoint_count"]:
            eval_bundle = artifacts.materialize_evaluation_bundle_v36(
                subject_id=episode_id,
                window_role="COLD_EXACT_GROUND_CHECKPOINT_REPLAY",
                base_values=reply.reply["evaluation_counter_values"],
                evidence_document={
                    "episode_id": episode_id,
                    "episode_index": episode_index,
                    "cold_evaluation_checkpoint_count": reply.reply[
                        "cold_evaluation_checkpoint_count"
                    ],
                },
                output_path=episode_dir
                / f"episode-{episode_index:04d}-evaluation.json",
            )
            evaluation_bundles.append(eval_bundle)
            evaluation_summary = _bundle_summary(
                eval_bundle, output_root=output_root
            )
        episode_rows.append(
            {
                "episode_index": episode_index,
                "v35_episode_id": episode_id,
                "decision_count": episode["decision_count"],
                "closure_reason": episode["closure_reason"],
                "final_state": episode["final_state"],
                "planning_operational_bundle": _bundle_summary(
                    planning_bundle, output_root=output_root
                ),
                "execution_operational_bundle": _bundle_summary(
                    execution_bundle, output_root=output_root
                ),
                "evaluation_bundle": evaluation_summary,
            }
        )
    if len(worker_pids) != len(replies):
        _fail("one-occurrence-per-worker invariant changed")

    process_values = runtime.NativeCounterSetV36()
    process_values.add("process.launches", len(replies))
    process_values.add("process.exit_successes", len(replies))
    process_values.add("common.protocol_checks", len(replies))
    process_values.add("common.integrity_checks", len(replies))
    process_values.add("common.hash_invocations")
    process_evidence = {
        "worker_process_count": len(replies),
        "maximum_concurrent_worker_process_count": min(
            pre.MAXIMUM_WORKER_PROCESSES, len(replies)
        ),
        "maximum_tasks_per_worker_process": pre.MAXIMUM_TASKS_PER_WORKER_PROCESS,
        "all_worker_pids_distinct": True,
    }
    process_bundle = artifacts.materialize_operational_bundle_v36(
        subject_id=_subject_id("PROCESS_SUPERVISION", process_evidence),
        window_role="PROCESS_AND_IO_SUPERVISION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=process_values.freeze(),
        evidence_document=process_evidence,
        output_path=output_root / "process-supervision.json",
    )
    operational_bundles.append(process_bundle)

    mounted_before = _directory_bytes(output_root)
    if mounted_before > pre.MAXIMUM_ACCOUNTING_OUTPUT_BYTES:
        _fail("V36 accounting output exceeded preregistered cap")
    campaign_evidence = {
        "v35_campaign_id": V35_CAMPAIGN_ID,
        "v35_verification_id": V35_VERIFICATION_ID,
        "v35_episode_ids": [
            row["adaptive_expression_episode_id"] for row in episode_documents
        ],
        "decision_count": replayed_v35["decision_count"],
        "ground_distinction_query_count": replayed_v35[
            "ground_distinction_query_count"
        ],
    }
    campaign_values = runtime.NativeCounterSetV36()
    campaign_values.add("common.hash_invocations", 3)
    campaign_values.add("common.integrity_checks", 4)
    campaign_values.add("common.protocol_checks", 4)
    campaign_values.maximum("io.mounted_bytes_peak", mounted_before)
    campaign_values.maximum(
        "memory.working_bytes_peak", pre.PARENT_WORKING_BYTES_PEAK_UPPER
    )
    campaign_bundle = artifacts.materialize_operational_bundle_v36(
        subject_id=_subject_id("CAMPAIGN_AGGREGATION", campaign_evidence),
        window_role="CAMPAIGN_AGGREGATION_AND_TERMINALIZATION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=campaign_values.freeze(),
        evidence_document=campaign_evidence,
        output_path=output_root / "campaign-aggregation.json",
    )
    operational_bundles.append(campaign_bundle)

    totals = {axis: 0 for axis in SHARED_AXES}
    prefix = []
    for sequence_index, bundle in enumerate(operational_bundles):
        totals = _accumulate(totals, bundle.chain.comparison_vector.values)
        prefix.append(
            {
                "sequence_index": sequence_index,
                "work_vector_id": bundle.chain.work_vector.work_vector_id,
                "comparison_vector_id": (
                    bundle.chain.comparison_vector.comparison_vector_id
                ),
                "subject_id": bundle.chain.work_vector.subject_id,
                "route_kind": bundle.chain.work_vector.route_kind.value,
                "cumulative_axis_values": [
                    {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
                ],
            }
        )
    final_totals = [
        {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
    ]
    profiles = registry_v9.freeze_construction_accounting_registry_v9()
    payload = {
        "schema": "acfqp.standard_2048_adaptive_accounted_campaign.v36",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "adaptive_accounting_preregistration": preregistration.to_document(),
        "v35_adaptive_expression_campaign_id": V35_CAMPAIGN_ID,
        "v35_adaptive_expression_verification_id": V35_VERIFICATION_ID,
        "v35_native_replay_campaign_id": replayed_v35[
            "adaptive_expression_campaign_id"
        ],
        "counter_registry_id": profiles["counter_registry"][
            "counter_registry_id"
        ],
        "stage_profile_id": profiles["stage_profile"]["stage_profile_id"],
        "comparison_profile_id": profiles["comparison_profile"][
            "comparison_profile_id"
        ],
        "actual_projection_profile_id": profiles[
            "actual_projection_profile"
        ]["actual_projection_profile_id"],
        "model_stage_bundles": [
            _bundle_summary(bundle, output_root=output_root)
            for bundle in (
                failure_bundle,
                acquisition_bundle,
                proposal_bundle,
                proof_bundle,
                overlay_bundle,
            )
        ],
        "matched_no_prior_control_bundle": _bundle_summary(
            control_bundle, output_root=output_root
        ),
        "episode_rows": episode_rows,
        "process_supervision_bundle": _bundle_summary(
            process_bundle, output_root=output_root
        ),
        "campaign_aggregation_bundle": _bundle_summary(
            campaign_bundle, output_root=output_root
        ),
        "operational_work_vector_count": len(operational_bundles),
        "evaluation_work_vector_count": len(evaluation_bundles),
        "vector_prefix_totals": prefix,
        "final_operational_comparison_totals": final_totals,
        "logical_occurrence_count": len(episode_documents),
        "complete_decision_count": replayed_v35["decision_count"],
        "model_certificate_count": replayed_v35["model_certificate_count"],
        "certificate_failure_count": replayed_v35[
            "certificate_failure_count"
        ],
        "operational_target_probability_label_query_count": replayed_v35[
            "ground_distinction_query_count"
        ],
        "evaluation_no_prior_probability_label_count": replayed_v35[
            "first_frontier_no_prior_label_count"
        ],
        "adaptive_label_fraction_of_no_prior": replayed_v35[
            "adaptive_label_fraction_of_no_prior"
        ],
        "cold_evaluation_checkpoint_count": replayed_v35[
            "cold_evaluation_checkpoint_count"
        ],
        "all_checkpoint_root_values_and_actions_exactly_equal": replayed_v35[
            "all_checkpoint_root_values_and_actions_exactly_equal"
        ],
        "all_required_counter_leaves_have_explicit_native_records": True,
        "all_nine_shared_resource_paths_have_measurement_receipts": True,
        "evaluation_replay_excluded_from_operational_comparison": True,
        "summary_to_counter_translation_used": False,
        "every_worker_process_executes_exactly_one_occurrence": True,
        "sample_tax_reduced_on_registered_first_failure_label_axis": True,
        "formal_counter_completeness_candidate": True,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "adaptive_accounted_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveAccountedCampaignV36:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    output_root: Path

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.canonical_bytes) is not bytes
            or not isinstance(self.output_root, Path)
        ):
            _fail("adaptive-accounted campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("adaptive-accounted campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_accounted_campaign_id"
        }
        if (
            document.get("adaptive_accounted_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload)
            != self.campaign_id
        ):
            _fail("adaptive-accounted campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive-accounted campaign is not an object")
        return document


def run_standard_2048_adaptive_accounted_campaign_v36(
    *,
    v35_campaign_bytes: bytes,
    v35_verification_bytes: bytes,
    output_root: Path,
) -> Standard2048AdaptiveAccountedCampaignV36:
    v35_campaign, _ = _verify_v35_inputs(
        v35_campaign_bytes, v35_verification_bytes
    )
    document = _materialize_campaign(
        v35_campaign=v35_campaign, output_root=output_root
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["adaptive_accounted_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen adaptive-accounted campaign changed")
    return Standard2048AdaptiveAccountedCampaignV36(
        _ISSUER,
        raw,
        document["adaptive_accounted_campaign_id"],
        output_root,
    )


def verify_standard_2048_adaptive_accounted_campaign_v36(
    value: Standard2048AdaptiveAccountedCampaignV36,
) -> Standard2048AdaptiveAccountedCampaignV36:
    if type(value) is not Standard2048AdaptiveAccountedCampaignV36:
        _fail("adaptive-accounted campaign rejects foreign values")
    value.__post_init__()
    document = value.to_document()
    if (
        document["all_required_counter_leaves_have_explicit_native_records"]
        is not True
        or document[
            "all_nine_shared_resource_paths_have_measurement_receipts"
        ]
        is not True
        or document["evaluation_replay_excluded_from_operational_comparison"]
        is not True
        or document["summary_to_counter_translation_used"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _fail("adaptive-accounted result or claim locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048AdaptiveAccountedCampaignV36Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048AdaptiveAccountedCampaignV36",
    "run_standard_2048_adaptive_accounted_campaign_v36",
    "verify_standard_2048_adaptive_accounted_campaign_v36",
)
