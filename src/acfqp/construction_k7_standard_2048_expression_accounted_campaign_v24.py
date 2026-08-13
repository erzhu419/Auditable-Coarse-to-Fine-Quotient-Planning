"""Run synthesized 2048 model construction and reuse under V9 counters."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
import resource
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_blind_expression_campaign_v22 as synthesis
from acfqp import construction_k7_standard_2048_blind_expression_preregistration_v22 as synthesis_pre
from acfqp import construction_k7_standard_2048_commit_reveal_target_kernel_v22 as target
from acfqp import construction_k7_standard_2048_expression_accounted_artifacts_v24 as artifacts
from acfqp import construction_k7_standard_2048_expression_accounted_preregistration_v24 as pre
from acfqp import construction_k7_standard_2048_expression_accounted_runtime_v24 as runtime
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
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = pre.PROFILE_KEY
MAXIMUM_PROCESSES = 4
EXPECTED_CAMPAIGN_ID = "3eba16cb6db6d0797991acbde6103d423741668730313385e404949b5907ab72"
EXPECTED_CANONICAL_BYTE_COUNT = 443508
EXPECTED_CANONICAL_SHA256 = "e43c8fa9f5281b89525249a34c48a2f5351b0d46f9c946bfd3f7a187d45d91f2"
EXPECTED_STRUCTURAL_POOL_ID = "e842bbe08c29ecac07d3ca23f297a1e2ab139c919ffa3c388a8171fa905b240c"
EXPECTED_PROPOSAL_ID = "ce539f9d21f0aeffab81e2383686dc3bfb1c9fb80564b402f97eda4edc3ed560"
EXPECTED_PROOF_ID = "06f9585ee717daf391f51a0b36491f2735bc590bb8ed354c2578d86f89856b94"
EXPECTED_WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"


class ConstructionK7Standard2048ExpressionAccountedCampaignV24Error(RuntimeError):
    """A synthesis operation, worker route, counter bundle, or join changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionAccountedCampaignV24Error(message)


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _path(lane: str, suffix: str) -> str:
    if lane == "OPERATIONAL":
        return "model." + suffix
    if lane == "EVALUATION":
        return "evaluation." + suffix
    _fail("model synthesis lane changed")


def _audit_path(lane: str, family: str) -> str:
    if lane == "OPERATIONAL":
        return "common." + family
    if lane == "EVALUATION":
        return "evaluation." + (
            "semantic_integrity_checks"
            if family == "integrity_checks"
            else "semantic_protocol_checks"
            if family == "protocol_checks"
            else family
        )
    _fail("model synthesis lane changed")


def _context_pool_with_native_counters(
    counters: runtime.NativeCounterSetV24, *, lane: str
) -> dict[str, Any]:
    raw_rows = []
    constants = set()
    for ordinal, (board, action) in enumerate(synthesis_pre.RAW_CONTEXT_POOL):
        post, merge = synthesis._swipe(board, action)  # noqa: SLF001
        if post == board:
            _fail("registered structural context is an illegal no-op")
        raw_rows.append((ordinal, board, action, post, merge))
        constants.update(board)
        constants.update(post)
    definitions = synthesis._expression_definitions(  # noqa: SLF001
        tuple(sorted(constants))
    )
    rows = []
    for ordinal, board, action, post, merge in raw_rows:
        expressions = []
        for key, ast in definitions:
            value = planner.evaluate_structural_expression_v1(
                ast,
                pre_board=board,
                action=action,
                post_swipe_board=post,
                merge_score=merge,
            )
            counters.add(_path(lane, "structural_expression_value_evaluations"))
            expressions.append(
                {"expression_key": key, "expression_ast": ast, "value": value}
            )
        raw_payload = {
            "pool_ordinal": ordinal,
            "pre_state_board_ranks": list(board),
            "action": action,
            "post_swipe_board_ranks": list(post),
            "merge_score": merge,
            "expression_values": expressions,
        }
        rows.append(
            {
                **raw_payload,
                "structural_context_sha256": hashlib.sha256(
                    canonical_json_bytes(raw_payload)
                ).hexdigest(),
            }
        )
        counters.add(_path(lane, "structural_context_rows_frozen"))
        counters.add(_audit_path(lane, "hash_invocations"))
    payload = {
        "schema": "acfqp.standard_2048_blind_structural_pool.v22",
        "schema_version": synthesis.SCHEMA_VERSION,
        "blind_expression_preregistration_id": synthesis_pre.PREREGISTRATION_ID,
        "target_kernel_commitment_id": synthesis_pre.TARGET_KERNEL_COMMITMENT_ID,
        "swipe_world_model_id": synthesis.swipe_v14.FACTORED_WORLD_MODEL_ID,
        "observed_raw_rank_constants": list(sorted(constants)),
        "rows": rows,
        "context_count": len(rows),
        "expression_count_per_context": len(definitions),
        "all_structural_values_frozen_before_first_probability_query": True,
        "target_semantics_source_or_reveal_present": False,
        "named_target_specific_feature_present": False,
    }
    pool = {
        **payload,
        "blind_structural_pool_id": content_id(
            synthesis_pre.FUTURE_DOMAINS["context_pool"], payload
        ),
    }
    counters.add(_audit_path(lane, "hash_invocations"))
    if pool["blind_structural_pool_id"] != EXPECTED_STRUCTURAL_POOL_ID:
        _fail("instrumented structural pool identity changed")
    return pool


