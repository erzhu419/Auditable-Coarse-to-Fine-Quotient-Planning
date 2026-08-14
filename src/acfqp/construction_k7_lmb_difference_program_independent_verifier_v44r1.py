"""Producer-free reconstruction of the V44r1 raw-difference LMB campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_difference_grammar_preregistration_v44 as base
from acfqp import (
    construction_k7_lmb_difference_grammar_successor_preregistration_v44r1 as pre,
)
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


PROFILE_KEY = "construction_k7_lmb_difference_program_independent_verification_v44r1"
EXPECTED_CAMPAIGN_ID = "3fdf113eb789fca2ceb033a430cc6491fc2ffc2a7cc0408e2929aeff6b414b35"
EXPECTED_CAMPAIGN_BYTE_COUNT = 583_171
EXPECTED_CAMPAIGN_SHA256 = "0c9b90c3ea45d5d9032e2de4554218f8bfe70656e20c6be65cf66daf281577cf"
EXPECTED_VERIFICATION_ID = "3c7f833428bcc92f4f3003caea638b1dd81a97a94f7ff1af8b817a8f3e8e3be1"
EXPECTED_CANONICAL_BYTE_COUNT = 2_394
EXPECTED_CANONICAL_SHA256 = "e3a993941f5a85bff00360f9128cbdc9d5e3e9979213cdc71dc49280f063bb33"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_lmb_difference_grammar_preregistration_v44.py",
    "src/acfqp/construction_k7_lmb_difference_grammar_failure_v44.py",
    "src/acfqp/construction_k7_lmb_difference_grammar_successor_preregistration_v44r1.py",
    "src/acfqp/domains/matching_buffer.py",
)


class ConstructionK7LMBDifferenceProgramIndependentVerifierV44R1Error(ValueError):
    """The V44r1 bytes fail independent raw-difference or plan replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBDifferenceProgramIndependentVerifierV44R1Error(message)


