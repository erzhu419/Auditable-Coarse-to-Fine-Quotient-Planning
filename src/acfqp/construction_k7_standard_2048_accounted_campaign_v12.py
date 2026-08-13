"""Run the preregistered fresh-board standard-2048 campaign with V8 accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
import multiprocessing
from pathlib import Path
import resource
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum, RouteKindEnum, SHARED_AXES
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import construction_k7_standard_2048_accounted_artifacts_v12 as artifacts
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre
from acfqp import construction_k7_standard_2048_instrumented_runtime_v12 as runtime
from acfqp import (
    construction_k7_standard_2048_long_episode_independent_verifier_v11 as replay,
)
from acfqp.domains.standard_2048 import Swipe2048Status, state_from_board_v1
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = pre.PROFILE_KEY
DOMAINS = pre.FUTURE_DOMAINS
PREDECESSOR_VERIFICATION_ID = (
    "d5e212e675bd2a2ed37d506ee871a1d6a65de5c8de3dd4c080086fffc7e59736"
)


class ConstructionK7Standard2048AccountedCampaignV12Error(RuntimeError):
    """A worker, route window, lane split, vector, or campaign join changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AccountedCampaignV12Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AccountedCampaignV12Error(
            f"{label} is not one exact content ID"
        ) from error


def _document_id(
    document: Mapping[str, Any], *, id_key: str, domain: str, label: str
) -> str:
    if type(document) is not dict or id_key not in document:
        _fail(f"{label} document changed")
    identity = _cid(document[id_key], label)
    payload = {key: value for key, value in document.items() if key != id_key}
    if content_id(domain, payload) != identity:
        _fail(f"{label} content identity changed")
    return identity


def _add(values: dict[str, int], path: str, value: int = 1) -> None:
    if path not in values or type(value) is not int or value < 0:
        _fail("campaign counter increment changed")
    values[path] += value


def _predecessor_verification_document() -> dict[str, Any]:
    verification = replay.Standard2048LongEpisodeIndependentVerificationV11(
        replay.EXPECTED_CAMPAIGN_ID
    )
    if verification.verification_id != PREDECESSOR_VERIFICATION_ID:
        _fail("V169 predecessor verification identity changed")
    payload = {
        "schema": "acfqp.standard_2048_predecessor_verification_binding.v12",
        "schema_version": SCHEMA_VERSION,
        "v169_independent_verification": verification.to_document(),
        "v169_campaign_canonical_byte_count": replay.EXPECTED_CANONICAL_BYTE_COUNT,
        "v169_campaign_canonical_sha256": replay.EXPECTED_CANONICAL_SHA256,
        "producer_and_independent_replay_byte_count_identical": True,
        "producer_and_independent_replay_sha256_identical": True,
        "independent_replay_completed_before_v12_execution": True,
        "predecessor_is_evidence_only": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "accounted_verification_id": content_id(DOMAINS["verification"], payload),
    }


def _task_document(episode_index: int, decision_limit: int) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_accounted_episode_task.v12",
        "schema_version": SCHEMA_VERSION,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode_index,
        "initial_board_ranks": list(pre.PREREGISTERED_INITIAL_BOARDS[episode_index]),
        "execution_seed": pre.PREREGISTERED_EPISODE_SEEDS[episode_index],
        "decision_limit": decision_limit,
        "planning_horizon": pre.PLANNING_HORIZON,
        "operator_binding_expected": (
            "d20ecf7186d8b37337e6c36212ac0aa7c9ee7f2b7e07f885d0c7e1cead330535"
        ),
        "evaluation_lane_separate_from_operational_route": True,
    }
    return {
        **payload,
        "accounted_measurement_id": content_id(DOMAINS["measurement"], payload),
    }