def _query_target_probability(
    post_swipe_board: tuple[int, ...],
    counters: runtime.NativeCounterSetV24,
    *,
    lane: str,
) -> Fraction:
    observed = target.query_rank_two_probability_v22(post_swipe_board)
    counters.add(_path(lane, "target_probability_labels_acquired"))
    return observed


def _query_record_from_observed(
    *,
    pool: dict[str, Any],
    pool_ordinal: int,
    query_ordinal: int,
    observed: Fraction,
    before: int | None,
    after: int,
    generated: bool,
    counters: runtime.NativeCounterSetV24,
    lane: str,
) -> dict[str, Any]:
    row = pool["rows"][pool_ordinal]
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_acquisition.v22",
        "schema_version": synthesis.SCHEMA_VERSION,
        "blind_expression_preregistration_id": synthesis_pre.PREREGISTRATION_ID,
        "blind_structural_pool_id": pool["blind_structural_pool_id"],
        "target_kernel_commitment_id": synthesis_pre.TARGET_KERNEL_COMMITMENT_ID,
        "query_ordinal": query_ordinal,
        "pool_ordinal": pool_ordinal,
        "structural_context_sha256": row["structural_context_sha256"],
        "observed_rank_two_probability": synthesis._fdoc(observed),  # noqa: SLF001
        "candidate_count_before": before,
        "candidate_count_after": after,
        "candidates_generated_after_this_query": generated,
        "context_and_all_expression_values_frozen_before_query": True,
        "query_interface_received_raw_post_swipe_board": True,
        "target_formula_used_by_acquisition_rule": False,
        "target_query_returns_scalar_label_only": True,
        "full_state_action_outcome_row_materialized": False,
    }
    result = {
        **payload,
        "blind_expression_acquisition_id": content_id(
            synthesis_pre.FUTURE_DOMAINS["acquisition"], payload
        ),
    }
    counters.add(_audit_path(lane, "hash_invocations"))
    return result


def _active_acquisition_with_native_counters(
    *,
    pool: dict[str, Any],
    candidates: tuple[Any, ...],
    first: Fraction,
    counters: runtime.NativeCounterSetV24,
    lane: str,
) -> tuple[list[dict[str, Any]], Any]:
    retained = []
    for candidate in candidates:
        counters.add(_path(lane, "candidate_label_consistency_checks"))
        if candidate[4][0] == first:
            retained.append(candidate)
    remaining = tuple(retained)
    queried = [0]
    rows = [
        _query_record_from_observed(
            pool=pool,
            pool_ordinal=0,
            query_ordinal=0,
            observed=first,
            before=None,
            after=len(remaining),
            generated=True,
            counters=counters,
            lane=lane,
        )
    ]
    while len(remaining) > 1:
        choices = []
        for pool_ordinal in range(len(pool["rows"])):
            if pool_ordinal in queried:
                continue
            buckets: dict[Fraction, int] = {}
            for candidate in remaining:
                counters.add(_path(lane, "active_query_partition_evaluations"))
                prediction = candidate[4][pool_ordinal]
                buckets[prediction] = buckets.get(prediction, 0) + 1
            if len(buckets) > 1:
                choices.append((max(buckets.values()), pool_ordinal))
        if not choices:
            _fail("registered active rule cannot separate model candidates")
        _, pool_ordinal = min(choices)
        queried.append(pool_ordinal)
        observed = _query_target_probability(
            tuple(pool["rows"][pool_ordinal]["post_swipe_board_ranks"]),
            counters,
            lane=lane,
        )
        before = remaining
        retained = []
        for candidate in before:
            counters.add(_path(lane, "candidate_label_consistency_checks"))
            if candidate[4][pool_ordinal] == observed:
                retained.append(candidate)
        remaining = tuple(retained)
        if not remaining or len(remaining) >= len(before):
            _fail("instrumented active query did not shrink version space")
        rows.append(
            _query_record_from_observed(
                pool=pool,
                pool_ordinal=pool_ordinal,
                query_ordinal=len(rows),
                observed=observed,
                before=len(before),
                after=len(remaining),
                generated=False,
                counters=counters,
                lane=lane,
            )
        )
        if len(rows) > synthesis_pre.MAXIMUM_TARGET_PROBABILITY_QUERIES:
            _fail("instrumented active query budget exhausted")
    return rows, remaining[0]


