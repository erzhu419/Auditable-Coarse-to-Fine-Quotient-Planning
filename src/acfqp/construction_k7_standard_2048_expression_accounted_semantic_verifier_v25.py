"""Independent semantic replay of the V24 accounted 2048 campaign.

The V24 verifier establishes the content-addressed accounting DAG.  This
successor also reconstructs model synthesis and every registered planning
window without importing the V24 producer or its counter emitter.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_standard_2048_blind_expression_independent_verifier_v22 as v22
from acfqp import construction_k7_standard_2048_expression_accounted_independent_verifier_v24 as bytes_v24
from acfqp import construction_k7_standard_2048_expression_accounted_preregistration_v24 as pre
from acfqp import construction_k7_standard_2048_expression_long_independent_verifier_v23 as v23
from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as long_pre
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_SEMANTIC_VERIFICATION_V25_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "25.0.0"
EXPECTED_VERIFICATION_ID = "0c9957d0d5a7832ef0a9e2f9cfe0bb2ab1e2329b990f89c5d12e2498957fe258"
EXPECTED_CANONICAL_BYTE_COUNT = 1313
EXPECTED_CANONICAL_SHA256 = "5828472f888c51be7f05eb382c281c79cf51ee838c3863897e5ca9b142b7ac15"
_MODEL_TOTALS = {
    "structural_context_rows_frozen": 8,
    "structural_expression_value_evaluations": 224,
    "expression_candidates_materialized": 80,
    "candidate_label_consistency_checks": 142,
    "active_query_partition_evaluations": 399,
    "target_probability_labels_acquired": 4,
    "exact_program_proof_rows_evaluated": 17,
    "world_model_freezes": 1,
}
_COLD_CHECKPOINTS = frozenset(long_pre.COLD_EVALUATION_CHECKPOINTS)


class ConstructionK7Standard2048ExpressionAccountedSemanticVerifierV25Error(
    RuntimeError
):
    """A retained accounting value differs from independent semantics."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionAccountedSemanticVerifierV25Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ExpressionAccountedSemanticVerifierV25Error(
            f"{label} is not canonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} canonical bytes changed")
    return document


def _state(document: Any) -> Any:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("accounted state shape changed")
    state = state_from_board_v1(tuple(document["board_ranks"]))
    if state.status.value != document["status"]:
        _fail("accounted state status changed")
    return state


def _bundle(root: Path, summary: Mapping[str, Any]) -> dict[str, Any]:
    if type(summary) is not dict or type(summary.get("output_key")) is not str:
        _fail("accounting summary changed")
    key = Path(summary["output_key"])
    if key.is_absolute() or ".." in key.parts:
        _fail("accounting output key escaped its root")
    raw = (root / key).read_bytes()
    if (
        summary.get("canonical_byte_count") != len(raw)
        or summary.get("canonical_sha256") != hashlib.sha256(raw).hexdigest()
    ):
        _fail("accounting summary bytes changed")
    return _object(raw, summary["output_key"])


def _values(document: Mapping[str, Any]) -> dict[str, int]:
    vector = document.get("work_vector")
    records = vector.get("records") if type(vector) is dict else None
    if type(records) is not list:
        _fail("semantic verifier lost CounterRecords")
    result = {}
    for row in records:
        if type(row) is not dict or type(row.get("path")) is not str:
            _fail("semantic CounterRecord shape changed")
        result[row["path"]] = row.get("value")
    if len(result) != len(records) or any(type(value) is not int for value in result.values()):
        _fail("semantic CounterRecord inventory changed")
    return result