def _worker_episode(raw_task: bytes) -> tuple[bytes, tuple[bytes, ...], int]:
    task = loads_canonical_json(raw_task)
    if type(task) is not dict:
        _fail("worker task is not canonical")
    _document_id(
        task,
        id_key="accounted_measurement_id",
        domain=DOMAINS["measurement"],
        label="episode task",
    )
    episode_index = task["episode_index"]
    decision_limit = task["decision_limit"]
    if (
        type(episode_index) is not int
        or episode_index < 0
        or episode_index >= len(pre.PREREGISTERED_INITIAL_BOARDS)
        or type(decision_limit) is not int
        or decision_limit <= 0
        or decision_limit > pre.MAXIMUM_DECISIONS_PER_EPISODE
        or task["accounted_preregistration_id"] != pre.PREREGISTRATION_ID
        or task["initial_board_ranks"]
        != list(pre.PREREGISTERED_INITIAL_BOARDS[episode_index])
        or task["execution_seed"] != pre.PREREGISTERED_EPISODE_SEEDS[episode_index]
    ):
        _fail("worker task identity changed")
    binding, bounds, lower, upper = replay._operator_binding()  # noqa: SLF001
    if binding["long_operator_binding_id"] != task["operator_binding_expected"]:
        _fail("worker operator binding changed")
    state = state_from_board_v1(tuple(task["initial_board_ranks"]))
    initial_state = runtime._state_document(state)  # noqa: SLF001
    seed = task["execution_seed"]
    initial_counters = runtime.NativeCounterSetV12()
    rows = runtime.InstrumentedLazyRowsV12(
        bounds, binding["long_operator_binding_id"], initial_counters
    )
    bellman = runtime.InstrumentedPersistentBellmanV12(
        lower, upper, initial_counters
    )
    decisions: list[dict[str, Any]] = []
    evaluations: list[bytes] = []
    for decision_index in range(decision_limit):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        common = runtime.NativeCounterSetV12()
        draft = runtime.execute_instrumented_decision_v12(
            state=state,
            decision_index=decision_index,
            seed=seed,
            operator_id=binding["long_operator_binding_id"],
            rows=rows,
            bellman=bellman,
            common_counters=common,
        )
        draft_document = draft.to_document()
        evaluation_id = None
        if draft.route == "ABSTRACT_CERTIFIED":
            evaluation_values = dict(draft_document["evaluation_counter_values"])
            _add(evaluation_values, "evaluation.hash_invocations")
            evaluation_payload = {
                "schema": "acfqp.standard_2048_accounted_evaluation_transport.v12",
                "schema_version": SCHEMA_VERSION,
                "accounted_preregistration_id": pre.PREREGISTRATION_ID,
                "episode_index": episode_index,
                "decision_index": decision_index,
                "state_before_decision": draft_document["state_before_decision"],
                "selected_action": draft_document["selected_action"],
                "exact_plan": draft_document["exact_plan"],
                "forced_selected_action_exact_evaluation": draft_document[
                    "forced_exact_plan"
                ],
                "selected_action_exact_value_and_loss_equivalent": draft_document[
                    "selected_action_exact_value_and_loss_equivalent"
                ],
                "selected_action_label_identical": draft_document[
                    "selected_action_label_identical"
                ],
                "evaluation_counter_values": evaluation_values,
                "operational_route_work_present": False,
            }
            evaluation_document = {
                **evaluation_payload,
                "accounted_counter_bundle_id": content_id(
                    DOMAINS["counter_bundle"], evaluation_payload
                ),
            }
            evaluation_id = evaluation_document["accounted_counter_bundle_id"]
            evaluations.append(canonical_json_bytes(evaluation_document))
            draft_document["exact_plan"] = None
            draft_document["forced_exact_plan"] = None
            draft_document["evaluation_counter_values"] = None
        selected_values_key = (
            "common_counter_values"
            if draft.route == "ABSTRACT_CERTIFIED"
            else "fallback_counter_values"
        )
        selected_values = dict(draft_document[selected_values_key])
        _add(selected_values, "common.hash_invocations")
        draft_document[selected_values_key] = selected_values
        decision_payload = {
            "schema": "acfqp.standard_2048_accounted_business_decision.v12",
            "schema_version": SCHEMA_VERSION,
            "accounted_preregistration_id": pre.PREREGISTRATION_ID,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "operational_draft": draft_document,
            "matched_evaluation_transport_id": evaluation_id,
            "evaluation_not_used_for_route_selection": True,
        }
        decisions.append(
            {
                **decision_payload,
                "accounted_decision_id": content_id(
                    DOMAINS["decision"], decision_payload
                ),
            }
        )
        state = draft.state_after
    payload = {
        "schema": "acfqp.standard_2048_accounted_business_episode.v12",
        "schema_version": SCHEMA_VERSION,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial_state,
        "operator_binding_id": binding["long_operator_binding_id"],
        "decisions": decisions,
        "evaluation_transport_ids": [
            loads_canonical_json(raw)["accounted_counter_bundle_id"]
            for raw in evaluations
        ],
        "decision_count": len(decisions),
        "abstract_route_count": sum(
            row["operational_draft"]["route"] == "ABSTRACT_CERTIFIED"
            for row in decisions
        ),
        "fallback_route_count": sum(
            row["operational_draft"]["route"]
            == "COLD_EXACT_DIRECT_GROUND_FALLBACK"
            for row in decisions
        ),
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "final_state": runtime._state_document(state),  # noqa: SLF001
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= 11,
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["operational_draft"][
                "selected_action_exact_value_and_loss_equivalent"
            ]
            for row in decisions
        ),
    }
    episode = {
        **payload,
        "accounted_episode_id": content_id(DOMAINS["episode"], payload),
    }
    observed_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if observed_peak > pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER:
        _fail("episode worker exceeded its preregistered working-byte upper")
    return canonical_json_bytes(episode), tuple(evaluations), observed_peak


