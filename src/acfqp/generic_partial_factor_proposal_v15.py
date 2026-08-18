"""Observation-bound partial proposals from the frozen V51 factor templates.

The factor prior contains anonymous normalized expressions, not target slots.
For every target output, this module enumerates every type-compatible binding of
those templates, evaluates it on aligned raw transitions, and retains the exact
minimum-description binding.  Unknown outputs remain explicitly unknown.  A
candidate is usable only after at least three output assignments were derived.

Each candidate is frozen before future batches.  Its known assignments are
scored by a universal-mixture e-process; a failed prediction invalidates the
candidate and starts a fresh telescopically weighted epoch.  This boundary does
not claim a complete world model or a plan: it is the proposal mechanism needed
for certificate-first partial planning in the successor campaign.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import heapq
from itertools import product
import hashlib
from math import ceil
from typing import Any, Callable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    DiscoveredLayoutV5,
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
)
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    integer_sequence_prefix_bits_v14,
    unsigned_integer_prefix_bits_v14,
    utf8_prefix_bits_v14,
)
from acfqp.phase3e_ids import canonical_json_bytes


V51_FACTOR_TEMPLATE_PROJECTION = {
    "schema": "acfqp.cross_schema_factor_template_projection.v15",
    "source_v51_campaign_id": (
        "44a63b782201b3e53a32de1bc071d66fb06526903f96a037d2c55c8f3068e144"
    ),
    "source_v51_verification_id": (
        "8d0e1044fe8db610375f35cd0956387b1ce6dca21d786cc62ae9bf1c69c66b3f"
    ),
    "source_factor_library_id": (
        "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
    ),
    "cross_schema_subprograms": [
        {
            "signature_sha256": (
                "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e"
            ),
            "result_type": "INT",
            "normalized_expression": ["S", "SELF"],
            "source_schema_pairs": [[7, 5], [9, 6]],
        },
        {
            "signature_sha256": (
                "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072"
            ),
            "result_type": "FINITE_INT_SUPPORT",
            "normalized_expression": [
                "E07",
                ["S", "SELF"],
                ["E05", ["S", "SELF"], ["A", 0]],
            ],
            "source_schema_pairs": [[7, 5], [9, 6]],
        },
        {
            "signature_sha256": (
                "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5"
            ),
            "result_type": "INT",
            "normalized_expression": ["A", 0],
            "source_schema_pairs": [[7, 5], [9, 6]],
        },
    ],
    "target_slot_inventory_supplied": False,
    "semantic_names_supplied": False,
}


class GenericPartialFactorProposalV15Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPartialFactorProposalV15Error(message)


@dataclass(frozen=True, slots=True)
class PartialFactorCandidateV15:
    public_document: Mapping[str, Any]
    layout: DiscoveredLayoutV5
    assignments: tuple[Mapping[str, Any], ...]
    issuance_rows: tuple[FlatRawTransitionV4, ...]


def _instantiations(
    target_column: int,
    action_width: int,
    library: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    result = []
    for template in library["cross_schema_subprograms"]:
        normalized = template["normalized_expression"]
        signature = template["signature_sha256"]
        if normalized == ["S", "SELF"]:
            result.append(
                {
                    "target_column": target_column,
                    "result_type": "INT",
                    "expression": ["E00", target_column],
                    "signature_sha256": signature,
                    "state_dependencies": [target_column],
                    "action_dependencies": [],
                }
            )
        elif normalized == ["A", 0]:
            for field in range(action_width):
                result.append(
                    {
                        "target_column": target_column,
                        "result_type": "INT",
                        "expression": ["E01", field],
                        "signature_sha256": signature,
                        "state_dependencies": [],
                        "action_dependencies": [field],
                    }
                )
        elif normalized == [
            "E07",
            ["S", "SELF"],
            ["E05", ["S", "SELF"], ["A", 0]],
        ]:
            for field in range(action_width):
                result.append(
                    {
                        "target_column": target_column,
                        "result_type": "FINITE_INT_SUPPORT",
                        "expression": [
                            "E07",
                            ["E00", target_column],
                            [
                                "E05",
                                ["E00", target_column],
                                ["E01", field],
                            ],
                        ],
                        "signature_sha256": signature,
                        "state_dependencies": [target_column],
                        "action_dependencies": [field],
                    }
                )
        else:  # pragma: no cover - frozen projection inventory
            _fail("V15 factor template escaped its frozen grammar")
    return tuple(result)


def _support(assignment: Mapping[str, Any], row: FlatRawTransitionV4) -> tuple[int, ...]:
    expression = assignment["expression"]
    if expression[0] == "E00":
        return (row.pre[expression[1]],)
    if expression[0] == "E01":
        return (row.action.fields[expression[1]],)
    if expression[0] == "E07":
        column = expression[1][1]
        field = expression[2][2][1]
        base = row.pre[column]
        return tuple(sorted({base, base + row.action.fields[field]}))
    _fail("V15 instantiated expression escaped its evaluator")


def _exact(assignment: Mapping[str, Any], rows: tuple[FlatRawTransitionV4, ...]) -> bool:
    target = assignment["target_column"]
    return all(row.post[target] in _support(assignment, row) for row in rows)


def synthesize_partial_factor_candidate_v15(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    factor_library: Mapping[str, Any],
    *,
    support_label_count: int,
    layout_domain: str,
    candidate_domain: str,
    candidate_content_id: Callable[[str, Any], str],
    minimum_factor_assignment_count: int,
) -> PartialFactorCandidateV15:
    if support_label_count <= 0 or not rows or not catalogue:
        _fail("V15 partial proposal requires nonempty raw evidence")
    if (
        factor_library.get("schema")
        != "acfqp.cross_schema_factor_template_projection.v15"
        or factor_library.get("target_slot_inventory_supplied") is not False
        or minimum_factor_assignment_count <= 0
    ):
        _fail("V15 factor-prior contract changed")
    layout = discover_generic_layout_v5(rows, catalogue, layout_domain=layout_domain)
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    state_width = len(aligned_rows[0].pre)
    action_width = len(aligned_catalogue[0].fields)
    assignments = []
    ambiguities = []
    for target in range(state_width):
        exact = [
            row
            for row in _instantiations(target, action_width, factor_library)
            if _exact(row, aligned_rows)
        ]
        if not exact:
            continue
        exact.sort(
            key=lambda row: (
                len(canonical_json_bytes(row["expression"])),
                canonical_json_bytes(row["expression"]),
                row["signature_sha256"],
            )
        )
        assignments.append(exact[0])
        ambiguities.append(
            {
                "target_column": target,
                "exact_template_binding_count": len(exact),
                "selection": "MIN_CANONICAL_EXPRESSION_BYTES_THEN_BYTES_THEN_SIGNATURE",
            }
        )
    if len(assignments) < minimum_factor_assignment_count:
        _fail("V15 observations did not identify enough reusable factor assignments")
    payload = {
        "schema": "acfqp.generic_partial_factor_candidate.v15",
        "source_factor_library_id": factor_library["source_factor_library_id"],
        "support_label_count_at_issuance": support_label_count,
        "raw_transition_count_at_issuance": len(rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "layout": layout.to_document(),
        "state_width": state_width,
        "action_field_width": action_width,
        "compiled_factor_assignments": assignments,
        "unknown_residual_target_columns": sorted(
            set(range(state_width))
            - {row["target_column"] for row in assignments}
        ),
        "binding_ambiguity_inventory": ambiguities,
        "minimum_factor_assignment_count": minimum_factor_assignment_count,
        "target_slot_inventory_supplied_by_prior": False,
        "target_bindings_derived_from_raw_observations": True,
        "semantic_names_used": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = {
        **payload,
        "candidate_id": candidate_content_id(candidate_domain, payload),
    }
    return PartialFactorCandidateV15(
        document, layout, tuple(assignments), aligned_rows
    )


def exact_partial_factor_replay_v15(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    aligned_rows, _aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    mismatch_rows = []
    for row in aligned_rows:
        mismatches = [
            assignment["target_column"]
            for assignment in candidate.assignments
            if row.post[assignment["target_column"]] not in _support(assignment, row)
        ]
        if mismatches:
            mismatch_rows.append(
                {
                    "transition_index": row.index,
                    "mismatched_target_columns": mismatches,
                }
            )
    return {
        "candidate_id": candidate.public_document["candidate_id"],
        "raw_transition_count": len(rows),
        "factor_assignment_count": len(candidate.assignments),
        "mismatch_count": len(mismatch_rows),
        "mismatch_rows": mismatch_rows,
        "exact": not mismatch_rows,
    }


def partial_factor_universal_stop_update_v15(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    candidate_epoch: int,
    post_issuance_exact_prediction_success_count: int,
    global_alpha_denominator: int,
) -> dict[str, Any]:
    if (
        candidate_epoch < 0
        or post_issuance_exact_prediction_success_count < 0
        or global_alpha_denominator <= 1
    ):
        _fail("V15 partial-factor stopping contract changed")
    replay = exact_partial_factor_replay_v15(candidate, rows, catalogue)
    successes = post_issuance_exact_prediction_success_count
    numerator = 2 ** (successes + 1) - 1
    denominator = successes + 1
    epoch_denominator = (candidate_epoch + 1) * (candidate_epoch + 2)
    threshold = global_alpha_denominator * epoch_denominator
    threshold_met = numerator >= denominator * threshold
    return {
        "schema": "acfqp.generic_partial_factor_universal_stop_update.v15",
        "candidate_id": candidate.public_document["candidate_id"],
        "candidate_epoch": candidate_epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "universal_mixture_evalue_numerator": numerator,
        "universal_mixture_evalue_denominator": denominator,
        "evalue_threshold": threshold,
        "universal_mixture_evalue_threshold_met": threshold_met,
        "current_partial_factor_replay": replay,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
        "stopped": replay["exact"] is True and threshold_met,
    }


def partial_factor_bit_codelength_stop_update_v15(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    candidate_epoch: int,
    invalidated_candidate_count: int,
    post_issuance_exact_prediction_success_count: int,
    global_alpha_denominator: int,
) -> dict[str, Any]:
    if invalidated_candidate_count < 0:
        _fail("V15 invalidated-candidate count changed")
    evidence = partial_factor_universal_stop_update_v15(
        candidate,
        rows,
        catalogue,
        candidate_epoch=candidate_epoch,
        post_issuance_exact_prediction_success_count=(
            post_issuance_exact_prediction_success_count
        ),
        global_alpha_denominator=global_alpha_denominator,
    )
    targets = tuple(row["target_column"] for row in candidate.assignments)
    state_layout = tuple(candidate.layout.state_canonical_to_raw)
    action_layout = tuple(candidate.layout.action_canonical_to_raw)
    program_bits = (
        integer_sequence_prefix_bits_v14(state_layout)
        + integer_sequence_prefix_bits_v14(action_layout)
        + unsigned_integer_prefix_bits_v14(len(candidate.assignments))
    )
    for assignment in candidate.assignments:
        program_bits += (
            unsigned_integer_prefix_bits_v14(assignment["target_column"])
            + utf8_prefix_bits_v14(assignment["result_type"])
            + utf8_prefix_bits_v14(assignment["signature_sha256"])
            + integer_sequence_prefix_bits_v14(assignment["state_dependencies"])
            + integer_sequence_prefix_bits_v14(assignment["action_dependencies"])
        )
    raw_bits = sum(
        integer_sequence_prefix_bits_v14(row.post[target] for target in targets)
        for row in rows
    )
    branch_bits = sum(
        assignment["result_type"] == "FINITE_INT_SUPPORT"
        for assignment in candidate.assignments
    ) * len(rows)
    change_bits = unsigned_integer_prefix_bits_v14(invalidated_candidate_count)
    total_model_bits = program_bits + branch_bits + change_bits
    savings_bits = raw_bits - total_model_bits
    return {
        **evidence,
        "schema": "acfqp.generic_partial_factor_bit_codelength_stop_update.v15",
        "partial_prediction_target_columns": list(targets),
        "raw_partial_outcome_prefix_code_bits": raw_bits,
        "partial_program_prefix_code_bits": program_bits,
        "partial_model_outcome_branch_bits": branch_bits,
        "candidate_change_prefix_code_bits": change_bits,
        "total_partial_two_part_model_code_bits": total_model_bits,
        "partial_two_part_codelength_savings_bits": savings_bits,
        "unknown_residual_outputs_transmitted_or_claimed": False,
        "factor_library_reference_code_available": True,
        "complete_world_model_claimed": False,
        "stopped": evidence["stopped"] is True and savings_bits >= 0,
    }


def _canonical_state(
    candidate: PartialFactorCandidateV15, raw_state: tuple[int, ...]
) -> tuple[int, ...]:
    return tuple(
        raw_state[index] for index in candidate.layout.state_canonical_to_raw
    )


def _canonical_catalogue(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[FlatRawActionV4, ...]:
    return tuple(
        FlatRawActionV4(
            action.key,
            tuple(
                action.fields[index]
                for index in candidate.layout.action_canonical_to_raw
            ),
        )
        for action in catalogue
    )


def _terminal_projection_rule(
    candidate: PartialFactorCandidateV15,
    aligned_rows: tuple[FlatRawTransitionV4, ...],
    actions: tuple[FlatRawActionV4, ...],
) -> tuple[dict[str, Any], ...]:
    accepting = tuple(row for row in aligned_rows if row.terminal_acceptance_after is True)
    if not accepting:
        _fail("V15 partial observations exposed no accepting projection")
    rules = []
    for assignment in candidate.assignments:
        target = assignment["target_column"]
        values = tuple(sorted({row.post[target] for row in accepting}))
        expression = assignment["expression"]
        if expression[0] == "E00" and len(values) == 1:
            rule = {"kind": "EQUAL", "value": values[0]}
        elif expression[0] == "E07":
            field = expression[2][2][1]
            increments = tuple(action.fields[field] for action in actions)
            if all(value >= 0 for value in increments):
                rule = {"kind": "AT_LEAST", "value": min(values)}
            elif all(value <= 0 for value in increments):
                rule = {"kind": "AT_MOST", "value": max(values)}
            else:
                rule = {"kind": "OBSERVED_SET", "values": list(values)}
        else:
            rule = {"kind": "UNCONSTRAINED"}
        rules.append({"target_column": target, **rule})
    return tuple(rules)


def _terminal_projection_matches(
    state: tuple[int, ...],
    rules: tuple[Mapping[str, Any], ...],
    rejected: frozenset[tuple[int, ...]],
) -> bool:
    if state in rejected:
        return False
    for value, rule in zip(state, rules, strict=True):
        kind = rule["kind"]
        if kind == "EQUAL" and value != rule["value"]:
            return False
        if kind == "AT_LEAST" and value < rule["value"]:
            return False
        if kind == "AT_MOST" and value > rule["value"]:
            return False
        if kind == "OBSERVED_SET" and value not in rule["values"]:
            return False
    return True


def partial_factor_successor_projections_v15(
    candidate: PartialFactorCandidateV15,
    projected_state: tuple[int, ...],
    action: FlatRawActionV4,
) -> tuple[tuple[int, ...], ...]:
    targets = tuple(row["target_column"] for row in candidate.assignments)
    if len(projected_state) != len(targets):
        _fail("V15 projected state width changed")
    state_by_target = dict(zip(targets, projected_state, strict=True))
    supports = []
    for assignment in candidate.assignments:
        expression = assignment["expression"]
        target = assignment["target_column"]
        if expression[0] == "E00":
            values = (state_by_target[target],)
        elif expression[0] == "E01":
            values = (action.fields[expression[1]],)
        elif expression[0] == "E07":
            base = state_by_target[target]
            field = expression[2][2][1]
            values = tuple(sorted({base, base + action.fields[field]}))
        else:  # pragma: no cover - constructor grammar
            _fail("V15 projected execution escaped its factor grammar")
        supports.append(values)
    return tuple(sorted(set(product(*supports))))


def plan_partial_factor_program_v15(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    *,
    forbidden_projection_actions: frozenset[tuple[tuple[int, ...], int]] = frozenset(),
    rejected_accepting_projections: frozenset[tuple[int, ...]] = frozenset(),
    maximum_depth: int,
) -> dict[str, Any]:
    if maximum_depth <= 0:
        _fail("V15 partial planning depth changed")
    aligned_rows, _ = align_generic_occurrence_v5(
        observed_rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    targets = tuple(row["target_column"] for row in candidate.assignments)
    initial_canonical = _canonical_state(candidate, initial_raw_state)
    initial = tuple(initial_canonical[target] for target in targets)
    actions = _canonical_catalogue(candidate, catalogue)
    terminal_rule = _terminal_projection_rule(candidate, aligned_rows, actions)
    action_values = {
        field: tuple(action.fields[field] for action in actions)
        for field in range(len(actions[0].fields))
    }

    def lower_bound(state: tuple[int, ...]) -> int | None:
        coordinate_bounds = []
        for offset, (assignment, rule) in enumerate(
            zip(candidate.assignments, terminal_rule, strict=True)
        ):
            current = state[offset]
            kind = rule["kind"]
            if kind == "UNCONSTRAINED":
                coordinate_bounds.append(0)
                continue
            if kind == "EQUAL":
                if current != rule["value"]:
                    return None
                coordinate_bounds.append(0)
                continue
            expression = assignment["expression"]
            if expression[0] != "E07":
                coordinate_bounds.append(0)
                continue
            increments = action_values[expression[2][2][1]]
            if kind == "AT_LEAST":
                distance = max(0, rule["value"] - current)
                maximum = max(increments)
            elif kind == "AT_MOST":
                distance = max(0, current - rule["value"])
                maximum = max(-value for value in increments)
            else:
                distance = min(abs(current - value) for value in rule["values"])
                maximum = max(abs(value) for value in increments)
            coordinate_bounds.append(
                0
                if distance == 0
                else ceil(distance / maximum)
                if maximum > 0
                else maximum_depth + 1
            )
        return max(coordinate_bounds, default=0)

    evaluations = 0
    initial_bound = lower_bound(initial)
    if initial_bound is None or initial_bound > maximum_depth:
        _fail("V15 partial factor program found no support-feasible continuation")
    frontier = [(initial_bound, 0, initial)]
    best_depth = {initial: 0}
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    terminal = None
    while frontier:
        _priority, depth, state = heapq.heappop(frontier)
        if depth != best_depth[state]:
            continue
        if _terminal_projection_matches(
            state, terminal_rule, rejected_accepting_projections
        ):
            terminal = state
            break
        if depth == maximum_depth:
            continue
        for action in actions:
            if (state, action.key) in forbidden_projection_actions:
                continue
            successors = partial_factor_successor_projections_v15(
                candidate, state, action
            )
            evaluations += len(successors)
            for successor in successors:
                if successor == state:
                    continue
                successor_bound = lower_bound(successor)
                successor_depth = depth + 1
                if (
                    successor_bound is None
                    or successor_depth + successor_bound > maximum_depth
                    or successor_depth >= best_depth.get(successor, maximum_depth + 1)
                ):
                    continue
                best_depth[successor] = successor_depth
                predecessor[successor] = (state, action.key)
                heapq.heappush(
                    frontier,
                    (successor_depth + successor_bound, successor_depth, successor),
                )
    if terminal is None:
        _fail("V15 partial factor program found no support-feasible continuation")
    reversed_actions = []
    cursor = terminal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        reversed_actions.append(key)
        cursor = parent
    plan = list(reversed(reversed_actions))
    selected_depth = len(plan)
    return {
        "schema": "acfqp.generic_partial_factor_receding_plan.v15",
        "candidate_id": candidate.public_document["candidate_id"],
        "known_factor_target_columns": list(targets),
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "terminal_projection_rule": [dict(row) for row in terminal_rule],
        "rejected_accepting_projection_count": len(
            rejected_accepting_projections
        ),
        "selected_support_feasible_depth": selected_depth,
        "action_keys": plan,
        "projected_planning_compute_events": evaluations,
        "stochastic_support_branch_receding_semantics": True,
        "robust_all_branches_completion_claimed": False,
        "finite_worst_case_completion_claimed": False,
        "ground_transition_accessed_during_abstract_search": False,
        "complete_world_model_claimed": False,
    }


def plan_partial_factor_observation_graph_v15(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    *,
    forbidden_projection_actions: frozenset[tuple[tuple[int, ...], int]] = frozenset(),
    rejected_accepting_projections: frozenset[tuple[int, ...]] = frozenset(),
) -> dict[str, Any]:
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        observed_rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    actions = {action.key: action for action in aligned_catalogue}
    targets = tuple(row["target_column"] for row in candidate.assignments)
    terminal_rule = _terminal_projection_rule(
        candidate, aligned_rows, tuple(actions.values())
    )
    adjacency: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = {}
    edge_checks = 0
    for row in aligned_rows:
        pre = tuple(row.pre[target] for target in targets)
        post = tuple(row.post[target] for target in targets)
        predicted = partial_factor_successor_projections_v15(
            candidate, pre, actions[row.action.key]
        )
        edge_checks += len(predicted)
        if post not in predicted:
            _fail("V15 observation edge escaped the compiled factor program")
        adjacency.setdefault(pre, set()).add((row.action.key, post))
    initial_canonical = _canonical_state(candidate, initial_raw_state)
    initial = tuple(initial_canonical[target] for target in targets)
    queue = deque((initial,))
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    goal = None
    evaluations = 0
    while queue:
        state = queue.popleft()
        if _terminal_projection_matches(
            state, terminal_rule, rejected_accepting_projections
        ):
            goal = state
            break
        for key, successor in sorted(adjacency.get(state, set())):
            evaluations += 1
            if (state, key) in forbidden_projection_actions:
                continue
            if successor not in predecessor:
                predecessor[successor] = (state, key)
                queue.append(successor)
    if goal is None:
        _fail("V15 observation graph found no projected continuation")
    reversed_actions = []
    cursor = goal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        reversed_actions.append(key)
        cursor = parent
    plan = list(reversed(reversed_actions))
    return {
        "schema": "acfqp.generic_partial_factor_observation_graph_plan.v15",
        "candidate_id": candidate.public_document["candidate_id"],
        "known_factor_target_columns": list(targets),
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "abstract_state_count": len(adjacency),
        "abstract_edge_count": sum(len(rows) for rows in adjacency.values()),
        "compiled_factor_support_edge_checks": edge_checks,
        "terminal_projection_rule": [dict(row) for row in terminal_rule],
        "action_keys": plan,
        "projected_planning_compute_events": evaluations,
        "compiled_factor_program_checked_each_abstract_edge": True,
        "ground_transition_accessed_during_abstract_search": False,
        "complete_world_model_claimed": False,
    }


__all__ = (
    "PartialFactorCandidateV15",
    "V51_FACTOR_TEMPLATE_PROJECTION",
    "exact_partial_factor_replay_v15",
    "partial_factor_bit_codelength_stop_update_v15",
    "plan_partial_factor_observation_graph_v15",
    "partial_factor_successor_projections_v15",
    "partial_factor_universal_stop_update_v15",
    "plan_partial_factor_program_v15",
    "synthesize_partial_factor_candidate_v15",
)