def _state(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


def _action(action: LMBAction) -> dict[str, int]:
    return {"tile": action.tile}


def _mode_complete(mode: str, rows: list[dict[str, Any]]) -> bool:
    if mode == "REWRITE_AND_SUCCESS_COVERAGE":
        return (
            any(row["selected_count_before"] < row["selected_count_after"] for row in rows)
            and any(row["selected_count_before"] > row["selected_count_after"] for row in rows)
            and any(row["post_board_empty"] and row["post_status"] == "success" for row in rows)
        )
    return (
        any(row["post_load"] == row["capacity"] and row["post_status"] == "active" for row in rows)
        and any(
            row["post_load"] == row["capacity"] + 1 and row["post_status"] == "failure"
            for row in rows
        )
    )


def _expected_v44_episode(seed: int, mode: str) -> tuple[list[dict[str, Any]], str]:
    kernel, witness = generate_solvable_lmb(seed=seed, **base.SOURCE_SPEC)
    del witness
    state = kernel.initial_distribution()[0][1]
    visits: dict[int, int] = {}
    rows = []
    while state.status is LMBStatus.ACTIVE:
        ranked = []
        for action in kernel.actions(state):
            selected = state.buffer[kernel.tile_types[action.tile]]
            score = (
                selected if mode == "REWRITE_AND_SUCCESS_COVERAGE" else -selected,
                -visits.get(selected, 0),
                sum(state.buffer),
                -action.tile,
            )
            ranked.append((score, action))
        score, action = max(ranked)
        component = kernel.tile_types[action.tile]
        outcome = kernel.step(state, action)[0]
        successor = outcome.next_state
        changed = [
            index
            for index, (before, after) in enumerate(zip(state.buffer, successor.buffer))
            if before != after
        ]
        payload = {
            "schema": "acfqp.lmb_raw_transition_observation.v44",
            "schema_version": base.SCHEMA_VERSION,
            "preregistration_id": base.PREREGISTRATION_ID,
            "mode": mode,
            "source_seed": seed,
            "decision_index": len(rows),
            "pre_state": _state(state),
            "legal_action_tiles": [candidate.tile for candidate in kernel.actions(state)],
            "action_tile": action.tile,
            "action_public_class": component,
            "selection_score": list(score),
            "post_state": _state(successor),
            "changed_buffer_components": changed,
            "selected_count_before": state.buffer[component],
            "selected_count_after": successor.buffer[component],
            "pre_load": sum(state.buffer),
            "post_load": sum(successor.buffer),
            "capacity": kernel.capacity,
            "post_board_empty": successor.removed_mask == (1 << kernel.tile_count) - 1,
            "post_status": successor.status.value,
            "source_generation_witness_accessed": False,
        }
        rows.append(
            {
                **payload,
                "observation_id": content_id(base.FUTURE_DOMAINS["raw_observation"], payload),
            }
        )
        visits[state.buffer[component]] = visits.get(state.buffer[component], 0) + 1
        state = successor
    return rows, state.status.value


def _expected_v44_failure() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    closures = []
    for schedule in base.SOURCE_SCHEDULE:
        mode_rows: list[dict[str, Any]] = []
        for seed in schedule["ordered_seeds"]:
            episode_rows, terminal = _expected_v44_episode(seed, schedule["mode"])
            rows.extend(episode_rows)
            mode_rows.extend(episode_rows)
            closures.append(
                {
                    "mode": schedule["mode"],
                    "source_seed": seed,
                    "transition_label_count": len(episode_rows),
                    "terminal_status": terminal,
                    "mode_requirements_satisfied_after_episode": _mode_complete(
                        schedule["mode"], mode_rows
                    ),
                }
            )
            if _mode_complete(schedule["mode"], mode_rows):
                break
    facts = {
        "operated_component_join_observed": all(
            row["changed_buffer_components"] == [row["action_public_class"]] for row in rows
        ),
        "increment_difference_observed": any(
            row["selected_count_after"] == row["selected_count_before"] + 1 for row in rows
        ),
        "rewrite_difference_observed": any(
            row["selected_count_after"] < row["selected_count_before"] for row in rows
        ),
        "active_at_capacity_observed": any(
            row["post_load"] == row["capacity"] and row["post_status"] == "active"
            for row in rows
        ),
        "failure_one_above_capacity_observed": any(
            row["post_load"] == row["capacity"] + 1 and row["post_status"] == "failure"
            for row in rows
        ),
        "success_on_full_removal_observed": any(
            row["post_board_empty"] and row["post_status"] == "success" for row in rows
        ),
    }
    payload = {
        "schema": "acfqp.lmb_difference_grammar_failure.v44",
        "schema_version": base.SCHEMA_VERSION,
        "profile_key": "construction_k7_lmb_difference_grammar_source_failure_v44",
        "preregistration_id": base.PREREGISTRATION_ID,
        "raw_observations": rows,
        "source_episode_closures": closures,
        "coverage_facts": facts,
        "offline_source_transition_label_count": len(rows),
        "target_episode_execution_count": 0,
        "target_generation_witness_access_count": 0,
        "failure_code": "PREREGISTERED_SOURCE_SUCCESS_COVERAGE_NOT_OBSERVED",
        "failure_preserved_before_successor_preregistration": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "TYPED_PREREGISTERED_COVERAGE_FAILURE",
    }
    document = {
        **payload,
        "failure_id": content_id(base.FUTURE_DOMAINS["campaign"], payload),
    }
    raw = canonical_json_bytes(document)
    if (
        document["failure_id"] != pre.V44_FAILURE_ID
        or len(raw) != pre.V44_FAILURE_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != pre.V44_FAILURE_SHA256
    ):
        _fail("independently reconstructed V44 failure changed")
    return document


def _model_step(
    kernel: LMBKernel,
    state: LMBState,
    action: LMBAction,
    rewrite_cardinality: int,
) -> LMBState:
    removed = state.removed_mask | (1 << action.tile)
    component = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[component] = (counts[component] + 1) % rewrite_cardinality
    load = sum(counts)
    board_empty = removed == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity
        else LMBStatus.SUCCESS
        if board_empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed, tuple(counts), status)


