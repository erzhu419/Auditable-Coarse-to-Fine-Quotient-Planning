"""Producer-free replay of the V42 Layered Matching Buffer campaign.

This verifier deliberately does not import the campaign producer.  It rebuilds
the held-out kernels from the preregistered seeds, reimplements the generic
rewrite/capacity law and deterministic feasibility search, replays every
certificate and transition, and recomputes all content identities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_reusable_world_model_preregistration_v42 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_lmb_reusable_world_model_independent_verification_v42"
EXPECTED_VERIFICATION_ID = (
    "af44dabf2f2f7b05767343c2d8306165cfe828ff8180efe7d409e0baa3315da0"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_914
EXPECTED_CANONICAL_SHA256 = (
    "610d8e767ff0134452d6fc9f7c236eb908ef52d0a245d944d7ee4a089d2b0c8e"
)
EXPECTED_CAMPAIGN_ID = (
    "c8adada792b7dacfce816bf1916457329643b61e8915f285472708c6c6bd359b"
)
EXPECTED_CAMPAIGN_BYTE_COUNT = 405_486
EXPECTED_CAMPAIGN_SHA256 = (
    "4f7cafbb0d1dff989ff6f9e824981e908f5a234ffe95a1f1ea162d3ede293161"
)

SOURCE_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_lmb_reusable_world_model_preregistration_v42.py",
    "src/acfqp/domains/matching_buffer.py",
)


class ConstructionK7LMBReusableWorldModelIndependentVerifierV42Error(ValueError):
    """The campaign bytes, proposal, plan, certificate, or accounting changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBReusableWorldModelIndependentVerifierV42Error(message)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} schema changed")
    return value


def _state_document(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


def _action_document(action: LMBAction) -> dict[str, int]:
    return {"tile": action.tile}


def _predict(kernel: LMBKernel, state: LMBState, action: LMBAction) -> LMBState:
    if action not in kernel.actions(state):
        _fail("recorded operation is ineligible")
    removed_mask = state.removed_mask | (1 << action.tile)
    operation_class = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[operation_class] += 1
    if counts[operation_class] == 3:
        counts[operation_class] = 0
    load = sum(counts)
    board_empty = removed_mask == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity
        else LMBStatus.SUCCESS
        if board_empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed_mask, tuple(counts), status)


def _candidate_predict(
    kernel: LMBKernel,
    state: LMBState,
    action: LMBAction,
    candidate: tuple[int, int],
) -> LMBState | None:
    removed_mask = state.removed_mask | (1 << action.tile)
    operation_class = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[operation_class] = (
        0 if counts[operation_class] == candidate[0] else counts[operation_class] + 1
    )
    if counts[operation_class] >= 3:
        return None
    load = sum(counts)
    board_empty = removed_mask == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity + candidate[1]
        else LMBStatus.SUCCESS
        if board_empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed_mask, tuple(counts), status)


def _support_key(kernel: LMBKernel, state: LMBState, action: LMBAction) -> tuple[int, int, bool]:
    return (
        state.buffer[kernel.tile_types[action.tile]],
        sum(state.buffer),
        sum(state.buffer) == kernel.capacity,
    )


def _context_key(state: LMBState, action: LMBAction) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["local_ground_distinction"],
        {
            "role": "STRICT_NO_PRIOR_EXACT_CONTEXT_KEY",
            "state": _state_document(state),
            "action": _action_document(action),
        },
    )


def _plan(kernel: LMBKernel, state: LMBState) -> tuple[tuple[LMBAction, ...], int, int]:
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
            successor = _predict(kernel, current, action)
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
        _fail("independent model replay found no successful path")
    return result, evaluations, peak


def _certificate_payload(
    *,
    proposal_id: str,
    arm: str,
    seed: int,
    decision_index: int,
    state: LMBState,
    action: LMBAction,
    support: list[Any],
    status: str,
    failed_id: str | None,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.lmb_receding_model_certificate.v42",
        "schema_version": SCHEMA_VERSION,
        "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
        "lmb_reusable_primitive_proposal_id": proposal_id,
        "acquisition_arm": arm,
        "episode_seed": seed,
        "decision_index": decision_index,
        "state": _state_document(state),
        "action": _action_document(action),
        "support_key": support,
        "planning_horizon": pre.RECEDING_HORIZON,
        "kernel_step_during_planning": False,
        "status": status,
        "failed_certificate_id": failed_id,
    }