def _model_expected() -> tuple[dict[str, Any], dict[str, int], dict[str, int]]:
    pool = v22._pool_expected()  # noqa: SLF001
    candidates, native = v22._candidates_expected(pool, v22.OVERRIDE_RATE)  # noqa: SLF001
    acquisitions, selected = v22._acquire_expected(pool, native)  # noqa: SLF001
    proposal = v22._proposal_expected(pool, candidates, acquisitions, selected)  # noqa: SLF001
    proof = v22._proof_expected(proposal)  # noqa: SLF001
    world = v22._world_expected(proposal, proof)  # noqa: SLF001
    trace = {
        "structural_pool": pool,
        "acquisitions": acquisitions,
        "proposal": proposal,
        "proof": proof,
        "world_model": world,
    }
    remaining = tuple(candidate for candidate in native if candidate[4][0] == v22._target_probability(  # noqa: SLF001
        tuple(pool["rows"][0]["post_swipe_board_ranks"])
    ))
    queried = {0}
    consistency_checks = len(native)
    partition_evaluations = 0
    while len(remaining) > 1:
        choices = []
        for ordinal in range(len(pool["rows"])):
            if ordinal in queried:
                continue
            buckets: dict[Fraction, int] = {}
            for candidate in remaining:
                partition_evaluations += 1
                prediction = candidate[4][ordinal]
                buckets[prediction] = buckets.get(prediction, 0) + 1
            if len(buckets) > 1:
                choices.append((max(buckets.values()), ordinal))
        if not choices:
            _fail("independent acquisition counter replay cannot separate candidates")
        _, ordinal = min(choices)
        queried.add(ordinal)
        before = remaining
        observed = v22._target_probability(  # noqa: SLF001
            tuple(pool["rows"][ordinal]["post_swipe_board_ranks"])
        )
        consistency_checks += len(before)
        remaining = tuple(
            candidate for candidate in before if candidate[4][ordinal] == observed
        )
    acquisition = {
        "model.structural_context_rows_frozen": len(pool["rows"]),
        "model.structural_expression_value_evaluations": sum(
            len(row["expression_values"]) for row in pool["rows"]
        ),
        "model.expression_candidates_materialized": len(candidates),
        "model.candidate_label_consistency_checks": consistency_checks,
        "model.active_query_partition_evaluations": partition_evaluations,
        "model.target_probability_labels_acquired": len(acquisitions),
        "common.hash_invocations": (
            len(pool["rows"]) + 1 + len(candidates) + len(acquisitions) + 1
        ),
        "common.integrity_checks": len(acquisitions),
        "common.protocol_checks": 1,
    }
    proof_values = {
        "model.exact_program_proof_rows_evaluated": len(proof["proof_rows"]),
        "model.world_model_freezes": 1,
        "common.hash_invocations": 2,
        "common.integrity_checks": len(proof["proof_rows"]),
        "common.protocol_checks": 2,
    }
    return trace, acquisition, proof_values


def _assert_sparse_values(
    observed: Mapping[str, int], expected_nonzero: Mapping[str, int], label: str
) -> None:
    for path, value in expected_nonzero.items():
        if observed.get(path) != value:
            _fail(f"{label} counter {path} changed")
    allowed = set(expected_nonzero) | {
        "io.output_bytes",
        "evaluation.io_output_bytes",
    }
    if any(value and path not in allowed for path, value in observed.items()):
        _fail(f"{label} contains an unexplained nonzero counter")


class _ColdPlanner(v22._Planner):  # noqa: SLF001
    def __init__(self) -> None:
        super().__init__()
        self.active_state_expansions = 0

    def state_value(self, board: tuple[int, ...], status: str, remaining: int) -> Any:
        canonical = v22._canonical(board)  # noqa: SLF001
        unseen = (canonical, status, remaining) not in self.cache
        if unseen and remaining > 0 and status == Swipe2048Status.ACTIVE.value:
            self.active_state_expansions += 1
        return super().state_value(board, status, remaining)


def _independent_cold(state: Any) -> tuple[dict[str, Any], dict[str, int]]:
    planner = _ColdPlanner()
    values = planner.roots(state)
    best = None
    for value in values:
        if v22._better(value, best):  # noqa: SLF001
            best = value
    if best is None or best.action is None:
        _fail("cold semantic replay has no action")
    document = {
        "root_action_exact_values": [
            {
                "action": value.action,
                "expected_merge_score": value.score,
                "loss_probability_within_horizon": value.loss,
            }
            for value in values
        ],
        "selected_action": best.action,
        "selected_expected_merge_score": best.score,
        "selected_loss_probability_within_horizon": best.loss,
        "ground_state_action_row_count": planner.rows,
        "ground_outcome_count": planner.outcomes,
        "lane": "STANDALONE_EVALUATION_ONLY",
        "route_or_certificate_authority": False,
    }
    counters = {
        "evaluation.exact_states_expanded": planner.active_state_expansions + 1,
        "evaluation.exact_actions_evaluated": planner.rows,
        "evaluation.exact_ground_steps": planner.rows,
        "evaluation.exact_outcome_rows": planner.outcomes,
        "evaluation.exact_bellman_backups": planner.rows,
        "evaluation.exact_subproof_cache_lookups": planner.hits + planner.misses,
        "evaluation.exact_subproof_cache_hits": planner.hits,
        "evaluation.exact_subproof_cache_misses": planner.misses,
        "evaluation.semantic_integrity_checks": 1,
        "evaluation.semantic_protocol_checks": 1,
    }
    return document, counters