def _process_entry(raw_task: bytes, sender: Any) -> None:
    try:
        episode, evaluations, peak = _worker_episode(raw_task)
        sender.send_bytes(episode)
        sender.send((len(evaluations), peak))
        for raw in evaluations:
            sender.send_bytes(raw)
    finally:
        sender.close()


@dataclass(frozen=True, slots=True)
class _WorkerReply:
    task_bytes: bytes = field(repr=False)
    episode_bytes: bytes = field(repr=False)
    episode: Mapping[str, Any]
    evaluation_bytes: tuple[bytes, ...] = field(repr=False)
    evaluations: tuple[Mapping[str, Any], ...]
    observed_working_peak: int


def _run_workers(decision_limit: int, episode_count: int) -> tuple[_WorkerReply, ...]:
    if (
        type(decision_limit) is not int
        or decision_limit <= 0
        or decision_limit > pre.MAXIMUM_DECISIONS_PER_EPISODE
        or type(episode_count) is not int
        or episode_count <= 0
        or episode_count > pre.EPISODE_WORKER_COUNT
    ):
        _fail("worker campaign bounds changed")
    context = multiprocessing.get_context("fork")
    processes = []
    receivers = []
    task_rows = []
    for episode_index in range(episode_count):
        task_bytes = canonical_json_bytes(_task_document(episode_index, decision_limit))
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_process_entry, args=(task_bytes, sender))
        process.start()
        sender.close()
        processes.append(process)
        receivers.append(receiver)
        task_rows.append(task_bytes)
    replies = []
    try:
        for task_bytes, receiver in zip(task_rows, receivers, strict=True):
            episode_bytes = receiver.recv_bytes()
            evaluation_count, peak = receiver.recv()
            evaluation_bytes = tuple(
                receiver.recv_bytes() for _ in range(evaluation_count)
            )
            episode = loads_canonical_json(episode_bytes)
            evaluations = tuple(loads_canonical_json(raw) for raw in evaluation_bytes)
            if type(episode) is not dict or any(
                type(row) is not dict for row in evaluations
            ):
                _fail("worker reply is not canonical object evidence")
            replies.append(
                _WorkerReply(
                    task_bytes,
                    episode_bytes,
                    MappingProxyType(episode),
                    evaluation_bytes,
                    tuple(MappingProxyType(row) for row in evaluations),
                    peak,
                )
            )
    finally:
        for receiver in receivers:
            receiver.close()
        for process in processes:
            process.join()
    if any(process.exitcode != 0 for process in processes):
        _fail("an accounted episode worker did not exit successfully")
    return tuple(replies)