def _verify_source_binding(value: Any) -> None:
    row = _exact(
        value,
        {
            "schema",
            "schema_version",
            "lmb_reusable_world_model_preregistration_id",
            "v41_campaign_id",
            "v41_verification_id",
            "bound_source_facts",
            "producer_full_source_closure_claimed",
            "independent_verifier_required",
        },
        "source binding",
    )
    if (
        row["schema"] != "acfqp.lmb_reusable_world_model_source_binding.v42"
        or row["schema_version"] != SCHEMA_VERSION
        or row["lmb_reusable_world_model_preregistration_id"] != pre.PREREGISTRATION_ID
        or row["v41_campaign_id"] != pre.V41_CAMPAIGN_ID
        or row["v41_verification_id"] != pre.V41_VERIFICATION_ID
        or row["producer_full_source_closure_claimed"] is not False
        or row["independent_verifier_required"] is not True
        or type(row["bound_source_facts"]) is not list
        or len(row["bound_source_facts"]) != len(EXPECTED_BOUND_SOURCE_PATHS)
    ):
        _fail("source binding claim changed")
    expected = []
    for relative in EXPECTED_BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        expected.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if row["bound_source_facts"] != expected:
        _fail("bound source bytes changed")


def _verify_proposal(value: Any) -> tuple[str, set[tuple[int, int, bool]], int]:
    row = _exact(
        value,
        {
            "schema",
            "schema_version",
            "lmb_reusable_world_model_preregistration_id",
            "source_relations",
            "meta_operators",
            "selected_expressions",
            "candidate_program_trace",
            "source_observation_rows",
            "source_support_keys",
            "offline_source_transition_label_count",
            "source_generation_witness_used_only_to_schedule_offline_observations",
            "heldout_generation_witness_accessed",
            "query_value_reward_or_target_policy_input_present",
            "all_source_rows_match_proposed_transition_law",
            "proposal_acceptance_authority",
            "lmb_reusable_primitive_proposal_id",
        },
        "primitive proposal",
    )
    if (
        row["schema"] != "acfqp.lmb_reusable_primitive_proposal.v42"
        or row["schema_version"] != SCHEMA_VERSION
        or row["lmb_reusable_world_model_preregistration_id"] != pre.PREREGISTRATION_ID
        or row["source_relations"] != list(pre.GENERIC_SOURCE_RELATIONS)
        or row["meta_operators"] != list(pre.GENERIC_META_OPERATORS)
        or row["source_generation_witness_used_only_to_schedule_offline_observations"] is not True
        or row["heldout_generation_witness_accessed"] is not False
        or row["query_value_reward_or_target_policy_input_present"] is not False
        or row["all_source_rows_match_proposed_transition_law"] is not True
        or row["proposal_acceptance_authority"] != "EXACT_SOURCE_OBSERVATION_CONSISTENCY_V1"
    ):
        _fail("primitive proposal semantics changed")

    expected_rows: list[dict[str, Any]] = []
    alternate_pool: list[tuple[int, int, LMBKernel, LMBState, LMBAction]] = []
    supports: set[tuple[int, int, bool]] = set()
    for seed in pre.SOURCE_OBSERVATION_SEEDS:
        kernel, witness = generate_solvable_lmb(
            tile_count=pre.TILE_COUNT,
            type_count=pre.TYPE_COUNT,
            capacity=pre.BUFFER_CAPACITY,
            max_layers=pre.MAX_LAYERS,
            seed=seed,
        )
        state = kernel.initial_distribution()[0][1]
        for index, tile in enumerate(witness.target_sequence):
            action = LMBAction(tile)
            alternate_pool.extend(
                (seed, index, kernel, state, candidate)
                for candidate in kernel.actions(state)
                if candidate != action
            )
            predicted = _predict(kernel, state, action)
            outcome = kernel.step(state, action)[0]
            if outcome.next_state != predicted:
                _fail("independent source observation differs from proposed law")
            key = _support_key(kernel, state, action)
            supports.add(key)
            expected_rows.append(
                {
                    "source_seed": seed,
                    "decision_index": index,
                    "observation_phase": "WITNESS_TRAJECTORY",
                    "state": _state_document(state),
                    "action": _action_document(action),
                    "selected_class_count": key[0],
                    "resource_load": key[1],
                    "at_capacity": key[2],
                    "observed_successor": _state_document(outcome.next_state),
                    "observed_failure": outcome.failure,
                    "observed_terminal": outcome.terminal,
                }
            )
            state = outcome.next_state

    candidates = tuple(
        (rewrite_trigger_count, capacity_failure_offset)
        for rewrite_trigger_count in (0, 1, 2)
        for capacity_failure_offset in (-1, 0, 1)
    )

    def consistent(candidate: tuple[int, int], observations: list[dict[str, Any]]) -> bool:
        for observation in observations:
            kernel, _witness = generate_solvable_lmb(
                tile_count=pre.TILE_COUNT,
                type_count=pre.TYPE_COUNT,
                capacity=pre.BUFFER_CAPACITY,
                max_layers=pre.MAX_LAYERS,
                seed=observation["source_seed"],
            )
            state_record = observation["state"]
            state = LMBState(
                state_record["removed_mask"],
                tuple(state_record["buffer_counts"]),
                LMBStatus(state_record["status"]),
            )
            predicted = _candidate_predict(
                kernel,
                state,
                LMBAction(observation["action"]["tile"]),
                candidate,
            )
            if (None if predicted is None else _state_document(predicted)) != observation[
                "observed_successor"
            ]:
                return False
        return True

    surviving = [candidate for candidate in candidates if consistent(candidate, expected_rows)]
    after_witness = list(surviving)
    adaptive_trace = []
    while len(surviving) > 1:
        best = None
        for candidate_row in alternate_pool:
            seed, decision_index, kernel, state, action = candidate_row
            groups: dict[str, int] = {}
            for hypothesis in surviving:
                predicted = _candidate_predict(kernel, state, action, hypothesis)
                key = repr(None if predicted is None else _state_document(predicted))
                groups[key] = groups.get(key, 0) + 1
            if len(groups) < 2:
                continue
            score = (
                len(groups),
                -max(groups.values()),
                -seed,
                -decision_index,
                -action.tile,
            )
            if best is None or score > best[0]:
                best = (score, candidate_row)
        if best is None:
            _fail("independent candidate selector cannot identify one program")
        seed, decision_index, kernel, state, action = best[1]
        outcome = kernel.step(state, action)[0]
        key = _support_key(kernel, state, action)
        supports.add(key)
        observation = {
            "source_seed": seed,
            "decision_index": decision_index,
            "observation_phase": "ADAPTIVE_CANDIDATE_DISAGREEMENT",
            "state": _state_document(state),
            "action": _action_document(action),
            "selected_class_count": key[0],
            "resource_load": key[1],
            "at_capacity": key[2],
            "observed_successor": _state_document(outcome.next_state),
            "observed_failure": outcome.failure,
            "observed_terminal": outcome.terminal,
        }
        expected_rows.append(observation)
        surviving = [candidate for candidate in surviving if consistent(candidate, [observation])]
        adaptive_trace.append(
            {
                "query_ordinal": len(adaptive_trace),
                "source_seed": seed,
                "decision_index": decision_index,
                "action": _action_document(action),
                "surviving_candidate_count_after_observation": len(surviving),
            }
        )
        alternate_pool.remove(best[1])
    if surviving != [(2, 0)]:
        _fail("independent candidate selector chose a different program")

    expected_expressions = [
        {"compatibility_name": "resource_load", "expression": ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"]},
        {
            "compatibility_name": "capacity_slack",
            "expression": ["SUBTRACT", "CAPACITY_LIMIT", ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"]],
        },
        {
            "compatibility_name": "selected_class_count",
            "expression": ["SELECT_CLASS_COUNT", "RESOURCE_COUNT_VECTOR", "OPERATION_CLASS"],
        },
        {
            "compatibility_name": "rewrite_on_next",
            "expression": [
                "EQUALS",
                ["SELECT_CLASS_COUNT", "RESOURCE_COUNT_VECTOR", "OPERATION_CLASS"],
                surviving[0][0],
            ],
        },
        {
            "compatibility_name": "post_operation_load",
            "expression": [
                "SUBTRACT_IF_REWRITE_ELSE_ADD_ONE",
                ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"],
                "rewrite_on_next",
            ],
        },
        {
            "compatibility_name": "future_repair_supply",
            "expression": [
                "COUNT_AVAILABLE_BY_CLASS",
                "AVAILABLE_OPERATION_SET",
                "OPERATION_CLASS",
            ],
        },
    ]
    expected_candidate_trace = {
        "candidate_grammar": {
            "rewrite_trigger_counts": [0, 1, 2],
            "capacity_failure_offsets": [-1, 0, 1],
        },
        "initial_candidates": [list(candidate) for candidate in candidates],
        "surviving_after_witness_observations": [list(candidate) for candidate in after_witness],
        "adaptive_disagreement_queries": adaptive_trace,
        "selected_candidate": list(surviving[0]),
        "selection_rule": "MAX_PARTITION_THEN_BALANCE_THEN_SEED_DECISION_TILE_V1",
    }
    if (
        row["selected_expressions"] != expected_expressions
        or row["candidate_program_trace"] != expected_candidate_trace
        or row["source_observation_rows"] != expected_rows
        or row["source_support_keys"] != [list(key) for key in sorted(supports)]
        or row["offline_source_transition_label_count"] != len(expected_rows)
    ):
        _fail("source observation evidence changed")
    payload = {key: item for key, item in row.items() if key != "lmb_reusable_primitive_proposal_id"}
    proposal_id = content_id(pre.FUTURE_DOMAINS["primitive_proposal"], payload)
    if row["lmb_reusable_primitive_proposal_id"] != proposal_id:
        _fail("primitive proposal identity changed")
    return proposal_id, supports, len(expected_rows)


def _verify_episode(
    value: Any,
    *,
    expected_arm: str,
    expected_seed: int,
    proposal_id: str,
    source_supports: set[tuple[int, int, bool]],
) -> dict[str, int | str | bool]:
    episode_keys = {
        "schema",
        "schema_version",
        "lmb_reusable_world_model_preregistration_id",
        "lmb_reusable_primitive_proposal_id",
        "acquisition_arm",
        "episode_seed",
        "instance_specification",
        "initial_state",
        "decisions",
        "terminal_state",
        "terminal_status",
        "full_board_cleared",
        "target_generation_witness_access_count",
        "target_local_distinction_label_count",
        "execution_environment_step_count",
        "abstract_transition_evaluation_count",
        "certificate_evaluation_count",
        "peak_dynamic_programming_cache_entries",
        "sample_labels_and_planning_compute_separate",
        "lmb_receding_episode_id",
    }
    row = _exact(value, episode_keys, "episode")
    if (
        row["schema"] != "acfqp.lmb_receding_episode.v42"
        or row["schema_version"] != SCHEMA_VERSION
        or row["lmb_reusable_world_model_preregistration_id"] != pre.PREREGISTRATION_ID
        or row["lmb_reusable_primitive_proposal_id"] != proposal_id
        or row["acquisition_arm"] != expected_arm
        or row["episode_seed"] != expected_seed
        or row["instance_specification"]
        != {
            "tile_count": pre.TILE_COUNT,
            "type_count": pre.TYPE_COUNT,
            "buffer_capacity": pre.BUFFER_CAPACITY,
            "max_layers": pre.MAX_LAYERS,
        }
        or row["target_generation_witness_access_count"] != 0
        or row["sample_labels_and_planning_compute_separate"] is not True
        or type(row["decisions"]) is not list
    ):
        _fail("episode binding changed")
    kernel, _witness = generate_solvable_lmb(
        tile_count=pre.TILE_COUNT,
        type_count=pre.TYPE_COUNT,
        capacity=pre.BUFFER_CAPACITY,
        max_layers=pre.MAX_LAYERS,
        seed=expected_seed,
    )
    del _witness
    state = kernel.initial_distribution()[0][1]
    if row["initial_state"] != _state_document(state):
        _fail("episode initial state changed")
    generic_overlay: set[tuple[int, int, bool]] = set()
    context_overlay: set[str] = set()
    labels = 0
    abstract_evaluations = 0
    certificate_evaluations = 0
    peak = 0
    for decision_index, decision in enumerate(row["decisions"]):
        decision = _exact(
            decision,
            {
                "decision_index",
                "source_state",
                "receding_plan_prefix",
                "selected_action",
                "predicted_successor",
                "initial_certificate",
                "local_ground_distinction",
                "replanned_after_local_distinction",
                "final_certificate",
                "executed_successor",
                "model_matches_execution",
                "kernel_step_during_planning",
            },
            "decision",
        )
        if decision["decision_index"] != decision_index or decision["source_state"] != _state_document(state):
            _fail("decision ordering/source state changed")
        plan, evaluations, plan_peak = _plan(kernel, state)
        abstract_evaluations += evaluations
        peak = max(peak, plan_peak)
        expected_prefix = [_action_document(action) for action in plan[: pre.RECEDING_HORIZON]]
        action = plan[0]
        predicted = _predict(kernel, state, action)
        if (
            decision["receding_plan_prefix"] != expected_prefix
            or decision["selected_action"] != _action_document(action)
            or decision["predicted_successor"] != _state_document(predicted)
            or decision["kernel_step_during_planning"] is not False
            or decision["model_matches_execution"] is not True
        ):
            _fail("independent receding plan changed")
        generic_key = _support_key(kernel, state, action)
        exact_key = _context_key(state, action)
        support = list(generic_key) if expected_arm == "STRUCTURAL_META_PRIOR" else [exact_key]
        supported = (
            generic_key in source_supports or generic_key in generic_overlay
            if expected_arm == "STRUCTURAL_META_PRIOR"
            else exact_key in context_overlay
        )
        initial_status = "CERTIFIED_MODEL_SUPPORT" if supported else "FAILED_MISSING_SUPPORT"
        expected_initial_payload = _certificate_payload(
            proposal_id=proposal_id,
            arm=expected_arm,
            seed=expected_seed,
            decision_index=decision_index,
            state=state,
            action=action,
            support=support,
            status=initial_status,
            failed_id=None,
        )
        expected_initial = {
            **expected_initial_payload,
            "certificate_id": content_id(
                pre.FUTURE_DOMAINS["local_ground_distinction"], expected_initial_payload
            ),
        }
        if decision["initial_certificate"] != expected_initial:
            _fail("initial certificate changed")
        certificate_evaluations += 1
        outcome = kernel.step(state, action)[0]
        if not supported:
            distinction_payload = {
                "schema": "acfqp.lmb_local_ground_distinction.v42",
                "schema_version": SCHEMA_VERSION,
                "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
                "lmb_reusable_primitive_proposal_id": proposal_id,
                "failed_certificate_id": expected_initial["certificate_id"],
                "acquisition_arm": expected_arm,
                "episode_seed": expected_seed,
                "decision_index": decision_index,
                "state": _state_document(state),
                "action": _action_document(action),
                "support_key": support,
                "observed_successor": _state_document(outcome.next_state),
                "observed_failure": outcome.failure,
                "observed_terminal": outcome.terminal,
                "acquired_after_failed_certificate": True,
                "acquisition_scope": "EPISODE_IMMUTABLE_OVERLAY",
            }
            expected_distinction = {
                **distinction_payload,
                "local_ground_distinction_id": content_id(
                    pre.FUTURE_DOMAINS["local_ground_distinction"], distinction_payload
                ),
            }
            if decision["local_ground_distinction"] != expected_distinction:
                _fail("local ground distinction changed")
            labels += 1
            if expected_arm == "STRUCTURAL_META_PRIOR":
                generic_overlay.add(generic_key)
            else:
                context_overlay.add(exact_key)
            replanned, evaluations, replan_peak = _plan(kernel, state)
            abstract_evaluations += evaluations
            peak = max(peak, replan_peak)
            if not replanned or replanned[0] != action:
                _fail("independent replan changed after local distinction")
            final_payload = _certificate_payload(
                proposal_id=proposal_id,
                arm=expected_arm,
                seed=expected_seed,
                decision_index=decision_index,
                state=state,
                action=action,
                support=support,
                status="CERTIFIED_AFTER_LOCAL_DISTINCTION",
                failed_id=expected_initial["certificate_id"],
            )
            expected_final = {
                **final_payload,
                "certificate_id": content_id(
                    pre.FUTURE_DOMAINS["local_ground_distinction"], final_payload
                ),
            }
            if (
                decision["final_certificate"] != expected_final
                or decision["replanned_after_local_distinction"] is not True
            ):
                _fail("post-distinction certificate changed")
            certificate_evaluations += 1
        else:
            if (
                decision["local_ground_distinction"] is not None
                or decision["final_certificate"] != expected_initial
                or decision["replanned_after_local_distinction"] is not False
            ):
                _fail("certified decision illegally acquired a target row")
        if outcome.next_state != predicted or decision["executed_successor"] != _state_document(outcome.next_state):
            _fail("executed transition changed")
        state = outcome.next_state
    if (
        state.status is not LMBStatus.SUCCESS
        or len(row["decisions"]) != pre.TILE_COUNT
        or row["terminal_state"] != _state_document(state)
        or row["terminal_status"] != LMBStatus.SUCCESS.value
        or row["full_board_cleared"] is not True
        or row["target_local_distinction_label_count"] != labels
        or row["execution_environment_step_count"] != pre.TILE_COUNT
        or row["abstract_transition_evaluation_count"] != abstract_evaluations
        or row["certificate_evaluation_count"] != certificate_evaluations
        or row["peak_dynamic_programming_cache_entries"] != peak
    ):
        _fail("episode closure/accounting changed")
    payload = {key: item for key, item in row.items() if key != "lmb_receding_episode_id"}
    if row["lmb_receding_episode_id"] != content_id(pre.FUTURE_DOMAINS["episode"], payload):
        _fail("episode identity changed")
    return {
        "labels": labels,
        "steps": pre.TILE_COUNT,
        "compute": abstract_evaluations + certificate_evaluations,
        "terminal": row["terminal_status"],
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBReusableWorldModelIndependentVerificationV42:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("independent verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("independent verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_reusable_world_model_verification_id"
        }
        if (
            document.get("lmb_reusable_world_model_verification_id") != self.verification_id
            or content_id(pre.FUTURE_DOMAINS["verification"], payload) != self.verification_id
        ):
            _fail("independent verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError("verification is not an object")
        return document


def independently_verify_lmb_reusable_world_model_campaign_v42(
    campaign_bytes: bytes,
    output_path: str | Path | None = None,
) -> LMBReusableWorldModelIndependentVerificationV42:
    if type(campaign_bytes) is not bytes:
        _fail("campaign input must be exact bytes")
    campaign = loads_canonical_json(campaign_bytes)
    top_keys = {
        "schema",
        "schema_version",
        "profile_key",
        "lmb_reusable_world_model_preregistration_id",
        "v41_campaign_id",
        "v41_verification_id",
        "source_binding",
        "primitive_proposal",
        "episodes",
        "matched_summary",
        "cross_domain_general_sample_efficiency_claimed",
        "broad_iid_claimed",
        "total_operational_work_saving_claimed",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "counter_completeness_gate_status",
        "workload_economics_gate_status",
        "lmb_reusable_world_model_campaign_id",
    }
    campaign = _exact(campaign, top_keys, "campaign")
    payload = {key: value for key, value in campaign.items() if key != "lmb_reusable_world_model_campaign_id"}
    campaign_id = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    if (
        canonical_json_bytes(campaign) != campaign_bytes
        or campaign["schema"] != "acfqp.lmb_reusable_world_model_campaign.v42"
        or campaign["schema_version"] != SCHEMA_VERSION
        or campaign["profile_key"] != "construction_k7_lmb_reusable_world_model_campaign_v42"
        or campaign["lmb_reusable_world_model_preregistration_id"] != pre.PREREGISTRATION_ID
        or campaign["v41_campaign_id"] != pre.V41_CAMPAIGN_ID
        or campaign["v41_verification_id"] != pre.V41_VERIFICATION_ID
        or campaign["lmb_reusable_world_model_campaign_id"] != campaign_id
        or campaign["cross_domain_general_sample_efficiency_claimed"] is not False
        or campaign["broad_iid_claimed"] is not False
        or campaign["total_operational_work_saving_claimed"] is not False
        or campaign["official_execution_allowed"] is not False
        or campaign["official_scalar_cost"] is not None
        or campaign["official_N_break_even"] is not None
        or campaign["counter_completeness_gate_status"] != "NOT_RUN"
        or campaign["workload_economics_gate_status"] != "NOT_RUN"
    ):
        _fail("campaign identity or claim locks changed")
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        campaign_id != EXPECTED_CAMPAIGN_ID
        or len(campaign_bytes) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_bytes).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("campaign differs from frozen evidence")
    _verify_source_binding(campaign["source_binding"])
    proposal_id, supports, offline_labels = _verify_proposal(campaign["primitive_proposal"])
    if type(campaign["episodes"]) is not list or len(campaign["episodes"]) != 12:
        _fail("campaign episode inventory changed")
    outcomes = []
    for index, (arm, seed) in enumerate(
        (arm, seed) for arm in pre.ACQUISITION_ARMS for seed in pre.HELDOUT_EPISODE_SEEDS
    ):
        outcomes.append(
            _verify_episode(
                campaign["episodes"][index],
                expected_arm=arm,
                expected_seed=seed,
                proposal_id=proposal_id,
                source_supports=supports,
            )
        )
    structural = outcomes[: len(pre.HELDOUT_EPISODE_SEEDS)]
    no_prior = outcomes[len(pre.HELDOUT_EPISODE_SEEDS) :]
    structural_labels = sum(int(row["labels"]) for row in structural)
    no_prior_labels = sum(int(row["labels"]) for row in no_prior)
    ratio = Fraction(structural_labels, no_prior_labels)
    expected_summary = {
        "heldout_episode_count_per_arm": len(pre.HELDOUT_EPISODE_SEEDS),
        "structural_meta_prior_target_label_count": structural_labels,
        "strict_no_prior_target_label_count": no_prior_labels,
        "target_label_fraction": ratio,
        "structural_meta_prior_execution_step_count": sum(int(row["steps"]) for row in structural),
        "strict_no_prior_execution_step_count": sum(int(row["steps"]) for row in no_prior),
        "structural_meta_prior_abstract_compute_events": sum(int(row["compute"]) for row in structural),
        "strict_no_prior_abstract_compute_events": sum(int(row["compute"]) for row in no_prior),
        "all_episodes_completed": True,
        "matched_terminal_statuses": [row["terminal"] for row in structural]
        == [row["terminal"] for row in no_prior],
        "every_local_label_has_failed_certificate": True,
        "planning_kernel_step_count": 0,
        "labels_and_compute_axes_not_collapsed": True,
    }
    if campaign["matched_summary"] != expected_summary or not 0 < structural_labels < no_prior_labels:
        _fail("matched acquisition summary changed")
    verification_payload = {
        "schema": "acfqp.lmb_reusable_world_model_verification.v42",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
        "lmb_reusable_world_model_campaign_id": campaign_id,
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "lmb_reusable_primitive_proposal_id": proposal_id,
        "offline_source_transition_label_count": offline_labels,
        "heldout_episode_count_per_arm": len(pre.HELDOUT_EPISODE_SEEDS),
        "structural_meta_prior_target_label_count": structural_labels,
        "strict_no_prior_target_label_count": no_prior_labels,
        "target_label_fraction": {"numerator": ratio.numerator, "denominator": ratio.denominator},
        "execution_environment_step_count_per_arm": sum(int(row["steps"]) for row in structural),
        "structural_meta_prior_abstract_compute_events": sum(int(row["compute"]) for row in structural),
        "strict_no_prior_abstract_compute_events": sum(int(row["compute"]) for row in no_prior),
        "replayed_certificate_count": sum(
            len(episode["decisions"])
            + sum(
                decision["local_ground_distinction"] is not None
                for decision in episode["decisions"]
            )
            for episode in campaign["episodes"]
        ),
        "replayed_execution_transition_count": sum(len(episode["decisions"]) for episode in campaign["episodes"]),
        "all_episodes_cold_replayed_to_success": True,
        "all_local_labels_bound_to_prior_failed_certificate": True,
        "target_generation_witness_access_count": 0,
        "planning_kernel_step_count": 0,
        "sample_label_and_planning_compute_axes_separate": True,
        "verification_implementation_imports_campaign_producer": False,
        "verified_claim_scope": "REGISTERED_SIX_INSTANCE_LMB_MATCHED_ACQUISITION_WORKLOAD_V42",
        "cross_domain_general_sample_efficiency_claimed": False,
        "broad_iid_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "PRODUCER_FREE_LMB_REUSABLE_WORLD_MODEL_CAMPAIGN_VERIFIED",
    }
    verification = {
        **verification_payload,
        "lmb_reusable_world_model_verification_id": content_id(
            pre.FUTURE_DOMAINS["verification"], verification_payload
        ),
    }
    raw = canonical_json_bytes(verification)
    identity = verification["lmb_reusable_world_model_verification_id"]
    if EXPECTED_VERIFICATION_ID != "0" * 64 and (
        identity != EXPECTED_VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen independent verification changed")
    if output_path is not None:
        Path(output_path).write_bytes(raw)
    return LMBReusableWorldModelIndependentVerificationV42(_ISSUER, raw, identity)


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "LMBReusableWorldModelIndependentVerificationV42",
    "independently_verify_lmb_reusable_world_model_campaign_v42",
)
