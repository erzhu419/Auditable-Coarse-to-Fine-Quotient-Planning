"""Incrementally compile an exact V105 quotient successor from local deltas.

The live state contains only compiled projected facts and raw-row identities.
Planning consumes that compiled state directly; raw transitions remain outside
the planner and are used only by the certificate engine and the matched full
rebuild verifier.
"""

from __future__ import annotations

from collections import defaultdict, deque
import copy
from dataclasses import dataclass, field
import hashlib
import heapq
from math import ceil
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v113 as domains
from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_observation_quotient_graph_v105 import (
    compile_observation_quotient_graph_v105,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    partial_factor_successor_projections_v15,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


_V105_MODEL_DOMAIN = b"acfqp:generic-observation-quotient-graph:v105\x00"
_V106_PLAN_DOMAIN = b"acfqp:generic-legality-conditioned-quotient-plan:v106\x00"
_ISSUER = object()


class GenericIncrementalAbstractSuccessorV113Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericIncrementalAbstractSuccessorV113Error(message)


def _raw_key(row: FlatRawTransitionV4) -> tuple[tuple[int, ...], int, tuple[int, ...]]:
    return row.pre, row.action.key, row.post


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique = {_raw_key(row): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _canonical_actions(
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


def _terminal_rules(
    candidate: PartialFactorCandidateV15,
    accepting_values: tuple[tuple[int, tuple[int, ...]], ...],
    actions: tuple[FlatRawActionV4, ...],
) -> tuple[dict[str, Any], ...]:
    by_target = dict(accepting_values)
    if not by_target or any(not by_target.get(row["target_column"]) for row in candidate.assignments):
        _fail("V113 partial observations exposed no accepting projection")
    rules = []
    for assignment in candidate.assignments:
        target = assignment["target_column"]
        values = by_target[target]
        expression = assignment["expression"]
        if expression[0] == "E00" and len(values) == 1:
            rule = {"kind": "EQUAL", "value": values[0]}
        elif expression[0] == "E07":
            action_field = expression[2][2][1]
            increments = tuple(action.fields[action_field] for action in actions)
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


def _project_rows(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[
    frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
    frozenset[tuple[tuple[int, ...], str]],
    frozenset[tuple[tuple[int, ...], int]],
    tuple[tuple[int, tuple[int, ...]], ...],
    int,
]:
    if not rows:
        return frozenset(), frozenset(), frozenset(), (), 0
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    actions = {action.key: action for action in aligned_catalogue}
    targets = tuple(row["target_column"] for row in candidate.assignments)
    edges: set[tuple[tuple[int, ...], int, tuple[int, ...]]] = set()
    terminal: set[tuple[tuple[int, ...], str]] = set()
    contexts: set[tuple[tuple[int, ...], int]] = set()
    accepting: dict[int, set[int]] = defaultdict(set)
    checks = 0
    for row in aligned_rows:
        pre = tuple(row.pre[target] for target in targets)
        post = tuple(row.post[target] for target in targets)
        predicted = partial_factor_successor_projections_v15(
            candidate, pre, actions[row.action.key]
        )
        checks += len(predicted)
        if post not in predicted:
            _fail("V113 projected observation escaped the compiled factor program")
        edges.add((pre, row.action.key, post))
        terminal_class = (
            "ACTIVE"
            if row.legal_after
            else "ACCEPT"
            if row.terminal_acceptance_after is True
            else "REJECT"
        )
        terminal.add((post, terminal_class))
        contexts.add((row.pre, row.action.key))
        if row.terminal_acceptance_after is True:
            for target in targets:
                accepting[target].add(row.post[target])
    return (
        frozenset(edges),
        frozenset(terminal),
        frozenset(contexts),
        tuple((target, tuple(sorted(values))) for target, values in sorted(accepting.items())),
        checks,
    )


def _model_document(
    candidate: PartialFactorCandidateV15,
    raw_keys: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
    contexts: frozenset[tuple[tuple[int, ...], int]],
    edges: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
    terminal_memberships: frozenset[tuple[tuple[int, ...], str]],
    checks: int,
) -> dict[str, Any]:
    edge_rows = [
        {
            "projected_pre": list(pre),
            "action_key": key,
            "projected_post": list(post),
        }
        for pre, key, post in sorted(edges)
    ]
    terminal: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for state, terminal_class in terminal_memberships:
        terminal[state].add(terminal_class)
    terminal_rows = [
        {
            "projected_state": list(state),
            "observed_terminal_classes": sorted(classes),
        }
        for state, classes in sorted(terminal.items())
    ]
    public = candidate.public_document
    targets = [row["target_column"] for row in candidate.assignments]
    payload = {
        "schema": "acfqp.generic_observation_quotient_graph.v105",
        "partial_candidate_id": public["candidate_id"],
        "layout_id": public["layout"]["layout_id"],
        "projected_state_target_columns": targets,
        "quotiented_residual_target_columns": list(
            public["unknown_residual_target_columns"]
        ),
        "projected_state_width": len(targets),
        "projected_edge_rows": edge_rows,
        "projected_edge_count": len(edge_rows),
        "projected_terminal_rows": terminal_rows,
        "projected_terminal_state_count": len(terminal_rows),
        "source_ground_support_label_count": len(contexts),
        "source_raw_transition_row_count": len(raw_keys),
        "source_projected_edge_program_checks": checks,
        "source_projected_rows_sha256": hashlib.sha256(
            canonical_json_bytes({"edges": edge_rows, "terminal": terminal_rows})
        ).hexdigest(),
        "all_projected_edges_checked_by_compiled_factor_program": True,
        "residual_coordinates_deliberately_quotiented_not_imputed": True,
        "query_local_overlay_may_extend_graph_only_after_certificate_failure": True,
        "ground_transition_accessed_during_abstract_search": False,
        "quotient_graph_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "quotient_graph_id": hashlib.sha256(
            _V105_MODEL_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _state_payload(
    model: Mapping[str, Any],
    terminal_rules: tuple[Mapping[str, Any], ...],
    raw_keys: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
) -> dict[str, Any]:
    raw_inventory = [
        {"pre": list(pre), "action_key": action, "post": list(post)}
        for pre, action, post in sorted(raw_keys)
    ]
    return {
        "quotient_graph_id": model["quotient_graph_id"],
        "terminal_projection_rule": [dict(row) for row in terminal_rules],
        "raw_row_identity_count": len(raw_keys),
        "raw_row_identity_sha256": hashlib.sha256(
            canonical_json_bytes(raw_inventory)
        ).hexdigest(),
    }


@dataclass(frozen=True, slots=True)
class IncrementalAbstractSuccessorStateV113:
    _issuer: object = field(repr=False, compare=False)
    candidate_id: str
    layout_id: str
    raw_keys: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]]
    contexts: frozenset[tuple[tuple[int, ...], int]]
    edges: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]]
    terminal_memberships: frozenset[tuple[tuple[int, ...], str]]
    accepting_values: tuple[tuple[int, tuple[int, ...]], ...]
    projected_program_checks: int
    model_bytes: bytes = field(repr=False)
    terminal_rules_bytes: bytes = field(repr=False)
    state_id: str

    @property
    def model(self) -> dict[str, Any]:
        return loads_canonical_json(self.model_bytes)

    @property
    def terminal_rules(self) -> tuple[dict[str, Any], ...]:
        value = loads_canonical_json(self.terminal_rules_bytes)
        if type(value) is not list:
            _fail("V113 terminal rule bytes changed")
        return tuple(value)


def _verify_state(
    state: IncrementalAbstractSuccessorStateV113,
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if (
        type(state) is not IncrementalAbstractSuccessorStateV113
        or state._issuer is not _ISSUER
        or type(candidate) is not PartialFactorCandidateV15
        or type(catalogue) is not tuple
        or not catalogue
        or state.candidate_id != candidate.public_document["candidate_id"]
        or state.layout_id != candidate.public_document["layout"]["layout_id"]
    ):
        _fail("V113 incremental state authority changed")
    model = _model_document(
        candidate,
        state.raw_keys,
        state.contexts,
        state.edges,
        state.terminal_memberships,
        state.projected_program_checks,
    )
    actions = _canonical_actions(candidate, catalogue)
    rules = _terminal_rules(candidate, state.accepting_values, actions)
    payload = _state_payload(model, rules, state.raw_keys)
    expected_id = hashlib.sha256(
        b"acfqp:generic-incremental-abstract-successor-state:v113\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    if (
        canonical_json_bytes(model) != state.model_bytes
        or canonical_json_bytes(list(rules)) != state.terminal_rules_bytes
        or state.state_id != expected_id
    ):
        _fail("V113 incremental state reconstruction changed")
    return model, rules


def _make_state(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    raw_keys: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
    contexts: frozenset[tuple[tuple[int, ...], int]],
    edges: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
    terminal_memberships: frozenset[tuple[tuple[int, ...], str]],
    accepting_values: tuple[tuple[int, tuple[int, ...]], ...],
    projected_program_checks: int,
) -> IncrementalAbstractSuccessorStateV113:
    model = _model_document(
        candidate,
        raw_keys,
        contexts,
        edges,
        terminal_memberships,
        projected_program_checks,
    )
    rules = _terminal_rules(
        candidate, accepting_values, _canonical_actions(candidate, catalogue)
    )
    payload = _state_payload(model, rules, raw_keys)
    state = IncrementalAbstractSuccessorStateV113(
        _ISSUER,
        candidate.public_document["candidate_id"],
        candidate.public_document["layout"]["layout_id"],
        raw_keys,
        contexts,
        edges,
        terminal_memberships,
        accepting_values,
        projected_program_checks,
        canonical_json_bytes(model),
        canonical_json_bytes(list(rules)),
        hashlib.sha256(
            b"acfqp:generic-incremental-abstract-successor-state:v113\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    )
    _verify_state(state, candidate, catalogue)
    return state


def initialize_incremental_abstract_successor_v113(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[IncrementalAbstractSuccessorStateV113, dict[str, Any]]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or type(catalogue) is not tuple
        or not catalogue
    ):
        _fail("V113 bootstrap inventory changed")
    rows = _deduplicate(observed_rows)
    edges, terminal, contexts, accepting, checks = _project_rows(
        candidate, rows, catalogue
    )
    state = _make_state(
        candidate,
        catalogue,
        raw_keys=frozenset(_raw_key(row) for row in rows),
        contexts=contexts,
        edges=edges,
        terminal_memberships=terminal,
        accepting_values=accepting,
        projected_program_checks=checks,
    )
    writes = len(edges) + len(terminal) + len(contexts) + sum(
        len(values) for _target, values in accepting
    )
    payload = {
        "schema": "acfqp.generic_incremental_abstract_successor_bootstrap.v113",
        "successor_state_id": state.state_id,
        "quotient_graph_id": state.model["quotient_graph_id"],
        "bootstrap_raw_identity_checks": len(observed_rows),
        "bootstrap_unique_raw_rows": len(rows),
        "bootstrap_projected_program_checks": checks,
        "bootstrap_projection_index_writes": writes,
        "bootstrap_compilation_events": len(observed_rows) + checks + writes,
        "bootstrap_is_one_time_full_compile": True,
        "ground_transition_accessed_during_abstract_search": False,
        "incremental_model_used_as_safety_authority": False,
    }
    return state, {
        **payload,
        "bootstrap_receipt_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_BOOTSTRAP_V113_DOMAIN,
            payload,
        ),
    }


def advance_incremental_abstract_successor_v113(
    state: IncrementalAbstractSuccessorStateV113,
    candidate: PartialFactorCandidateV15,
    new_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[IncrementalAbstractSuccessorStateV113, dict[str, Any]]:
    previous_model, _previous_rules = _verify_state(state, candidate, catalogue)
    if type(new_rows) is not tuple:
        _fail("V113 delta inventory changed")
    unique_input = _deduplicate(new_rows)
    novel = tuple(row for row in unique_input if _raw_key(row) not in state.raw_keys)
    edges, terminal, contexts, accepting_delta, checks = _project_rows(
        candidate, novel, catalogue
    )
    accepting: dict[int, set[int]] = defaultdict(set)
    for target, values in state.accepting_values:
        accepting[target].update(values)
    accepting_insertions = 0
    for target, values in accepting_delta:
        before = len(accepting[target])
        accepting[target].update(values)
        accepting_insertions += len(accepting[target]) - before
    next_state = _make_state(
        candidate,
        catalogue,
        raw_keys=state.raw_keys | frozenset(_raw_key(row) for row in novel),
        contexts=state.contexts | contexts,
        edges=state.edges | edges,
        terminal_memberships=state.terminal_memberships | terminal,
        accepting_values=tuple(
            (target, tuple(sorted(values))) for target, values in sorted(accepting.items())
        ),
        projected_program_checks=state.projected_program_checks + checks,
    )
    edge_inserts = len(next_state.edges) - len(state.edges)
    terminal_inserts = len(next_state.terminal_memberships) - len(
        state.terminal_memberships
    )
    context_inserts = len(next_state.contexts) - len(state.contexts)
    writes = edge_inserts + terminal_inserts + context_inserts + accepting_insertions
    events = len(new_rows) + checks + writes
    payload = {
        "schema": "acfqp.generic_incremental_abstract_successor_update.v113",
        "previous_successor_state_id": state.state_id,
        "current_successor_state_id": next_state.state_id,
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": next_state.model["quotient_graph_id"],
        "delta_input_raw_row_count": len(new_rows),
        "delta_unique_input_raw_row_count": len(unique_input),
        "delta_novel_raw_row_count": len(novel),
        "delta_raw_identity_checks": len(new_rows),
        "delta_projected_program_checks": checks,
        "delta_projected_edge_insertions": edge_inserts,
        "delta_terminal_membership_insertions": terminal_inserts,
        "delta_ground_context_insertions": context_inserts,
        "delta_accepting_value_insertions": accepting_insertions,
        "delta_projection_index_writes": writes,
        "incremental_compilation_events": events,
        "model_identity_changed": previous_model["quotient_graph_id"]
        != next_state.model["quotient_graph_id"],
        "only_novel_certificate_local_rows_projected": True,
        "previous_compiled_rows_not_replayed": True,
        "ground_transition_accessed_during_abstract_search": False,
        "incremental_model_used_as_safety_authority": False,
    }
    return next_state, {
        **payload,
        "update_receipt_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_UPDATE_V113_DOMAIN,
            payload,
        ),
    }


def verify_incremental_successor_against_full_rebuild_v113(
    state: IncrementalAbstractSuccessorStateV113,
    candidate: PartialFactorCandidateV15,
    all_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    update_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    model, rules = _verify_state(state, candidate, catalogue)
    if type(all_rows) is not tuple or not all_rows:
        _fail("V113 full-rebuild match inventory changed")
    rows = _deduplicate(all_rows)
    full_model = compile_observation_quotient_graph_v105(candidate, rows, catalogue)
    edges, terminal, contexts, accepting, checks = _project_rows(
        candidate, rows, catalogue
    )
    full_rules = _terminal_rules(
        candidate, accepting, _canonical_actions(candidate, catalogue)
    )
    writes = len(edges) + len(terminal) + len(contexts) + sum(
        len(values) for _target, values in accepting
    )
    full_events = len(all_rows) + checks + writes
    if (
        model != full_model
        or rules != full_rules
        or state.raw_keys != frozenset(_raw_key(row) for row in rows)
    ):
        _fail("V113 incremental successor differs from exact full rebuild")
    incremental_events = (
        full_events
        if update_receipt is None
        else update_receipt.get("incremental_compilation_events")
    )
    if type(incremental_events) is not int or incremental_events < 0:
        _fail("V113 incremental compilation accounting changed")
    payload = {
        "schema": "acfqp.generic_incremental_abstract_successor_full_rebuild_match.v113",
        "successor_state_id": state.state_id,
        "quotient_graph_id": model["quotient_graph_id"],
        "update_receipt_id": None
        if update_receipt is None
        else update_receipt.get("update_receipt_id"),
        "incremental_compilation_events": incremental_events,
        "matched_full_rebuild_raw_identity_checks": len(all_rows),
        "matched_full_rebuild_projected_program_checks": checks,
        "matched_full_rebuild_projection_index_writes": writes,
        "matched_full_rebuild_compilation_events": full_events,
        "compilation_events_avoided_against_full_rebuild": full_events
        - incremental_events,
        "model_bytes_exactly_equal_full_v105_rebuild": True,
        "terminal_projection_rule_exactly_equal_full_rebuild": True,
        "raw_row_identity_inventory_exactly_equal_full_rebuild": True,
        "matched_control_compute_not_charged_to_incremental_arm": True,
        "incremental_model_used_as_safety_authority": False,
    }
    return {
        **payload,
        "match_receipt_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_MATCH_V113_DOMAIN,
            payload,
        ),
    }


def _terminal_match(
    state: tuple[int, ...], rules: tuple[Mapping[str, Any], ...]
) -> bool:
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


def _initial_projected_state(
    candidate: PartialFactorCandidateV15, raw: tuple[int, ...]
) -> tuple[int, ...]:
    canonical = tuple(raw[index] for index in candidate.layout.state_canonical_to_raw)
    return tuple(
        canonical[row["target_column"]] for row in candidate.assignments
    )


def _observation_graph_plan(
    model: Mapping[str, Any],
    rules: tuple[Mapping[str, Any], ...],
    initial: tuple[int, ...],
    legal: frozenset[int],
    candidate: PartialFactorCandidateV15,
) -> dict[str, Any]:
    adjacency: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = defaultdict(set)
    for row in model["projected_edge_rows"]:
        adjacency[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    queue = deque((initial,))
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    goal = None
    evaluations = 0
    while queue:
        state = queue.popleft()
        if _terminal_match(state, rules):
            goal = state
            break
        for key, successor in sorted(adjacency.get(state, set())):
            evaluations += 1
            if state == initial and key not in legal:
                continue
            if successor not in predecessor:
                predecessor[successor] = (state, key)
                queue.append(successor)
    if goal is None:
        _fail("V113 compiled observation graph found no projected continuation")
    actions = []
    cursor = goal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        actions.append(key)
        cursor = parent
    actions.reverse()
    return {
        "schema": "acfqp.generic_partial_factor_observation_graph_plan.v15",
        "candidate_id": candidate.public_document["candidate_id"],
        "known_factor_target_columns": [
            row["target_column"] for row in candidate.assignments
        ],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "abstract_state_count": len(adjacency),
        "abstract_edge_count": sum(len(rows) for rows in adjacency.values()),
        "compiled_factor_support_edge_checks": model[
            "source_projected_edge_program_checks"
        ],
        "terminal_projection_rule": [dict(row) for row in rules],
        "action_keys": actions,
        "projected_planning_compute_events": evaluations,
        "compiled_factor_program_checked_each_abstract_edge": True,
        "ground_transition_accessed_during_abstract_search": False,
        "complete_world_model_claimed": False,
    }


def _program_plan(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    rules: tuple[Mapping[str, Any], ...],
    initial: tuple[int, ...],
    legal: frozenset[int],
    *,
    maximum_depth: int,
) -> dict[str, Any]:
    actions = _canonical_actions(candidate, catalogue)
    action_values = {
        field: tuple(action.fields[field] for action in actions)
        for field in range(len(actions[0].fields))
    }

    def lower_bound(state: tuple[int, ...]) -> int | None:
        bounds = []
        for offset, (assignment, rule) in enumerate(
            zip(candidate.assignments, rules, strict=True)
        ):
            current = state[offset]
            kind = rule["kind"]
            if kind == "UNCONSTRAINED":
                bounds.append(0)
                continue
            if kind == "EQUAL":
                if current != rule["value"]:
                    return None
                bounds.append(0)
                continue
            expression = assignment["expression"]
            if expression[0] != "E07":
                bounds.append(0)
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
            bounds.append(
                0
                if distance == 0
                else ceil(distance / maximum)
                if maximum > 0
                else maximum_depth + 1
            )
        return max(bounds, default=0)

    initial_bound = lower_bound(initial)
    if initial_bound is None or initial_bound > maximum_depth:
        _fail("V113 compiled factor program found no support-feasible continuation")
    frontier = [(initial_bound, 0, initial)]
    best_depth = {initial: 0}
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    terminal = None
    evaluations = 0
    while frontier:
        _priority, depth, state = heapq.heappop(frontier)
        if depth != best_depth[state]:
            continue
        if _terminal_match(state, rules):
            terminal = state
            break
        if depth == maximum_depth:
            continue
        for action in actions:
            if state == initial and action.key not in legal:
                continue
            successors = partial_factor_successor_projections_v15(
                candidate, state, action
            )
            evaluations += len(successors)
            for successor in successors:
                if successor == state:
                    continue
                bound = lower_bound(successor)
                successor_depth = depth + 1
                if (
                    bound is None
                    or successor_depth + bound > maximum_depth
                    or successor_depth >= best_depth.get(successor, maximum_depth + 1)
                ):
                    continue
                best_depth[successor] = successor_depth
                predecessor[successor] = (state, action.key)
                heapq.heappush(
                    frontier,
                    (successor_depth + bound, successor_depth, successor),
                )
    if terminal is None:
        _fail("V113 compiled factor program found no support-feasible continuation")
    actions_out = []
    cursor = terminal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        actions_out.append(key)
        cursor = parent
    actions_out.reverse()
    return {
        "schema": "acfqp.generic_partial_factor_receding_plan.v15",
        "candidate_id": candidate.public_document["candidate_id"],
        "known_factor_target_columns": [
            row["target_column"] for row in candidate.assignments
        ],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "terminal_projection_rule": [dict(row) for row in rules],
        "rejected_accepting_projection_count": 0,
        "selected_support_feasible_depth": len(actions_out),
        "action_keys": actions_out,
        "projected_planning_compute_events": evaluations,
        "stochastic_support_branch_receding_semantics": True,
        "robust_all_branches_completion_claimed": False,
        "finite_worst_case_completion_claimed": False,
        "ground_transition_accessed_during_abstract_search": False,
        "complete_world_model_claimed": False,
    }


def plan_incremental_abstract_successor_v113(
    state: IncrementalAbstractSuccessorStateV113,
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    exact_legal_action_keys: tuple[int, ...],
    *,
    legality_support_source: str,
    legality_failure_index: int | None,
    maximum_depth: int,
) -> dict[str, Any]:
    model, rules = _verify_state(state, candidate, catalogue)
    catalogue_keys = {action.key for action in catalogue}
    if (
        type(initial_raw_state) is not tuple
        or type(exact_legal_action_keys) is not tuple
        or not exact_legal_action_keys
        or len(set(exact_legal_action_keys)) != len(exact_legal_action_keys)
        or any(type(key) is not int or key not in catalogue_keys for key in exact_legal_action_keys)
        or legality_support_source
        not in (
            "PRELOADED_EXACT_LEGALITY_SUPPORT",
            "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
            "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
        )
        or (
            legality_support_source == "PRELOADED_EXACT_LEGALITY_SUPPORT"
            and legality_failure_index is not None
        )
        or (
            legality_support_source != "PRELOADED_EXACT_LEGALITY_SUPPORT"
            and (type(legality_failure_index) is not int or legality_failure_index < 0)
        )
        or maximum_depth <= 0
    ):
        _fail("V113 compiled planner inventory changed")
    initial = _initial_projected_state(candidate, initial_raw_state)
    legal = frozenset(exact_legal_action_keys)
    try:
        plan = _observation_graph_plan(model, rules, initial, legal, candidate)
        source = "OBSERVATION_QUOTIENT_GRAPH"
    except GenericIncrementalAbstractSuccessorV113Error:
        plan = _program_plan(
            candidate,
            catalogue,
            rules,
            initial,
            legal,
            maximum_depth=maximum_depth,
        )
        source = "COMPILED_FACTOR_PROGRAM_FALLBACK"
    actions = plan.get("action_keys")
    if type(actions) is not list or not actions or actions[0] not in legal:
        _fail("V113 compiled planner action path changed")
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(actions[0],),
        partial_proposal=(actions[0],),
        legal_action_keys=exact_legal_action_keys,
    )
    payload = {
        "schema": "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "quotient_graph_id": model["quotient_graph_id"],
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "planning_source": source,
        "initial_action_key": actions[0],
        "projected_action_path": list(actions),
        "abstract_support_branch_evaluations": plan[
            "projected_planning_compute_events"
        ],
        "embedded_projected_plan": copy.deepcopy(plan),
        "exact_legal_action_keys_at_initial_state": list(exact_legal_action_keys),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": shield,
        "initial_illegal_actions_forbidden_in_abstract_search": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "legality_conditioned_quotient_plan_id": hashlib.sha256(
            _V106_PLAN_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "GenericIncrementalAbstractSuccessorV113Error",
    "IncrementalAbstractSuccessorStateV113",
    "advance_incremental_abstract_successor_v113",
    "initialize_incremental_abstract_successor_v113",
    "plan_incremental_abstract_successor_v113",
    "verify_incremental_successor_against_full_rebuild_v113",
)