def _worker_chain(reply: _WorkerReply) -> tuple[
    artifacts.Standard2048AccountingMeasurementV12,
    runtime.OperationalAccountingChainV12,
]:
    episode_id = _document_id(
        dict(reply.episode),
        id_key="accounted_episode_id",
        domain=DOMAINS["episode"],
        label="business episode",
    )
    values = dict(runtime.NativeCounterSetV12().freeze())
    values["common.hash_invocations"] = 2
    values["common.integrity_checks"] = 2
    values["common.protocol_checks"] = 1
    values["io.read_bytes"] = len(reply.task_bytes)
    values["io.output_bytes"] = len(reply.episode_bytes)
    values["memory.working_bytes_peak"] = (
        pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER
    )
    values["process.launches"] = 1
    values["process.exit_successes"] = 1
    if reply.observed_working_peak > values["memory.working_bytes_peak"]:
        _fail("worker peak escaped the preregistered cap")
    measurement = artifacts.Standard2048AccountingMeasurementV12(
        episode_id,
        "EPISODE_WORKER_PROCESS_AND_OPERATIONAL_PIPE",
        tuple((path, values[path]) for path in artifacts.SHARED_PATHS),
        "ONE_FORKED_WORKER_TASK_AND_OPERATIONAL_REPLY",
    )
    chain = runtime.build_operational_accounting_chain_v12(
        subject_id=episode_id,
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        values=values,
        recorder_id=episode_id,
        recorder_ids_by_path={
            path: measurement.measurement_id for path in artifacts.SHARED_PATHS
        },
    )
    return measurement, chain


def _bundle_summary(
    bundle: artifacts.MaterializedOperationalSegmentV12,
) -> dict[str, Any]:
    full = bundle.to_document()
    return {
        "accounted_counter_bundle_id": full["accounted_counter_bundle_id"],
        "segment_role": bundle.segment_role,
        "accounting_measurement_id": bundle.measurement.measurement_id,
        "work_vector_id": bundle.accounting_chain.work_vector.work_vector_id,
        "comparison_vector_id": (
            bundle.accounting_chain.comparison_vector.comparison_vector_id
        ),
        "actual_projection_proof_id": (
            bundle.accounting_chain.projection_proof.actual_projection_proof_id
        ),
        "output_bytes_fixed_point_result_id": bundle.fixed_point.result_id,
        "output_commit_id": bundle.output_commit.output_commit_id,
        "output_key": bundle.output_commit.output_key,
        "io.output_bytes": bundle.fixed_point.output_bytes,
    }


def _evaluation_summary(
    bundle: artifacts.MaterializedEvaluationV12,
) -> dict[str, Any]:
    full = bundle.to_document()
    return {
        "accounted_counter_bundle_id": full["accounted_counter_bundle_id"],
        "work_vector_id": bundle.work_vector.work_vector_id,
        "accounting_measurement_id": bundle.measurement["accounting_measurement_id"],
        "output_commit_id": bundle.output_commit.output_commit_id,
        "output_key": bundle.output_commit.output_key,
        "evaluation.io.output_bytes": bundle.work_vector.value(
            "evaluation.io_output_bytes"
        ),
        "comparison_vector_issued": False,
    }


def _accumulate_comparison(
    current: dict[str, int], values: tuple[tuple[str, int], ...]
) -> dict[str, int]:
    profile = registry_v8.official_comparison_profile_v8()
    reducers = {row.name: row.reducer for row in profile.axes}
    result = dict(current)
    for axis, value in values:
        if reducers[axis] is ReducerEnum.SUM:
            result[axis] += value
        else:
            result[axis] = max(result[axis], value)
    return result