def _plan(
    kernel: LMBKernel,
    state: LMBState,
    rewrite_cardinality: int,
) -> tuple[tuple[LMBAction, ...], int, int]:
    memo: dict[LMBState, tuple[LMBAction, ...] | None] = {}
    evaluations = 0
    peak = 0

    def solve(current: LMBState) -> tuple[LMBAction, ...] | None:
        nonlocal evaluations, peak
        if current.status is LMBStatus.SUCCESS:
            return ()
        if current.status is LMBStatus.FAILURE:
            return None
        if current in memo:
            return memo[current]
        candidates = []
        for action in kernel.actions(current):
            successor = _model_step(kernel, current, action, rewrite_cardinality)
            evaluations += 1
            rewrite = sum(successor.buffer) < sum(current.buffer)
            available = sum(
                1
                for tile in range(kernel.tile_count)
                if not successor.removed_mask & (1 << tile)
                and all(
                    successor.removed_mask & (1 << blocker)
                    for blocker in kernel.blockers[tile]
                )
            )
            candidates.append(
                ((-int(rewrite), sum(successor.buffer), -available, action.tile), action, successor)
            )
        for _rank, action, successor in sorted(candidates):
            suffix = solve(successor)
            if suffix is not None:
                memo[current] = (action, *suffix)
                peak = max(peak, len(memo))
                return memo[current]
        memo[current] = None
        peak = max(peak, len(memo))
        return None

    result = solve(state)
    if result is None:
        _fail("independent derived program found no successful continuation")
    return result, evaluations, peak


def _expected_confirmation(
    rewrite_cardinality: int,
) -> tuple[list[dict[str, Any]], int, int]:
    kernel, witness = generate_solvable_lmb(
        seed=pre.SOURCE_CONFIRMATION_SEED,
        **pre.SOURCE_SPEC,
    )
    del witness
    state = kernel.initial_distribution()[0][1]
    plan, evaluations, peak = _plan(kernel, state, rewrite_cardinality)
    rows = []
    for action in plan:
        predicted = _model_step(kernel, state, action, rewrite_cardinality)
        outcome = kernel.step(state, action)[0]
        successor = outcome.next_state
        if successor != predicted:
            _fail("independent source confirmation differs from derived program")
        component = kernel.tile_types[action.tile]
        changed = [
            index
            for index, (before, after) in enumerate(zip(state.buffer, successor.buffer))
            if before != after
        ]
        payload = {
            "schema": "acfqp.lmb_model_derived_source_observation.v44r1",
            "schema_version": pre.SCHEMA_VERSION,
            "preregistration_id": pre.PREREGISTRATION_ID,
            "inherited_v44_failure_id": pre.V44_FAILURE_ID,
            "source_seed": pre.SOURCE_CONFIRMATION_SEED,
            "decision_index": len(rows),
            "pre_state": _state(state),
            "legal_action_tiles": [candidate.tile for candidate in kernel.actions(state)],
            "action_tile": action.tile,
            "action_public_class": component,
            "source_plan_prefix": [
                candidate.tile
                for candidate in plan[len(rows) : len(rows) + pre.RECEDING_HORIZON]
            ],
            "post_state": _state(successor),
            "changed_buffer_components": changed,
            "selected_count_before": state.buffer[component],
            "selected_count_after": successor.buffer[component],
            "pre_load": sum(state.buffer),
            "post_load": sum(successor.buffer),
            "capacity": kernel.capacity,
            "post_board_empty": successor.removed_mask == (1 << kernel.tile_count) - 1,
            "post_status": successor.status.value,
            "source_planning_kernel_step": False,
            "source_generation_witness_accessed": False,
        }
        rows.append(
            {
                **payload,
                "observation_id": content_id(
                    pre.FUTURE_DOMAINS["source_observation"], payload
                ),
            }
        )
        state = successor
    if state.status is not LMBStatus.SUCCESS:
        _fail("independent source confirmation did not reach success")
    return rows, evaluations, peak


def _support_key(row: dict[str, Any]) -> tuple[int, int, bool]:
    return (
        row["selected_count_before"],
        row["capacity"] - row["pre_load"],
        row["pre_load"] == row["capacity"],
    )


def _expression_node_count(value: Any) -> int:
    if type(value) is list:
        return 1 + sum(_expression_node_count(item) for item in value)
    return 1