def _verify_episode(task: tuple[int, Mapping[str, Any], str]) -> dict[str, int]:
    episode_index, summary, output_root = task
    root = Path(output_root)
    state = state_from_board_v1(long_pre.INITIAL_BOARDS[episode_index])
    planner = v23._PersistentPlanner()  # noqa: SLF001
    worker_bundle = _bundle(root, summary["worker_bundle"])
    worker_evidence = worker_bundle.get("evidence")
    if type(worker_evidence) is not dict or type(worker_evidence.get("episode_task")) is not dict:
        _fail("worker evidence changed")
    episode_task = worker_evidence["episode_task"]
    task_payload = {
        key: value
        for key, value in episode_task.items()
        if key != "expression_accounted_measurement_id"
    }
    if (
        content_id(pre.FUTURE_DOMAINS["measurement"], task_payload)
        != episode_task.get("expression_accounted_measurement_id")
        or episode_task.get("expression_accounted_preregistration_id") != pre.PREREGISTRATION_ID
        or episode_task.get("episode_index") != episode_index
        or episode_task.get("initial_board_ranks") != list(long_pre.INITIAL_BOARDS[episode_index])
        or episode_task.get("execution_seed") != long_pre.EPISODE_SEEDS[episode_index]
        or episode_task.get("decision_limit") != 32
        or episode_task.get("planning_horizon") != 3
        or episode_task.get("world_model_id") != v23.V22_WORLD_MODEL_ID
    ):
        _fail("worker episode task differs from preregistration")
    decisions = summary.get("decisions")
    if type(decisions) is not list or len(decisions) != 32:
        _fail("semantic decision inventory changed")
    totals = {"rows": 0, "outcomes": 0, "hits": 0, "misses": 0, "cross": 0}
    reconstructed_decisions = []
    for decision_index, row in enumerate(decisions):
        replay = planner.plan(state)
        bundle = _bundle(root, row["operational_bundle"])
        evidence = bundle.get("evidence")
        certificate = evidence.get("certificate") if type(evidence) is dict else None
        if (
            type(certificate) is not dict
            or row.get("decision_index") != decision_index
            or row.get("decision_id") != evidence.get("expression_accounted_decision_id")
            or row.get("route") != evidence.get("route")
            or row.get("selected_action") != evidence.get("executed_action")
            or evidence.get("episode_index") != episode_index
            or evidence.get("decision_index") != decision_index
            or _state(evidence.get("predecision_state")) != state
            or certificate.get("root_action_exact_values") != replay["root_action_exact_values"]
            or certificate.get("selected_action") != replay["selected_action"]
            or certificate.get("selected_expected_merge_score") != replay["selected_expected_merge_score"]
            or certificate.get("selected_loss_probability_within_horizon") != replay["selected_loss_probability_within_horizon"]
            or certificate.get("factored_action_row_evaluation_count") != replay["rows"]
            or certificate.get("factored_support_outcome_evaluation_count") != replay["outcomes"]
            or certificate.get("subproof_cache_hit_count") != replay["hits"]
            or certificate.get("subproof_cache_miss_count") != replay["misses"]
            or certificate.get("cross_decision_subproof_cache_hit_count") != replay["cross_hits"]
            or certificate.get("operational_target_probability_query_count") != 0
            or certificate.get("operational_ground_state_action_row_count") != 0
            or certificate.get("status") != "CERTIFIED_PERSISTENT_EXPRESSION_MODEL_H3"
            or evidence.get("certificate_frozen_before_evaluation_and_target_transition") is not True
        ):
            _fail("accounted certificate differs from independent H3 replay")
        target_outcomes = v22._target_outcomes(  # noqa: SLF001
            state, Swipe2048Action(replay["selected_action"])
        )
        expected_operational = {
            "common.abstract_bellman_backups": replay["rows"],
            "common.abstract_support_outcome_evaluations": replay["outcomes"],
            "common.abstract_subproof_cache_lookups": replay["hits"] + replay["misses"],
            "common.abstract_subproof_cache_hits": replay["hits"],
            "common.abstract_subproof_cache_misses": replay["misses"],
            "common.protocol_checks": 2,
            "common.integrity_checks": 2,
            "common.hash_invocations": 2,
            "route.attempts": 1,
            "route.successes": 1,
            "target.execution_ground_steps": 1,
            "target.execution_outcome_rows": len(target_outcomes),
            "target.transition_observations": 1,
        }
        operational_values = _values(bundle)
        _assert_sparse_values(operational_values, expected_operational, "decision")
        evaluation = row.get("evaluation_bundle")
        evaluation_values = None
        if decision_index in _COLD_CHECKPOINTS:
            if evaluation is None:
                _fail("registered cold checkpoint disappeared")
            cold_document, cold_counters = _independent_cold(state)
            evaluation_bundle = _bundle(root, evaluation)
            if evidence.get("cold_evaluation") != cold_document:
                _fail("cold evidence differs from independent exact replay")
            evaluation_evidence = evaluation_bundle.get("evidence")
            if (
                type(evaluation_evidence) is not dict
                or evaluation_evidence.get("episode_index") != episode_index
                or evaluation_evidence.get("decision_index") != decision_index
                or evaluation_evidence.get("predecision_state") != evidence.get("predecision_state")
                or evaluation_evidence.get("abstract_certificate") != certificate
                or evaluation_evidence.get("cold_evaluation") != cold_document
            ):
                _fail("cold evaluation evidence binding changed")
            evaluation_values = _values(evaluation_bundle)
            _assert_sparse_values(
                evaluation_values, cold_counters, "cold evaluation"
            )
        elif evaluation is not None or evidence.get("cold_evaluation") is not None:
            _fail("unregistered cold checkpoint appeared")
        outcome, tape = select_seeded_outcome_v1(
            target_outcomes,
            seed=long_pre.EPISODE_SEEDS[episode_index],
            decision_index=decision_index,
        )
        if (
            evidence.get("executed_action") != replay["selected_action"]
            or evidence.get("execution_tape_sha256") != tape
            or _state(evidence.get("executed_next_state")) != outcome.next_state
            or evidence.get("online_target_transition_observation_count") != 1
            or evidence.get("execution_transition_used_to_modify_world_model") is not False
        ):
            _fail("accounted target transition differs from independent replay")
        operational_base_values = dict(operational_values)
        operational_base_values["io.output_bytes"] = 0
        evaluation_base_values = None
        if evaluation_values is not None:
            evaluation_base_values = dict(evaluation_values)
            evaluation_base_values["evaluation.io_output_bytes"] = 0
        reconstructed = {
            **evidence,
            "operational_counter_values": operational_base_values,
            "evaluation_counter_values": evaluation_base_values,
        }
        decision_payload = {
            key: value
            for key, value in reconstructed.items()
            if key != "expression_accounted_decision_id"
        }
        if content_id(pre.FUTURE_DOMAINS["decision"], decision_payload) != reconstructed.get(
            "expression_accounted_decision_id"
        ):
            _fail("business decision identity differs from reconstructed counters")
        reconstructed_decisions.append(reconstructed)
        state = outcome.next_state
        totals["rows"] += replay["rows"]
        totals["outcomes"] += replay["outcomes"]
        totals["hits"] += replay["hits"]
        totals["misses"] += replay["misses"]
        totals["cross"] += replay["cross_hits"]
    final_state = {
        "board_ranks": list(state.board),
        "status": state.status.value,
    }
    if (
        summary.get("episode_index") != episode_index
        or summary.get("decision_count") != len(reconstructed_decisions)
        or summary.get("closure_reason") != (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        )
        or summary.get("final_state") != final_state
        or summary.get("maximum_final_board_tile_rank") != max(state.board)
        or summary.get("tile_2048_reached") is not (max(state.board) >= GOAL_RANK)
    ):
        _fail("accounted episode final state changed")
    initial_state = {
        "board_ranks": list(long_pre.INITIAL_BOARDS[episode_index]),
        "status": Swipe2048Status.ACTIVE.value,
    }
    episode_payload = {
        "schema": "acfqp.standard_2048_expression_accounted_business_episode.v24",
        "schema_version": pre.SCHEMA_VERSION,
        "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_task_id": episode_task["expression_accounted_measurement_id"],
        "episode_index": episode_index,
        "execution_seed": long_pre.EPISODE_SEEDS[episode_index],
        "initial_state": initial_state,
        "decisions": reconstructed_decisions,
        "decision_count": len(reconstructed_decisions),
        "maximum_registered_decision_count": 32,
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "model_certificate_count": len(reconstructed_decisions),
        "local_ground_recovery_count": 0,
        "final_state": final_state,
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
    }
    episode_document = {
        **episode_payload,
        "expression_accounted_episode_id": content_id(
            pre.FUTURE_DOMAINS["episode"], episode_payload
        ),
    }
    episode_raw = canonical_json_bytes(episode_document)
    if (
        worker_evidence.get("episode_id") != episode_document["expression_accounted_episode_id"]
        or summary.get("episode_id") != episode_document["expression_accounted_episode_id"]
        or worker_evidence.get("worker_reply_byte_count") != len(episode_raw)
        or worker_evidence.get("worker_reply_sha256") != hashlib.sha256(episode_raw).hexdigest()
    ):
        _fail("worker reply differs from independently reconstructed episode")
    worker_expected = {
        "common.hash_invocations": 2,
        "common.integrity_checks": 2,
        "common.protocol_checks": 2,
        "io.staged_bytes": len(canonical_json_bytes(episode_task)),
        "io.read_bytes": len(canonical_json_bytes(episode_task)) + len(episode_raw),
        "process.launches": 1,
        "process.exit_successes": 1,
        "memory.working_bytes_peak": pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER,
    }
    _assert_sparse_values(_values(worker_bundle), worker_expected, "episode worker")
    return totals


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionAccountedSemanticVerificationV25:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("semantic verification is not issuer-created")
        document = _object(self.canonical_bytes, "semantic verification")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_accounted_semantic_verification_id"
        }
        if (
            document.get("expression_accounted_semantic_verification_id")
            != self.verification_id
            or document.get("expression_accounted_campaign_id") != self.campaign_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_SEMANTIC_VERIFICATION_V25_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("semantic verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("semantic verification is not an object")
        return document


_ISSUER = object()


def verify_standard_2048_expression_accounting_semantics_v25(
    campaign_bytes: bytes, output_root: Path
) -> Standard2048ExpressionAccountedSemanticVerificationV25:
    bytes_result = bytes_v24.verify_standard_2048_expression_accounting_bytes_independently_v24(
        campaign_bytes, output_root
    )
    campaign = _object(campaign_bytes, "V24 campaign")
    trace, acquisition_expected, proof_expected = _model_expected()
    model_operational = campaign.get("model_operational_bundles")
    if type(model_operational) is not list or len(model_operational) != 2:
        _fail("model operational bundle inventory changed")
    acquisition = _bundle(output_root, model_operational[0])
    proof = _bundle(output_root, model_operational[1])
    if (
        acquisition.get("evidence", {}).get("structural_pool") != trace["structural_pool"]
        or acquisition.get("evidence", {}).get("acquisitions") != trace["acquisitions"]
        or acquisition.get("evidence", {}).get("proposal") != trace["proposal"]
        or proof.get("evidence", {}).get("proof") != trace["proof"]
        or proof.get("evidence", {}).get("world_model") != trace["world_model"]
    ):
        _fail("model evidence differs from independent synthesis")
    _assert_sparse_values(_values(acquisition), acquisition_expected, "model acquisition")
    _assert_sparse_values(_values(proof), proof_expected, "model proof")
    model_evaluation = _bundle(output_root, campaign["model_evaluation_bundle"])
    model_evaluation_evidence = model_evaluation.get("evidence")
    expected_evaluation_totals = [
        {"path": "evaluation." + path, "value": value}
        for path, value in _MODEL_TOTALS.items()
    ]
    if (
        type(model_evaluation_evidence) is not dict
        or model_evaluation_evidence.get("lane") != "EVALUATION"
        or model_evaluation_evidence.get("structural_pool") != trace["structural_pool"]
        or model_evaluation_evidence.get("acquisitions") != trace["acquisitions"]
        or model_evaluation_evidence.get("proposal") != trace["proposal"]
        or model_evaluation_evidence.get("proof") != trace["proof"]
        or model_evaluation_evidence.get("world_model") != trace["world_model"]
        or model_evaluation_evidence.get("registered_event_totals")
        != expected_evaluation_totals
        or model_evaluation_evidence.get("unique_target_probability_labels") != 4
        or model_evaluation_evidence.get("actual_target_probability_query_invocations") != 4
        or model_evaluation_evidence.get("duplicate_label_query_for_artifact_recording") is not False
    ):
        _fail("evaluation model trace differs from independent synthesis")
    evaluation_expected = {
        "evaluation." + path.removeprefix("model."): value
        for path, value in {**acquisition_expected, **proof_expected}.items()
        if path.startswith("model.")
    }
    evaluation_expected.update(
        {
            "evaluation.hash_invocations": 96,
            "evaluation.semantic_integrity_checks": 21,
            "evaluation.semantic_protocol_checks": 3,
        }
    )
    _assert_sparse_values(_values(model_evaluation), evaluation_expected, "model evaluation")
    episodes = campaign.get("episodes")
    if type(episodes) is not list or len(episodes) != 4:
        _fail("semantic episode inventory changed")
    with ProcessPoolExecutor(max_workers=4) as executor:
        totals = list(
            executor.map(
                _verify_episode,
                ((index, episode, str(output_root)) for index, episode in enumerate(episodes)),
                chunksize=1,
            )
        )
    aggregate = {
        key: sum(row[key] for row in totals)
        for key in ("rows", "outcomes", "hits", "misses", "cross")
    }
    campaign_bundle = _bundle(output_root, campaign["campaign_bundle"])
    campaign_evidence = campaign_bundle.get("evidence")
    expected_campaign_evidence = {
        "episode_ids": [episode["episode_id"] for episode in episodes],
        "decision_count": 128,
        "model_operational_bundle_ids": [
            row["counter_bundle_id"] for row in model_operational
        ],
        "model_evaluation_bundle_id": campaign["model_evaluation_bundle"][
            "counter_bundle_id"
        ],
    }
    if campaign_evidence != expected_campaign_evidence:
        _fail("campaign aggregation evidence changed")
    campaign_key = campaign["campaign_bundle"]["output_key"]
    mounted_before = sum(
        path.stat().st_size
        for path in output_root.rglob("*.json")
        if path.relative_to(output_root).as_posix() != campaign_key
    )
    _assert_sparse_values(
        _values(campaign_bundle),
        {
            "common.hash_invocations": 3,
            "common.integrity_checks": 4,
            "common.protocol_checks": 4,
            "io.mounted_bytes_peak": mounted_before,
            "memory.working_bytes_peak": pre.CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER,
        },
        "campaign aggregation",
    )
    if (
        campaign.get("operational_abstract_bellman_backup_count") != aggregate["rows"]
        or campaign.get("operational_abstract_support_outcome_evaluation_count") != aggregate["outcomes"]
        or campaign.get("operational_target_execution_ground_step_count") != 128
        or campaign.get("model_operational_nonkernel_event_count") != sum(_MODEL_TOTALS.values())
        or campaign.get("operational_target_probability_label_query_count") != 4
        or campaign.get("unique_operational_target_probability_label_count") != 4
        or campaign.get("strict_no_prior_target_probability_label_count") != 8
        or campaign.get("target_probability_label_fraction_of_no_prior") != Fraction(1, 2)
        or campaign.get("local_ground_recovery_count") != 0
        or campaign.get("full_standard_2048_game_completed") is not False
        or campaign.get("official_execution_allowed") is not False
    ):
        _fail("semantic campaign aggregate or claim boundary changed")
    payload = {
        "schema": "acfqp.standard_2048_expression_accounted_semantic_verification.v25",
        "schema_version": SCHEMA_VERSION,
        "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_accounted_campaign_id": bytes_result.campaign_id,
        "accounting_bundle_verification_id": bytes_result.verification_id,
        "independent_model_synthesis_replay": True,
        "independent_model_counter_replay": True,
        "independent_h3_certificate_replay_count": 128,
        "independent_cold_checkpoint_replay_count": 12,
        "independent_seeded_target_transition_replay_count": 128,
        "independent_decision_counter_window_replay_count": 128,
        "exact_rational_precision_preserved": True,
        "registered_label_axis_sample_tax_reduction_verified": True,
        "broad_iid_or_total_work_sample_efficiency_verified": False,
        "full_game_or_tile_2048_verified": False,
        "registered_profile_counter_completeness_candidate_verified": True,
        "global_counter_completeness_gate_passed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_SEMANTIC_VERIFICATION_V25_DOMAIN,
        payload,
    )
    raw = canonical_json_bytes(
        {**payload, "expression_accounted_semantic_verification_id": verification_id}
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen semantic verification identity changed")
    if EXPECTED_CANONICAL_BYTE_COUNT and (
        len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen semantic verification bytes changed")
    return Standard2048ExpressionAccountedSemanticVerificationV25(
        _ISSUER, raw, verification_id, bytes_result.campaign_id
    )


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048ExpressionAccountedSemanticVerificationV25",
    "verify_standard_2048_expression_accounting_semantics_v25",
)