def _tree_file_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _materialize_campaign(
    *, output_root: Path, decision_limit: int, episode_count: int
) -> tuple[dict[str, Any], tuple[runtime.OperationalAccountingChainV12, ...]]:
    preregistration = pre.verify_standard_2048_accounted_preregistration_v12(
        pre.freeze_standard_2048_accounted_preregistration_v12()
    )
    predecessor = _predecessor_verification_document()
    replies = _run_workers(decision_limit, episode_count)
    if output_root.exists():
        _fail("accounted campaign output root must be absent")
    output_root.mkdir(mode=0o700, parents=False)
    operational_chains: list[runtime.OperationalAccountingChainV12] = []
    evaluation_vectors = []
    episode_summaries = []
    total_operational_pipe_read = 0
    for episode_ordinal, reply in enumerate(replies):
        episode = dict(reply.episode)
        episode_id = _document_id(
            episode,
            id_key="accounted_episode_id",
            domain=DOMAINS["episode"],
            label="episode reply",
        )
        if episode["episode_index"] != episode_ordinal:
            _fail("episode result order changed")
        worker_measurement, worker_chain = _worker_chain(reply)
        operational_chains.append(worker_chain)
        total_operational_pipe_read += len(reply.episode_bytes)
        evaluations_by_id = {}
        evaluation_raw_by_id = {}
        for raw, evaluation in zip(
            reply.evaluation_bytes, reply.evaluations, strict=True
        ):
            row = dict(evaluation)
            identity = _document_id(
                row,
                id_key="accounted_counter_bundle_id",
                domain=DOMAINS["counter_bundle"],
                label="evaluation transport",
            )
            evaluations_by_id[identity] = row
            evaluation_raw_by_id[identity] = raw
        episode_dir = output_root / f"episode-{episode_ordinal:04d}"
        episode_dir.mkdir(mode=0o700)
        decision_summaries = []
        for decision in episode["decisions"]:
            decision_id = _document_id(
                decision,
                id_key="accounted_decision_id",
                domain=DOMAINS["decision"],
                label="business decision",
            )
            draft = decision["operational_draft"]
            decision_index = decision["decision_index"]
            decision_dir = episode_dir / f"decision-{decision_index:04d}"
            decision_dir.mkdir(mode=0o700)
            bundle_rows = []
            evaluation_summary = None
            if draft["route"] == "ABSTRACT_CERTIFIED":
                values = dict(draft["common_counter_values"])
                _add(values, "common.hash_invocations")
                _add(values, "common.integrity_checks")
                _add(values, "common.protocol_checks")
                bundle = artifacts.materialize_operational_segment_v12(
                    subject_id=decision_id,
                    segment_role="ABSTRACT_CERTIFIED_SELECTED_ROUTE",
                    route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
                    work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
                    base_values=values,
                    business_document=decision,
                    trace_document=draft,
                    terminal_document={
                        "terminal_scope": "LOGICAL_DECISION",
                        "terminal_class": "PLAN_CERTIFICATE",
                        "terminal_code": "ABSTRACT_CERTIFIED",
                    },
                    output_directory=decision_dir / "abstract",
                    output_key=(
                        f"episode-{episode_ordinal:04d}/"
                        f"decision-{decision_index:04d}/abstract"
                    ),
                    allocation_profile=(
                        "PER_DECISION_OUTPUT_ONLY_GLOBAL_PEAKS_ELSEWHERE"
                    ),
                )
                operational_chains.append(bundle.accounting_chain)
                bundle_rows.append(_bundle_summary(bundle))
                evaluation_id = decision["matched_evaluation_transport_id"]
                evaluation = evaluations_by_id.pop(evaluation_id)
                evaluation_raw = evaluation_raw_by_id.pop(evaluation_id)
                evaluation_values = dict(evaluation["evaluation_counter_values"])
                _add(evaluation_values, "evaluation.hash_invocations")
                _add(evaluation_values, "evaluation.semantic_integrity_checks")
                _add(evaluation_values, "evaluation.semantic_protocol_checks")
                evaluation_values["evaluation.io_read_bytes"] = len(evaluation_raw)
                evaluation_bundle = artifacts.materialize_evaluation_v12(
                    subject_id=decision_id,
                    transport_document=evaluation,
                    exact_document=evaluation["exact_plan"],
                    forced_document=evaluation[
                        "forced_selected_action_exact_evaluation"
                    ],
                    base_values=evaluation_values,
                    transport_output_bytes=len(evaluation_raw),
                    working_bytes_peak=(
                        pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER
                    ),
                    output_directory=decision_dir / "evaluation",
                    output_key=(
                        f"episode-{episode_ordinal:04d}/"
                        f"decision-{decision_index:04d}/evaluation"
                    ),
                )
                evaluation_vectors.append(evaluation_bundle.work_vector)
                evaluation_summary = _evaluation_summary(evaluation_bundle)
            elif draft["route"] == "COLD_EXACT_DIRECT_GROUND_FALLBACK":
                common_bundle = artifacts.materialize_operational_segment_v12(
                    subject_id=decision_id,
                    segment_role="FAILED_ABSTRACT_CERTIFICATE_COMMON_PREFIX",
                    route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
                    work_scope=ActualWorkScope.COMMON_PREFIX,
                    base_values=draft["common_counter_values"],
                    business_document={
                        "certificate": draft["certificate"],
                        "route": draft["route"],
                    },
                    trace_document=draft,
                    terminal_document={
                        "terminal_scope": "NONTERMINAL_ROUTE_SEGMENT",
                        "terminal_class": "SEGMENT_CLOSURE_NONTERMINAL",
                        "terminal_code": (
                            "ABSTRACT_CERTIFICATE_FAILED_FALLBACK_PENDING"
                        ),
                    },
                    output_directory=decision_dir / "common",
                    output_key=(
                        f"episode-{episode_ordinal:04d}/"
                        f"decision-{decision_index:04d}/common"
                    ),
                    allocation_profile=(
                        "PER_DECISION_OUTPUT_ONLY_GLOBAL_PEAKS_ELSEWHERE"
                    ),
                )
                operational_chains.append(common_bundle.accounting_chain)
                bundle_rows.append(_bundle_summary(common_bundle))
                fallback_values = dict(draft["fallback_counter_values"])
                _add(fallback_values, "common.hash_invocations")
                _add(fallback_values, "common.integrity_checks")
                _add(fallback_values, "common.protocol_checks")
                fallback_bundle = artifacts.materialize_operational_segment_v12(
                    subject_id=decision_id,
                    segment_role="DIRECT_GROUND_FALLBACK_SELECTED_ROUTE",
                    route_kind=RouteKindEnum.DIRECT_FALLBACK,
                    work_scope=ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
                    base_values=fallback_values,
                    business_document=decision,
                    trace_document=draft,
                    terminal_document={
                        "terminal_scope": "LOGICAL_DECISION",
                        "terminal_class": "PLAN_CERTIFICATE",
                        "terminal_code": "FULL_GROUND_FALLBACK",
                    },
                    output_directory=decision_dir / "fallback",
                    output_key=(
                        f"episode-{episode_ordinal:04d}/"
                        f"decision-{decision_index:04d}/fallback"
                    ),
                    allocation_profile=(
                        "PER_DECISION_OUTPUT_ONLY_GLOBAL_PEAKS_ELSEWHERE"
                    ),
                )
                operational_chains.append(fallback_bundle.accounting_chain)
                bundle_rows.append(_bundle_summary(fallback_bundle))
            else:
                _fail("business decision used an unknown route")
            decision_payload = {
                "schema": "acfqp.standard_2048_accounted_decision.v12",
                "schema_version": SCHEMA_VERSION,
                "business_decision_id": decision_id,
                "episode_index": episode_ordinal,
                "decision_index": decision_index,
                "route": draft["route"],
                "selected_action": draft["selected_action"],
                "operational_counter_bundles": bundle_rows,
                "evaluation_counter_bundle": evaluation_summary,
                "selected_action_exact_value_and_loss_equivalent": draft[
                    "selected_action_exact_value_and_loss_equivalent"
                ],
                "evaluation_excluded_from_operational_comparison": True,
                "official_execution_allowed": False,
            }
            decision_summaries.append(
                {
                    **decision_payload,
                    "accounted_decision_id": content_id(
                        DOMAINS["decision"], decision_payload
                    ),
                }
            )
        if evaluations_by_id:
            _fail("an evaluation transport was not joined to its decision")
        episode_payload = {
            "schema": "acfqp.standard_2048_accounted_episode.v12",
            "schema_version": SCHEMA_VERSION,
            "business_episode_id": episode_id,
            "business_episode": episode,
            "worker_task": loads_canonical_json(reply.task_bytes),
            "episode_index": episode_ordinal,
            "worker_accounting_measurement": worker_measurement.to_document(),
            "worker_work_vector": worker_chain.work_vector.to_dict(),
            "worker_comparison_vector": worker_chain.comparison_vector.to_dict(),
            "worker_actual_projection_proof": (
                worker_chain.projection_proof.to_dict()
            ),
            "decisions": decision_summaries,
            "decision_count": len(decision_summaries),
            "abstract_route_count": episode["abstract_route_count"],
            "fallback_route_count": episode["fallback_route_count"],
            "closure_reason": episode["closure_reason"],
            "final_state": episode["final_state"],
            "maximum_final_board_tile_rank": episode[
                "maximum_final_board_tile_rank"
            ],
            "tile_2048_reached": episode["tile_2048_reached"],
            "all_selected_actions_exact_value_and_loss_equivalent": episode[
                "all_selected_actions_exact_value_and_loss_equivalent"
            ],
        }
        episode_summaries.append(
            {
                **episode_payload,
                "accounted_episode_id": content_id(
                    DOMAINS["episode"], episode_payload
                ),
            }
        )
    decision_rows = [
        decision
        for episode in episode_summaries
        for decision in episode["decisions"]
    ]
    business_payload = {
        "schema": "acfqp.standard_2048_accounted_business_campaign.v12",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "predecessor_verification_id": predecessor["accounted_verification_id"],
        "business_episode_ids": [
            episode["business_episode_id"] for episode in episode_summaries
        ],
        "decision_count": len(decision_rows),
        "abstract_route_count": sum(
            row["route"] == "ABSTRACT_CERTIFIED" for row in decision_rows
        ),
        "fallback_route_count": sum(
            row["route"] == "COLD_EXACT_DIRECT_GROUND_FALLBACK"
            for row in decision_rows
        ),
        "offline_transition_observation_count": pre.OFFLINE_OBSERVATION_COUNT,
        "additional_model_acquisition_observation_count": 0,
        "online_target_transition_observation_count": len(decision_rows),
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"]
            for row in decision_rows
        ),
    }
    business_campaign = {
        **business_payload,
        "accounted_campaign_id": content_id(DOMAINS["campaign"], business_payload),
    }
    _document_id(
        business_campaign,
        id_key="accounted_campaign_id",
        domain=DOMAINS["campaign"],
        label="business campaign",
    )
    global_mounted_before = _tree_file_bytes(output_root)
    campaign_values = dict(runtime.NativeCounterSetV12().freeze())
    campaign_values["common.hash_invocations"] = 2
    campaign_values["common.integrity_checks"] = 4
    campaign_values["common.protocol_checks"] = 3
    campaign_values["io.read_bytes"] = total_operational_pipe_read
    campaign_values["io.mounted_bytes_peak"] = global_mounted_before
    campaign_values["memory.working_bytes_peak"] = (
        pre.CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER
    )
    parent_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if parent_peak > pre.CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER:
        _fail("campaign parent exceeded its preregistered working-byte upper")
    campaign_bundle = artifacts.materialize_operational_segment_v12(
        subject_id=business_campaign["accounted_campaign_id"],
        segment_role="CAMPAIGN_BUILD_AND_ACCOUNTING_COMMON",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=campaign_values,
        business_document=business_campaign,
        trace_document={
            "preregistration": preregistration.to_document(),
            "predecessor_verification": predecessor,
            "episodes": episode_summaries,
        },
        terminal_document={
            "terminal_scope": "REGISTERED_CAMPAIGN_EVIDENCE",
            "terminal_class": "CAMPAIGN_EVIDENCE_CLOSURE",
            "terminal_code": "REGISTERED_DECISION_LIMIT_EVIDENCE_COMPLETE",
        },
        output_directory=output_root / "campaign",
        output_key="campaign",
        allocation_profile="CAMPAIGN_GLOBAL_MOUNT_PEAK_PLUS_OWN_OUTPUT",
    )
    operational_chains.append(campaign_bundle.accounting_chain)
    if _tree_file_bytes(output_root) != (
        global_mounted_before + campaign_bundle.fixed_point.output_bytes
    ):
        _fail("global mounted output byte closure changed")
    totals = {axis: 0 for axis in SHARED_AXES}
    prefix = []
    for sequence_index, chain in enumerate(operational_chains):
        totals = _accumulate_comparison(
            totals, chain.comparison_vector.values
        )
        prefix.append(
            {
                "sequence_index": sequence_index,
                "work_vector_id": chain.work_vector.work_vector_id,
                "comparison_vector_id": chain.comparison_vector.comparison_vector_id,
                "subject_id": chain.work_vector.subject_id,
                "route_kind": chain.work_vector.route_kind.value,
                "cumulative_axis_values": [
                    {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
                ],
            }
        )
    evaluation_totals = {
        path: sum(vector.value(path) for vector in evaluation_vectors)
        for path in registry_v8.official_counter_registry_v8().by_path
        if path.startswith("evaluation.")
    }
    payload = {
        "schema": "acfqp.standard_2048_accounted_campaign.v12",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "predecessor_verification": predecessor,
        "business_campaign": business_campaign,
        "episodes": episode_summaries,
        "episode_count": len(episode_summaries),
        "decision_count": len(decision_rows),
        "abstract_route_count": business_campaign["abstract_route_count"],
        "fallback_route_count": business_campaign["fallback_route_count"],
        "offline_transition_observation_count": pre.OFFLINE_OBSERVATION_COUNT,
        "additional_model_acquisition_observation_count": 0,
        "online_target_transition_observation_count": len(decision_rows),
        "operational_work_vector_count": len(operational_chains),
        "evaluation_work_vector_count": len(evaluation_vectors),
        "campaign_counter_bundle": _bundle_summary(campaign_bundle),
        "vector_prefix_totals": prefix,
        "final_operational_comparison_totals": [
            {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
        ],
        "evaluation_lane_totals": evaluation_totals,
        "all_selected_actions_exact_value_and_loss_equivalent": business_campaign[
            "all_selected_actions_exact_value_and_loss_equivalent"
        ],
        "full_standard_2048_game_completed": all(
            episode["closure_reason"] == "TERMINAL_STATE"
            for episode in episode_summaries
        ),
        "tile_2048_reached": any(
            episode["tile_2048_reached"] for episode in episode_summaries
        ),
        "maximum_final_board_tile_rank": max(
            episode["maximum_final_board_tile_rank"]
            for episode in episode_summaries
        ),
        "counter_record_to_work_vector_to_comparison_vector_complete": True,
        "all_nine_shared_resource_paths_closed": True,
        "evaluation_excluded_from_operational_route_vectors": True,
        "independent_complete_bundle_verifier_present": False,
        "broad_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    document = {
        **payload,
        "accounted_campaign_id": content_id(DOMAINS["campaign"], payload),
    }
    return document, tuple(operational_chains)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AccountedCampaignV12:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    output_root: str = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("accounted campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("accounted campaign bytes changed")
        identity = _document_id(
            document,
            id_key="accounted_campaign_id",
            domain=DOMAINS["campaign"],
            label="accounted campaign",
        )
        if identity != self.campaign_id:
            _fail("accounted campaign object identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("accounted campaign is not an object")
        return document


def run_standard_2048_accounted_campaign_v12(
    *, output_root: str | Path
) -> Standard2048AccountedCampaignV12:
    root = Path(output_root)
    document, _ = _materialize_campaign(
        output_root=root,
        decision_limit=pre.MAXIMUM_DECISIONS_PER_EPISODE,
        episode_count=pre.EPISODE_WORKER_COUNT,
    )
    return Standard2048AccountedCampaignV12(
        _ISSUER,
        canonical_json_bytes(document),
        document["accounted_campaign_id"],
        str(root),
    )


__all__ = (
    "ConstructionK7Standard2048AccountedCampaignV12Error",
    "PREDECESSOR_VERIFICATION_ID",
    "Standard2048AccountedCampaignV12",
    "run_standard_2048_accounted_campaign_v12",
)