def _expected_program() -> tuple[dict[str, Any], set[tuple[int, int, bool]]]:
    failure = _expected_v44_failure()
    inherited_rows = failure["raw_observations"]
    wrap_equations = sorted(
        {
            (
                row["selected_count_before"],
                row["selected_count_after"],
                row["selected_count_before"] + 1 - row["selected_count_after"],
            )
            for row in inherited_rows
            if row["selected_count_after"] < row["selected_count_before"]
        }
    )
    cardinalities = {equation[2] for equation in wrap_equations}
    if len(cardinalities) != 1:
        _fail("independent raw differences do not derive one cardinality")
    rewrite_cardinality = next(iter(cardinalities))
    confirmation_rows, source_compute, source_peak = _expected_confirmation(
        rewrite_cardinality
    )
    rows = [*inherited_rows, *confirmation_rows]
    if not all(
        row["changed_buffer_components"] == [row["action_public_class"]]
        and row["post_state"]["removed_mask"]
        == row["pre_state"]["removed_mask"] | (1 << row["action_tile"])
        and row["selected_count_after"]
        == (row["selected_count_before"] + 1) % rewrite_cardinality
        for row in rows
    ):
        _fail("independent difference equations changed")
    for row in rows:
        expected_status = (
            "failure"
            if row["post_load"] > row["capacity"]
            else "success"
            if row["post_board_empty"]
            else "active"
        )
        if row["post_status"] != expected_status:
            _fail("independent terminal derivation changed")
    expressions = [
        ["operated_component", ["ACTION_PUBLIC_CLASS"]],
        [
            "next_selected_count",
            [
                "MODULO",
                ["ADD_ONE", ["VECTOR_AT", "PRE_BUFFER", "operated_component"]],
                rewrite_cardinality,
            ],
        ],
        [
            "post_buffer",
            ["VECTOR_UPDATE", "PRE_BUFFER", "operated_component", "next_selected_count"],
        ],
        ["post_removed_set", ["SET_INSERT", "PRE_REMOVED_SET", "ACTION_TILE"]],
        ["post_load", ["SUM_VECTOR", "post_buffer"]],
        ["failure", ["GREATER_THAN", "post_load", "INSTANCE_CAPACITY"]],
        ["board_empty", ["ALL_REGISTERED_TILES_REMOVED", "post_removed_set"]],
        [
            "post_status",
            [
                "IF_THEN_ELSE",
                "failure",
                "FAILURE",
                ["IF_THEN_ELSE", "board_empty", "SUCCESS", "ACTIVE"],
            ],
        ],
    ]
    grammar_events = 6 * len(rows) + sum(
        _expression_node_count(expression) for expression in expressions
    )
    supports = {_support_key(row) for row in rows}
    payload = {
        "schema": "acfqp.lmb_derived_transition_program.v44r1",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v44_failure_id": pre.V44_FAILURE_ID,
        "typed_expression_grammar": pre.TYPED_GRAMMAR,
        "inherited_raw_observations": inherited_rows,
        "fresh_source_confirmation_observations": confirmation_rows,
        "inherited_offline_source_transition_label_count": len(inherited_rows),
        "additional_source_confirmation_label_count": len(confirmation_rows),
        "total_offline_source_transition_label_count": len(rows),
        "operated_component_derivation": {
            "expression": ["ACTION_PUBLIC_CLASS"],
            "unique_difference_join_count": len(rows),
            "all_rows_satisfied": True,
        },
        "removed_set_derivation": {
            "expression": ["SET_INSERT", "PRE_REMOVED_SET", "ACTION_TILE"],
            "all_rows_satisfied": True,
        },
        "rewrite_cardinality_derivation": {
            "wrap_difference_equations": [list(row) for row in wrap_equations],
            "derived_numeric_literal": rewrite_cardinality,
            "numeric_candidate_grid_used": False,
            "all_rows_satisfy_modular_increment": True,
        },
        "capacity_boundary_derivation": {
            "expression": ["GREATER_THAN", "post_load", "INSTANCE_CAPACITY"],
            "active_at_capacity_observation_count": sum(
                row["post_load"] == row["capacity"] and row["post_status"] == "active"
                for row in rows
            ),
            "failure_one_above_capacity_observation_count": sum(
                row["post_load"] == row["capacity"] + 1
                and row["post_status"] == "failure"
                for row in rows
            ),
            "numeric_capacity_offset_grid_used": False,
        },
        "terminal_rule_derivation": {
            "failure_precedes_success": True,
            "success_on_full_removal_observation_count": sum(
                row["post_board_empty"] and row["post_status"] == "success"
                for row in rows
            ),
            "active_otherwise_observation_count": sum(
                row["post_status"] == "active" for row in rows
            ),
            "all_rows_satisfied": True,
        },
        "compiled_typed_expressions": expressions,
        "source_structural_support_keys": [list(row) for row in sorted(supports)],
        "source_program_planning_kernel_step_count": 0,
        "source_program_abstract_transition_evaluation_count": source_compute,
        "source_program_peak_dynamic_program_cache_entries": source_peak,
        "grammar_derivation_compute_event_count": grammar_events,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "predeclared_numeric_program_grid_present": False,
        "status": "ONE_EXACT_TYPED_PROGRAM_DERIVED_FROM_RAW_DIFFERENCES",
    }
    return (
        {**payload, "program_id": content_id(pre.FUTURE_DOMAINS["program"], payload)},
        supports,
    )