def _instrumented_model_synthesis(lane: str) -> tuple[
    dict[str, Any], Mapping[str, int], Mapping[str, int]
]:
    acquisition = runtime.NativeCounterSetV24()
    proof_counters = acquisition if lane == "EVALUATION" else runtime.NativeCounterSetV24()
    if target.verify_target_kernel_commitment_v22() != synthesis_pre.TARGET_KERNEL_COMMITMENT_ID:
        _fail("target commitment changed before instrumented synthesis")
    acquisition.add(_audit_path(lane, "protocol_checks"))
    pool = _context_pool_with_native_counters(acquisition, lane=lane)
    first = _query_target_probability(
        tuple(pool["rows"][0]["post_swipe_board_ranks"]),
        acquisition,
        lane=lane,
    )
    if first == synthesis.BASE_RATE:
        _fail("instrumented first query returned base probability")
    candidate_artifacts, candidates = synthesis._candidate_artifacts(  # noqa: SLF001
        pool, first
    )
    acquisition.add(
        _path(lane, "expression_candidates_materialized"),
        len(candidate_artifacts),
    )
    acquisition.add(_audit_path(lane, "hash_invocations"), len(candidate_artifacts))
    acquisitions, selected = _active_acquisition_with_native_counters(
        pool=pool,
        candidates=candidates,
        first=first,
        counters=acquisition,
        lane=lane,
    )
    proposal = synthesis._proposal(  # noqa: SLF001
        pool, candidate_artifacts, acquisitions, selected
    )
    acquisition.add(_audit_path(lane, "hash_invocations"))
    acquisition.add(_audit_path(lane, "integrity_checks"), len(acquisitions))
    proof = synthesis._proof(proposal)  # noqa: SLF001
    proof_counters.add(_audit_path(lane, "hash_invocations"))
    for row in proof["proof_rows"]:
        proof_counters.add(_path(lane, "exact_program_proof_rows_evaluated"))
        proof_counters.add(_audit_path(lane, "integrity_checks"))
        if row["exact_match"] is not True:
            _fail("instrumented exact program proof mismatch")
    world = synthesis._world_model(proposal, proof)  # noqa: SLF001
    proof_counters.add(_path(lane, "world_model_freezes"))
    proof_counters.add(_audit_path(lane, "hash_invocations"))
    proof_counters.add(_audit_path(lane, "protocol_checks"), 2)
    if (
        proposal["blind_expression_proposal_id"] != EXPECTED_PROPOSAL_ID
        or proof["blind_expression_proof_id"] != EXPECTED_PROOF_ID
        or world["blind_expression_world_model_id"] != EXPECTED_WORLD_MODEL_ID
    ):
        _fail("instrumented model synthesis identity changed")
    combined = acquisition.freeze()
    if lane == "EVALUATION":
        acquisition_values = combined
        proof_values = runtime.NativeCounterSetV24().freeze()
        total_values = dict(combined)
    else:
        acquisition_values = combined
        proof_values = proof_counters.freeze()
        total_values = {
            path: acquisition_values[path] + proof_values[path]
            for path in acquisition_values
        }
    expected = {
        _path(lane, "structural_context_rows_frozen"): 8,
        _path(lane, "structural_expression_value_evaluations"): 224,
        _path(lane, "expression_candidates_materialized"): 80,
        _path(lane, "candidate_label_consistency_checks"): 142,
        _path(lane, "active_query_partition_evaluations"): 399,
        _path(lane, "target_probability_labels_acquired"): 4,
        _path(lane, "exact_program_proof_rows_evaluated"): 17,
        _path(lane, "world_model_freezes"): 1,
    }
    if any(total_values[path] != value for path, value in expected.items()):
        _fail("instrumented model synthesis event totals changed")
    trace = {
        "lane": lane,
        "structural_pool": pool,
        "acquisitions": acquisitions,
        "proposal": proposal,
        "proof": proof,
        "world_model": world,
        "registered_event_totals": [
            {"path": path, "value": value} for path, value in expected.items()
        ],
        "unique_target_probability_labels": len(acquisitions),
        "actual_target_probability_query_invocations": total_values[
            _path(lane, "target_probability_labels_acquired")
        ],
        "duplicate_label_query_for_artifact_recording": False,
    }
    return trace, acquisition_values, proof_values