def _context(state: LMBState, action: LMBAction) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["distinction"],
        {"role": "EXACT_CONTEXT", "state": _state(state), "action": _action(action)},
    )


def _certificate(
    program_id: str,
    arm: str,
    seed: int,
    index: int,
    state: LMBState,
    action: LMBAction,
    support_key: list[Any],
    status: str,
    failed_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_derived_program_certificate.v44r1",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "program_id": program_id,
        "arm": arm,
        "episode_seed": seed,
        "decision_index": index,
        "state": _state(state),
        "action": _action(action),
        "support_key": support_key,
        "status": status,
        "failed_certificate_id": failed_id,
        "kernel_step_during_planning": False,
    }
    return {
        **payload,
        "certificate_id": content_id(pre.FUTURE_DOMAINS["distinction"], payload),
    }


def _expected_episode(
    seed: int,
    arm: str,
    program_id: str,
    rewrite_cardinality: int,
    source_supports: set[tuple[int, int, bool]],
) -> dict[str, Any]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.TARGET_SPEC)
    del witness
    state = kernel.initial_distribution()[0][1]
    structural_overlay: set[tuple[int, int, bool]] = set()
    context_overlay: set[str] = set()
    decisions = []
    labels = 0
    abstract_compute = 0
    certificate_compute = 0
    peak = 0
    while state.status is LMBStatus.ACTIVE:
        index = len(decisions)
        plan, evaluations, plan_peak = _plan(kernel, state, rewrite_cardinality)
        abstract_compute += evaluations
        peak = max(peak, plan_peak)
        action = plan[0]
        predicted = _model_step(kernel, state, action, rewrite_cardinality)
        structural_key = (
            state.buffer[kernel.tile_types[action.tile]],
            kernel.capacity - sum(state.buffer),
            sum(state.buffer) == kernel.capacity,
        )
        context_key = _context(state, action)
        support_key = list(structural_key) if arm == pre.ARMS[0] else [context_key]
        supported = (
            structural_key in source_supports or structural_key in structural_overlay
            if arm == pre.ARMS[0]
            else context_key in context_overlay
        )
        initial = _certificate(
            program_id,
            arm,
            seed,
            index,
            state,
            action,
            support_key,
            "CERTIFIED_MODEL_SUPPORT" if supported else "FAILED_MISSING_SUPPORT",
            None,
        )
        certificate_compute += 1
        distinction = None
        exact = None
        final = initial
        replanned = False
        if not supported:
            exact = kernel.step(state, action)[0]
            labels += 1
            distinction_payload = {
                "schema": "acfqp.lmb_derived_program_local_distinction.v44r1",
                "schema_version": pre.SCHEMA_VERSION,
                "preregistration_id": pre.PREREGISTRATION_ID,
                "program_id": program_id,
                "failed_certificate_id": initial["certificate_id"],
                "arm": arm,
                "episode_seed": seed,
                "decision_index": index,
                "state": _state(state),
                "action": _action(action),
                "support_key": support_key,
                "observed_successor": _state(exact.next_state),
                "observed_failure": exact.failure,
                "observed_terminal": exact.terminal,
                "acquired_after_failed_certificate": True,
            }
            distinction = {
                **distinction_payload,
                "distinction_id": content_id(
                    pre.FUTURE_DOMAINS["distinction"], distinction_payload
                ),
            }
            if arm == pre.ARMS[0]:
                structural_overlay.add(structural_key)
            else:
                context_overlay.add(context_key)
            repeated, repeated_evaluations, repeated_peak = _plan(
                kernel, state, rewrite_cardinality
            )
            abstract_compute += repeated_evaluations
            peak = max(peak, repeated_peak)
            if repeated[0] != action:
                _fail("independent local recovery changed action")
            replanned = True
            final = _certificate(
                program_id,
                arm,
                seed,
                index,
                state,
                action,
                support_key,
                "CERTIFIED_AFTER_LOCAL_DISTINCTION",
                initial["certificate_id"],
            )
            certificate_compute += 1
        outcome = exact or kernel.step(state, action)[0]
        if outcome.next_state != predicted:
            _fail("independent held-out execution differs from program")
        decisions.append(
            {
                "decision_index": index,
                "source_state": _state(state),
                "plan_prefix": [_action(candidate) for candidate in plan[: pre.RECEDING_HORIZON]],
                "selected_action": _action(action),
                "predicted_successor": _state(predicted),
                "initial_certificate": initial,
                "local_distinction": distinction,
                "replanned_after_local_distinction": replanned,
                "final_certificate": final,
                "executed_successor": _state(outcome.next_state),
                "model_matches_execution": True,
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.lmb_derived_program_episode.v44r1",
        "schema_version": pre.SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "program_id": program_id,
        "arm": arm,
        "episode_seed": seed,
        "instance_specification": pre.TARGET_SPEC,
        "decisions": decisions,
        "terminal_state": _state(state),
        "full_board_cleared": True,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "target_local_distinction_label_count": labels,
        "execution_environment_step_count": len(decisions),
        "abstract_transition_evaluation_count": abstract_compute,
        "certificate_evaluation_count": certificate_compute,
        "peak_dynamic_program_cache_entries": peak,
        "labels_steps_and_compute_separate": True,
    }
    return {**payload, "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload)}


def _verify_source_binding(binding: Any) -> None:
    facts = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        facts.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    expected = {
        "schema": "acfqp.lmb_difference_program_source_binding.v44r1",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v44_failure_id": pre.V44_FAILURE_ID,
        "source_facts": facts,
        "full_producer_source_closure_claimed": False,
        "producer_free_verification_required": True,
    }
    if binding != expected:
        _fail("V44r1 source binding changed")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBDifferenceProgramIndependentVerificationV44R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V44r1 verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V44r1 verification bytes changed")
        payload = {key: value for key, value in document.items() if key != "verification_id"}
        if (
            document.get("verification_id") != self.verification_id
            or content_id(pre.FUTURE_DOMAINS["verification"], payload) != self.verification_id
        ):
            _fail("V44r1 verification identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V44r1 verification is not an object")
        return value


def independently_verify_lmb_difference_program_campaign_v44r1(
    campaign_bytes: bytes,
    output_path: str | Path | None = None,
) -> LMBDifferenceProgramIndependentVerificationV44R1:
    if type(campaign_bytes) is not bytes:
        _fail("V44r1 campaign input must be exact bytes")
    campaign = loads_canonical_json(campaign_bytes)
    if type(campaign) is not dict or canonical_json_bytes(campaign) != campaign_bytes:
        _fail("V44r1 campaign is not canonical")
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    campaign_id = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    expected_keys = {
        "schema",
        "schema_version",
        "profile_key",
        "preregistration_id",
        "v41_campaign_id",
        "v41_verification_id",
        "v42_campaign_id",
        "v42_verification_id",
        "v43_campaign_id",
        "v43_verification_id",
        "v44_preregistration_id",
        "v44_failure_id",
        "source_binding",
        "derived_program",
        "episodes",
        "summary",
        "verified_scope_candidate",
        "open_ended_grammar_invention_claimed",
        "broad_iid_or_cross_domain_sample_efficiency_claimed",
        "total_operational_work_saving_claimed",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "counter_completeness_gate_status",
        "workload_economics_gate_status",
        "campaign_id",
    }
    if (
        set(campaign) != expected_keys
        or campaign["schema"] != "acfqp.lmb_difference_program_campaign.v44r1"
        or campaign["schema_version"] != pre.SCHEMA_VERSION
        or campaign["profile_key"] != "construction_k7_lmb_difference_program_campaign_v44r1"
        or campaign["preregistration_id"] != pre.PREREGISTRATION_ID
        or campaign["v41_campaign_id"] != pre.V41_CAMPAIGN_ID
        or campaign["v41_verification_id"] != pre.V41_VERIFICATION_ID
        or campaign["v42_campaign_id"] != pre.V42_CAMPAIGN_ID
        or campaign["v42_verification_id"] != pre.V42_VERIFICATION_ID
        or campaign["v43_campaign_id"] != pre.V43_CAMPAIGN_ID
        or campaign["v43_verification_id"] != pre.V43_VERIFICATION_ID
        or campaign["v44_preregistration_id"] != pre.V44_PREREGISTRATION_ID
        or campaign["v44_failure_id"] != pre.V44_FAILURE_ID
        or campaign["campaign_id"] != campaign_id
        or campaign["open_ended_grammar_invention_claimed"] is not False
        or campaign["broad_iid_or_cross_domain_sample_efficiency_claimed"] is not False
        or campaign["total_operational_work_saving_claimed"] is not False
        or campaign["official_execution_allowed"] is not False
        or campaign["official_scalar_cost"] is not None
        or campaign["official_N_break_even"] is not None
        or campaign["counter_completeness_gate_status"] != "NOT_RUN"
        or campaign["workload_economics_gate_status"] != "NOT_RUN"
    ):
        _fail("V44r1 campaign schema, predecessor, identity, or claims changed")
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        campaign_id != EXPECTED_CAMPAIGN_ID
        or len(campaign_bytes) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_bytes).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("V44r1 campaign differs from frozen evidence")
    _verify_source_binding(campaign["source_binding"])
    program, supports = _expected_program()
    if campaign["derived_program"] != program:
        _fail("V44r1 raw-difference program replay changed")
    rewrite_cardinality = program["rewrite_cardinality_derivation"]["derived_numeric_literal"]
    expected_episodes = [
        _expected_episode(seed, arm, program["program_id"], rewrite_cardinality, supports)
        for arm in pre.ARMS
        for seed in pre.HELDOUT_SEEDS
    ]
    if campaign["episodes"] != expected_episodes:
        _fail("V44r1 held-out episode replay changed")
    structural = expected_episodes[: len(pre.HELDOUT_SEEDS)]
    control = expected_episodes[len(pre.HELDOUT_SEEDS) :]
    structural_labels = sum(row["target_local_distinction_label_count"] for row in structural)
    control_labels = sum(row["target_local_distinction_label_count"] for row in control)
    expected_summary = {
        "inherited_offline_source_transition_label_count": program[
            "inherited_offline_source_transition_label_count"
        ],
        "additional_source_confirmation_label_count": program[
            "additional_source_confirmation_label_count"
        ],
        "total_offline_source_transition_label_count": program[
            "total_offline_source_transition_label_count"
        ],
        "structural_meta_prior_target_label_count": structural_labels,
        "strict_no_prior_target_label_count": control_labels,
        "target_label_fraction": Fraction(structural_labels, control_labels),
        "heldout_episode_count_per_arm": len(pre.HELDOUT_SEEDS),
        "execution_environment_step_count_per_arm": sum(
            row["execution_environment_step_count"] for row in structural
        ),
        "structural_abstract_compute_events": sum(
            row["abstract_transition_evaluation_count"] + row["certificate_evaluation_count"]
            for row in structural
        ),
        "control_abstract_compute_events": sum(
            row["abstract_transition_evaluation_count"] + row["certificate_evaluation_count"]
            for row in control
        ),
        "source_abstract_compute_events": program[
            "source_program_abstract_transition_evaluation_count"
        ],
        "grammar_derivation_compute_events": program[
            "grammar_derivation_compute_event_count"
        ],
        "all_episodes_completed": True,
        "all_local_labels_follow_failed_certificates": True,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "planning_kernel_step_count": 0,
        "labels_steps_and_compute_separate": True,
    }
    if campaign["summary"] != expected_summary:
        _fail("V44r1 campaign summary changed")
    verification_payload = {
        "schema": "acfqp.lmb_difference_program_verification.v44r1",
        "schema_version": pre.SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v44_failure_id": pre.V44_FAILURE_ID,
        "campaign_id": campaign_id,
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "program_id": program["program_id"],
        "rewrite_cardinality_derived_from_raw_differences": rewrite_cardinality,
        "numeric_program_grid_present": False,
        "inherited_offline_source_transition_label_count": 42,
        "additional_source_confirmation_label_count": 15,
        "total_offline_source_transition_label_count": 57,
        "structural_meta_prior_target_label_count": structural_labels,
        "strict_no_prior_target_label_count": control_labels,
        "target_label_fraction": Fraction(structural_labels, control_labels),
        "source_tile_count": pre.SOURCE_SPEC["tile_count"],
        "source_type_count": pre.SOURCE_SPEC["type_count"],
        "source_capacity": pre.SOURCE_SPEC["capacity"],
        "source_max_layers": pre.SOURCE_SPEC["max_layers"],
        "target_tile_count": pre.TARGET_SPEC["tile_count"],
        "target_type_count": pre.TARGET_SPEC["type_count"],
        "target_capacity": pre.TARGET_SPEC["capacity"],
        "target_max_layers": pre.TARGET_SPEC["max_layers"],
        "heldout_episode_count_per_arm": len(pre.HELDOUT_SEEDS),
        "execution_environment_step_count_per_arm": expected_summary[
            "execution_environment_step_count_per_arm"
        ],
        "source_abstract_compute_events": expected_summary["source_abstract_compute_events"],
        "grammar_derivation_compute_events": expected_summary[
            "grammar_derivation_compute_events"
        ],
        "structural_abstract_compute_events": expected_summary[
            "structural_abstract_compute_events"
        ],
        "control_abstract_compute_events": expected_summary[
            "control_abstract_compute_events"
        ],
        "replayed_source_transition_count": 57,
        "replayed_target_execution_transition_count": sum(
            len(episode["decisions"]) for episode in expected_episodes
        ),
        "replayed_certificate_count": sum(
            len(episode["decisions"])
            + sum(decision["local_distinction"] is not None for decision in episode["decisions"])
            for episode in expected_episodes
        ),
        "all_episodes_cold_replayed_to_success": True,
        "all_local_labels_follow_failed_certificates": True,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "planning_kernel_step_count": 0,
        "labels_steps_and_compute_separate": True,
        "verification_imports_campaign_producer": False,
        "verified_claim_scope": (
            "REGISTERED_RAW_DIFFERENCE_LMB_CROSS_CAPACITY_WORKLOAD_V44R1"
        ),
        "open_ended_grammar_invention_claimed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "PRODUCER_FREE_RAW_DIFFERENCE_PROGRAM_VERIFIED",
    }
    verification = {
        **verification_payload,
        "verification_id": content_id(pre.FUTURE_DOMAINS["verification"], verification_payload),
    }
    raw = canonical_json_bytes(verification)
    identity = verification["verification_id"]
    if EXPECTED_VERIFICATION_ID != "0" * 64 and (
        identity != EXPECTED_VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V44r1 independent verification changed")
    if output_path is not None:
        Path(output_path).write_bytes(raw)
    return LMBDifferenceProgramIndependentVerificationV44R1(_ISSUER, raw, identity)


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "LMBDifferenceProgramIndependentVerificationV44R1",
    "independently_verify_lmb_difference_program_campaign_v44r1",
)