def _episode_task(episode_index: int, decision_limit: int) -> bytes:
    if (
        type(episode_index) is not int
        or not 0 <= episode_index < len(long_pre.INITIAL_BOARDS)
        or type(decision_limit) is not int
        or not 1 <= decision_limit <= long_pre.MAXIMUM_DECISIONS_PER_EPISODE
    ):
        _fail("episode task bounds changed")
    payload = {
        "schema": "acfqp.standard_2048_expression_accounted_episode_task.v24",
        "schema_version": SCHEMA_VERSION,
        "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode_index,
        "initial_board_ranks": list(long_pre.INITIAL_BOARDS[episode_index]),
        "execution_seed": long_pre.EPISODE_SEEDS[episode_index],
        "decision_limit": decision_limit,
        "planning_horizon": long_pre.PLANNING_HORIZON,
        "world_model_id": EXPECTED_WORLD_MODEL_ID,
        "expression_ast": {
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 1,
        },
        "threshold": 2,
        "base_probability": Fraction(1, 10),
        "override_probability": Fraction(3, 20),
    }
    document = {
        **payload,
        "expression_accounted_measurement_id": content_id(
            pre.FUTURE_DOMAINS["measurement"], payload
        ),
    }
    return canonical_json_bytes(document)


def _episode_worker(task_bytes: bytes) -> tuple[bytes, int]:
    task = loads_canonical_json(task_bytes)
    if type(task) is not dict:
        _fail("episode worker task is not canonical")
    task_payload = {
        key: value
        for key, value in task.items()
        if key != "expression_accounted_measurement_id"
    }
    if (
        content_id(pre.FUTURE_DOMAINS["measurement"], task_payload)
        != task.get("expression_accounted_measurement_id")
        or task.get("expression_accounted_preregistration_id")
        != pre.PREREGISTRATION_ID
        or task.get("world_model_id") != EXPECTED_WORLD_MODEL_ID
    ):
        _fail("episode worker task identity changed")
    episode_index = task["episode_index"]
    decision_limit = task["decision_limit"]
    state = state_from_board_v1(tuple(task["initial_board_ranks"]))
    initial_state = _state_document(state)
    session = planner.create_expression_planning_session_v1(
        expression_ast=task["expression_ast"],
        threshold=task["threshold"],
        base_probability=task["base_probability"],
        override_probability=task["override_probability"],
        horizon=task["planning_horizon"],
    )
    decisions = []
    for decision_index in range(decision_limit):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = session.plan_root(state)
        if model.get("target_transition_accessed") is not False:
            _fail("expression planner accessed target transition before certificate")
        certificate_payload = {
            "schema": "acfqp.standard_2048_expression_accounted_certificate.v24",
            "schema_version": SCHEMA_VERSION,
            "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
            "world_model_id": EXPECTED_WORLD_MODEL_ID,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": task["planning_horizon"],
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
            "operational_target_probability_query_count": 0,
            "operational_ground_state_action_row_count": 0,
            "certificate_frozen_before_target_access": True,
            "status": "CERTIFIED_PERSISTENT_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "expression_accounted_decision_id": content_id(
                pre.FUTURE_DOMAINS["decision"], certificate_payload
            ),
        }
        cold = None
        evaluation_values = None
        if decision_index in long_pre.COLD_EVALUATION_CHECKPOINTS:
            cold, evaluation_values = (
                runtime.evaluate_ground_root_with_native_counters_v24(
                    state,
                    outcome_provider=target.target_outcomes_v22,
                    horizon=task["planning_horizon"],
                )
            )
            if (
                cold["root_action_exact_values"]
                != model["root_action_exact_values"]
                or cold["selected_action"] != model["selected_action"]
            ):
                _fail("instrumented cold checkpoint differs from abstract model")
        selected = Swipe2048Action(model["selected_action"])
        outcomes = target.target_outcomes_v22(state, selected)
        operational_values = runtime.operational_decision_counter_values_v24(
            model=model,
            target_outcome_count=len(outcomes),
        )
        outcome, tape = select_seeded_outcome_v1(
            outcomes,
            seed=task["execution_seed"],
            decision_index=decision_index,
        )
        decision_payload = {
            "schema": "acfqp.standard_2048_expression_accounted_business_decision.v24",
            "schema_version": SCHEMA_VERSION,
            "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "predecision_state": _state_document(state),
            "certificate": certificate,
            "route": "PERSISTENT_EXPRESSION_WORLD_MODEL_CERTIFIED",
            "cold_evaluation": cold,
            "evaluation_counter_values": (
                None if evaluation_values is None else dict(evaluation_values)
            ),
            "operational_counter_values": dict(operational_values),
            "certificate_frozen_before_evaluation_and_target_transition": True,
            "executed_action": selected.value,
            "execution_tape_sha256": tape,
            "executed_next_state": _state_document(outcome.next_state),
            "online_target_transition_observation_count": 1,
            "execution_transition_used_to_modify_world_model": False,
        }
        decisions.append(
            {
                **decision_payload,
                "expression_accounted_decision_id": content_id(
                    pre.FUTURE_DOMAINS["decision"], decision_payload
                ),
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.standard_2048_expression_accounted_business_episode.v24",
        "schema_version": SCHEMA_VERSION,
        "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_task_id": task["expression_accounted_measurement_id"],
        "episode_index": episode_index,
        "execution_seed": task["execution_seed"],
        "initial_state": initial_state,
        "decisions": decisions,
        "decision_count": len(decisions),
        "maximum_registered_decision_count": decision_limit,
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "final_state": _state_document(state),
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
    }
    document = {
        **payload,
        "expression_accounted_episode_id": content_id(
            pre.FUTURE_DOMAINS["episode"], payload
        ),
    }
    return (
        canonical_json_bytes(document),
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    )


@dataclass(frozen=True, slots=True)
class _WorkerReplyV24:
    task_bytes: bytes
    episode_bytes: bytes
    episode: Mapping[str, Any]
    observed_working_peak: int


def _run_workers(
    *, episode_count: int, decision_limit: int
) -> tuple[_WorkerReplyV24, ...]:
    tasks = tuple(_episode_task(index, decision_limit) for index in range(episode_count))
    with ProcessPoolExecutor(max_workers=min(MAXIMUM_PROCESSES, episode_count)) as executor:
        raw_results = tuple(executor.map(_episode_worker, tasks, chunksize=1))
    replies = []
    for task_bytes, raw_result in zip(tasks, raw_results, strict=True):
        episode_bytes, observed_working_peak = raw_result
        episode = loads_canonical_json(episode_bytes)
        if (
            type(episode) is not dict
            or type(observed_working_peak) is not int
            or observed_working_peak < 0
            or observed_working_peak
            > pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER
        ):
            _fail("episode worker response is not canonical")
        replies.append(
            _WorkerReplyV24(
                task_bytes,
                episode_bytes,
                episode,
                observed_working_peak,
            )
        )
    return tuple(replies)


def _subject_id(role: str, evidence: Mapping[str, Any]) -> str:
    payload = {
        "schema": "acfqp.standard_2048_expression_accounting_subject.v24",
        "schema_version": SCHEMA_VERSION,
        "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "role": role,
        "evidence": dict(evidence),
    }
    return content_id(pre.FUTURE_DOMAINS["measurement"], payload)


def _bundle_summary(
    bundle: artifacts.MaterializedOperationalBundleV24
    | artifacts.MaterializedEvaluationBundleV24,
    *,
    output_root: Path,
) -> dict[str, Any]:
    document = bundle.to_document()
    vector = document["work_vector"]
    comparison = document["comparison_vector"]
    return {
        "counter_bundle_id": bundle.bundle_id,
        "window_role": document["window_role"],
        "work_vector_id": vector["work_vector_id"],
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


def _tree_file_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


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


def _materialize_campaign(
    *,
    output_root: Path,
    episode_count: int,
    decision_limit: int,
) -> tuple[dict[str, Any], tuple[bytes, ...]]:
    preregistration = pre.verify_standard_2048_expression_accounted_preregistration_v24(
        pre.freeze_standard_2048_expression_accounted_preregistration_v24()
    )
    if output_root.exists():
        _fail("V24 accounting output root must be absent")
    output_root.mkdir(mode=0o700, parents=False)
    model_dir = output_root / "model"
    model_dir.mkdir(mode=0o700)
    operational_trace, acquisition_values, proof_values = (
        _instrumented_model_synthesis("OPERATIONAL")
    )
    evaluation_trace, model_evaluation_values, empty_proof_values = (
        _instrumented_model_synthesis("EVALUATION")
    )
    if any(empty_proof_values.values()):
        _fail("model evaluation unexpectedly split operational stages")
    acquisition_evidence = {
        "structural_pool": operational_trace["structural_pool"],
        "acquisitions": operational_trace["acquisitions"],
        "proposal": operational_trace["proposal"],
        "actual_target_probability_query_invocations": 4,
        "duplicate_label_query_for_artifact_recording": False,
    }
    acquisition_subject = _subject_id(
        "MODEL_ACQUISITION_AND_SELECTION", acquisition_evidence
    )
    acquisition_bundle = artifacts.materialize_operational_bundle_v24(
        subject_id=acquisition_subject,
        window_role="MODEL_ACQUISITION_AND_SELECTION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=acquisition_values,
        evidence_document=acquisition_evidence,
        output_path=model_dir / "operational-acquisition.json",
    )
    proof_evidence = {
        "proposal_id": EXPECTED_PROPOSAL_ID,
        "proof": operational_trace["proof"],
        "world_model": operational_trace["world_model"],
    }
    proof_subject = _subject_id("MODEL_PROOF_AND_FREEZE", proof_evidence)
    proof_bundle = artifacts.materialize_operational_bundle_v24(
        subject_id=proof_subject,
        window_role="MODEL_PROOF_AND_FREEZE",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=proof_values,
        evidence_document=proof_evidence,
        output_path=model_dir / "operational-proof.json",
    )
    model_evaluation_subject = _subject_id(
        "MODEL_SYNTHESIS_STANDALONE_REPLAY",
        {
            "proposal_id": evaluation_trace["proposal"][
                "blind_expression_proposal_id"
            ],
            "proof_id": evaluation_trace["proof"]["blind_expression_proof_id"],
            "world_model_id": evaluation_trace["world_model"][
                "blind_expression_world_model_id"
            ],
        },
    )
    model_evaluation_bundle = artifacts.materialize_evaluation_bundle_v24(
        subject_id=model_evaluation_subject,
        window_role="MODEL_SYNTHESIS_STANDALONE_REPLAY",
        base_values=model_evaluation_values,
        evidence_document=evaluation_trace,
        output_path=model_dir / "evaluation-replay.json",
    )
    operational_bundles = [acquisition_bundle, proof_bundle]
    evaluation_bundles = [model_evaluation_bundle]
    replies = _run_workers(
        episode_count=episode_count, decision_limit=decision_limit
    )
    episode_summaries = []
    for episode_ordinal, reply in enumerate(replies):
        episode = dict(reply.episode)
        if episode["episode_index"] != episode_ordinal:
            _fail("worker episode order changed")
        episode_dir = output_root / f"episode-{episode_ordinal:04d}"
        episode_dir.mkdir(mode=0o700)
        worker_values = runtime.NativeCounterSetV24()
        worker_values.add("common.hash_invocations", 2)
        worker_values.add("common.integrity_checks", 2)
        worker_values.add("common.protocol_checks", 2)
        worker_values.add("io.staged_bytes", len(reply.task_bytes))
        worker_values.add("io.read_bytes", len(reply.task_bytes) + len(reply.episode_bytes))
        worker_values.add("process.launches")
        worker_values.add("process.exit_successes")
        worker_values.maximum(
            "memory.working_bytes_peak",
            pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER,
        )
        worker_subject = episode["expression_accounted_episode_id"]
        worker_bundle = artifacts.materialize_operational_bundle_v24(
            subject_id=worker_subject,
            window_role="EPISODE_WORKER_PROCESS_AND_TRANSPORT",
            route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            work_scope=ActualWorkScope.COMMON_PREFIX,
            base_values=worker_values.freeze(),
            evidence_document={
                "episode_task": loads_canonical_json(reply.task_bytes),
                "episode_id": worker_subject,
                "worker_reply_sha256": hashlib.sha256(reply.episode_bytes).hexdigest(),
                "worker_reply_byte_count": len(reply.episode_bytes),
            },
            output_path=episode_dir / "worker.json",
            external_output_bytes=len(reply.episode_bytes),
        )
        operational_bundles.append(worker_bundle)
        decision_summaries = []
        for decision in episode["decisions"]:
            decision_index = decision["decision_index"]
            decision_id = decision["expression_accounted_decision_id"]
            decision_dir = episode_dir / f"decision-{decision_index:04d}"
            decision_dir.mkdir(mode=0o700)
            operational_bundle = artifacts.materialize_operational_bundle_v24(
                subject_id=decision_id,
                window_role="ABSTRACT_CERTIFICATE_AND_SELECTED_TARGET_EXECUTION",
                route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
                work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
                base_values=decision["operational_counter_values"],
                evidence_document={
                    key: value
                    for key, value in decision.items()
                    if key
                    not in {
                        "operational_counter_values",
                        "evaluation_counter_values",
                    }
                },
                output_path=decision_dir / "operational.json",
            )
            operational_bundles.append(operational_bundle)
            evaluation_summary = None
            if decision["evaluation_counter_values"] is not None:
                evaluation_bundle = artifacts.materialize_evaluation_bundle_v24(
                    subject_id=decision_id,
                    window_role="COLD_TARGET_CHECKPOINT_STANDALONE_REPLAY",
                    base_values=decision["evaluation_counter_values"],
                    evidence_document={
                        "episode_index": episode_ordinal,
                        "decision_index": decision_index,
                        "predecision_state": decision["predecision_state"],
                        "abstract_certificate": decision["certificate"],
                        "cold_evaluation": decision["cold_evaluation"],
                    },
                    output_path=decision_dir / "evaluation.json",
                )
                evaluation_bundles.append(evaluation_bundle)
                evaluation_summary = _bundle_summary(
                    evaluation_bundle, output_root=output_root
                )
            decision_summaries.append(
                {
                    "decision_id": decision_id,
                    "decision_index": decision_index,
                    "route": decision["route"],
                    "selected_action": decision["executed_action"],
                    "operational_bundle": _bundle_summary(
                        operational_bundle, output_root=output_root
                    ),
                    "evaluation_bundle": evaluation_summary,
                }
            )
        episode_summaries.append(
            {
                "episode_id": episode["expression_accounted_episode_id"],
                "episode_index": episode_ordinal,
                "decision_count": episode["decision_count"],
                "closure_reason": episode["closure_reason"],
                "final_state": episode["final_state"],
                "maximum_final_board_tile_rank": episode[
                    "maximum_final_board_tile_rank"
                ],
                "tile_2048_reached": episode["tile_2048_reached"],
                "worker_bundle": _bundle_summary(
                    worker_bundle, output_root=output_root
                ),
                "decisions": decision_summaries,
            }
        )
    decision_rows = [
        decision
        for episode in episode_summaries
        for decision in episode["decisions"]
    ]
    campaign_subject_evidence = {
        "episode_ids": [row["episode_id"] for row in episode_summaries],
        "decision_count": len(decision_rows),
        "model_operational_bundle_ids": [
            acquisition_bundle.bundle_id,
            proof_bundle.bundle_id,
        ],
        "model_evaluation_bundle_id": model_evaluation_bundle.bundle_id,
    }
    campaign_subject = _subject_id(
        "CAMPAIGN_AGGREGATION_AND_TERMINALIZATION",
        campaign_subject_evidence,
    )
    mounted_before = _tree_file_bytes(output_root)
    campaign_values = runtime.NativeCounterSetV24()
    campaign_values.add("common.hash_invocations", 3)
    campaign_values.add("common.integrity_checks", 4)
    campaign_values.add("common.protocol_checks", 4)
    campaign_values.maximum("io.mounted_bytes_peak", mounted_before)
    if (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        > pre.CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER
    ):
        _fail("campaign parent exceeded preregistered working-byte cap")
    campaign_values.maximum(
        "memory.working_bytes_peak",
        pre.CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER,
    )
    campaign_bundle = artifacts.materialize_operational_bundle_v24(
        subject_id=campaign_subject,
        window_role="CAMPAIGN_AGGREGATION_AND_TERMINALIZATION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=campaign_values.freeze(),
        evidence_document=campaign_subject_evidence,
        output_path=output_root / "campaign.json",
    )
    operational_bundles.append(campaign_bundle)
    totals = {axis: 0 for axis in SHARED_AXES}
    prefix = []
    for sequence_index, bundle in enumerate(operational_bundles):
        totals = _accumulate_comparison(
            totals, bundle.chain.comparison_vector.values
        )
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
                    {"axis": axis, "value": totals[axis]}
                    for axis in SHARED_AXES
                ],
            }
        )
    registry = registry_v9.official_counter_registry_v9()
    evaluation_totals = {
        path: sum(bundle.work_vector.value(path) for bundle in evaluation_bundles)
        for path in registry.by_path
        if path.startswith("evaluation.")
    }
    planning_rows = sum(
        bundle.chain.work_vector.value("common.abstract_bellman_backups")
        for bundle in operational_bundles
    )
    planning_outcomes = sum(
        bundle.chain.work_vector.value("common.abstract_support_outcome_evaluations")
        for bundle in operational_bundles
    )
    target_steps = sum(
        bundle.chain.work_vector.value("target.execution_ground_steps")
        for bundle in operational_bundles
    )
    model_event_total = sum(
        bundle.chain.work_vector.value(path)
        for bundle in operational_bundles
        for path in pre.MODEL_OPERATIONAL_PATHS
    )
    payload = {
        "schema": "acfqp.standard_2048_expression_accounted_campaign.v24",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "expression_accounted_preregistration": preregistration.to_document(),
        "model_operational_bundles": [
            _bundle_summary(acquisition_bundle, output_root=output_root),
            _bundle_summary(proof_bundle, output_root=output_root),
        ],
        "model_evaluation_bundle": _bundle_summary(
            model_evaluation_bundle, output_root=output_root
        ),
        "episodes": episode_summaries,
        "episode_count": len(episode_summaries),
        "decision_count": len(decision_rows),
        "model_certificate_count": len(decision_rows),
        "local_ground_recovery_count": 0,
        "cold_evaluation_checkpoint_count": sum(
            row["evaluation_bundle"] is not None for row in decision_rows
        ),
        "operational_work_vector_count": len(operational_bundles),
        "evaluation_work_vector_count": len(evaluation_bundles),
        "campaign_bundle": _bundle_summary(
            campaign_bundle, output_root=output_root
        ),
        "vector_prefix_totals": prefix,
        "final_operational_comparison_totals": [
            {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
        ],
        "evaluation_lane_totals": evaluation_totals,
        "model_operational_nonkernel_event_count": model_event_total,
        "operational_target_probability_label_query_count": 4,
        "unique_operational_target_probability_label_count": 4,
        "duplicate_operational_label_query_count": 0,
        "strict_no_prior_target_probability_label_count": 8,
        "target_probability_label_fraction_of_no_prior": Fraction(1, 2),
        "operational_abstract_bellman_backup_count": planning_rows,
        "operational_abstract_support_outcome_evaluation_count": planning_outcomes,
        "operational_target_execution_ground_step_count": target_steps,
        "all_registered_decisions_use_synthesized_world_model": True,
        "all_registered_decisions_certificate_before_target_execution": True,
        "all_required_counter_leaves_have_explicit_native_records": True,
        "all_nine_shared_resource_paths_have_measurement_receipts": True,
        "evaluation_replay_excluded_from_operational_comparison": True,
        "registered_profile_counter_completeness_candidate": True,
        "measurement_replays_revealed_target_not_fresh_blind_science": True,
        "sample_tax_reduced_on_registered_label_axis": True,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": any(row["tile_2048_reached"] for row in episode_summaries),
        "maximum_final_board_tile_rank": max(
            row["maximum_final_board_tile_rank"] for row in episode_summaries
        ),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "expression_accounted_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }
    bundle_bytes = tuple(
        bundle.canonical_bytes
        for bundle in (*operational_bundles, *evaluation_bundles)
    )
    return document, bundle_bytes


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionAccountedCampaignV24:
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
            _fail("accounted campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            _fail("accounted campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_accounted_campaign_id"
        }
        if (
            document.get("expression_accounted_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload)
            != self.campaign_id
        ):
            _fail("accounted campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("accounted campaign is not an object")
        return document


def run_standard_2048_expression_accounted_campaign_v24(
    output_root: Path,
) -> Standard2048ExpressionAccountedCampaignV24:
    if not isinstance(output_root, Path):
        _fail("accounted campaign output root must be one Path")
    document, _ = _materialize_campaign(
        output_root=output_root,
        episode_count=len(long_pre.INITIAL_BOARDS),
        decision_limit=long_pre.MAXIMUM_DECISIONS_PER_EPISODE,
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["expression_accounted_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen full accounted campaign outcome changed")
    return Standard2048ExpressionAccountedCampaignV24(
        _ISSUER,
        raw,
        document["expression_accounted_campaign_id"],
        output_root,
    )


def verify_standard_2048_expression_accounted_campaign_v24(
    value: Standard2048ExpressionAccountedCampaignV24,
) -> Standard2048ExpressionAccountedCampaignV24:
    if type(value) is not Standard2048ExpressionAccountedCampaignV24:
        _fail("accounted campaign verifier rejects foreign values")
    value.__post_init__()
    document = value.to_document()
    summaries = [
        *document["model_operational_bundles"],
        document["model_evaluation_bundle"],
        document["campaign_bundle"],
    ]
    for episode in document["episodes"]:
        summaries.append(episode["worker_bundle"])
        for decision in episode["decisions"]:
            summaries.append(decision["operational_bundle"])
            if decision["evaluation_bundle"] is not None:
                summaries.append(decision["evaluation_bundle"])
    if len(summaries) != (
        document["operational_work_vector_count"]
        + document["evaluation_work_vector_count"]
    ):
        _fail("accounted bundle inventory changed")
    for summary in summaries:
        raw = (value.output_root / summary["output_key"]).read_bytes()
        row = loads_canonical_json(raw)
        if (
            type(row) is not dict
            or len(raw) != summary["canonical_byte_count"]
            or hashlib.sha256(raw).hexdigest() != summary["canonical_sha256"]
            or row.get("expression_accounted_counter_bundle_id")
            != summary["counter_bundle_id"]
        ):
            _fail("accounted bundle bytes changed")
    if (
        document["operational_target_probability_label_query_count"] != 4
        or document["duplicate_operational_label_query_count"] != 0
        or document["all_required_counter_leaves_have_explicit_native_records"]
        is not True
        or document["official_execution_allowed"] is not False
        or document["counter_completeness_gate_status"] != "NOT_RUN"
    ):
        _fail("accounted campaign claim locks changed")
    return value


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "Standard2048ExpressionAccountedCampaignV24",
    "_instrumented_model_synthesis",
    "_materialize_campaign",
    "run_standard_2048_expression_accounted_campaign_v24",
    "verify_standard_2048_expression_accounted_campaign_v24",
)
