"""Compile and incrementally maintain quotient models with generic programs.

V123 retains the audited V113 state carrier and receipt schemas, but replaces
its three-shape projected-edge checker and terminal-rule dispatch.  New edges
are admitted only after recursive V122 interpretation; terminal directions are
derived from an exact affine abstraction of the compiled typed expression.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import generic_incremental_abstract_successor_v113 as v113
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_compiled_factor_planner_v122 import (
    generic_factor_successor_projections_v122,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


_MODEL_DOMAIN = b"acfqp:generic-observation-quotient-graph:v105\x00"


class GenericCompiledQuotientModelV123Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCompiledQuotientModelV123Error(message)


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique = {(row.pre, row.action.key, row.post): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _raw_key(row: FlatRawTransitionV4) -> tuple[tuple[int, ...], int, tuple[int, ...]]:
    return row.pre, row.action.key, row.post


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


def _project_rows_v123(
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
    edges = set()
    terminal = set()
    contexts = set()
    accepting: dict[int, set[int]] = defaultdict(set)
    checks = 0
    for row in aligned_rows:
        pre = tuple(row.pre[target] for target in targets)
        post = tuple(row.post[target] for target in targets)
        predicted = generic_factor_successor_projections_v122(
            candidate, pre, actions[row.action.key]
        )
        checks += len(predicted)
        if post not in predicted:
            _fail("V123 projected observation escaped the generic compiled program")
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


def _add_coefficients(left, right):
    result = dict(left)
    for key, value in right:
        result[key] = result.get(key, 0) + value
    return tuple(sorted((key, value) for key, value in result.items() if value))


def _affine_forms(expression: Any):
    if type(expression) is bool:
        return None
    if type(expression) is int:
        return frozenset(((expression, (), ()),))
    opcode = expression[0]
    if opcode == "E00":
        return frozenset(((0, ((expression[1], 1),), ()),))
    if opcode == "E01":
        return frozenset(((0, (), ((expression[1], 1),)),))
    if opcode == "E05":
        left = _affine_forms(expression[1])
        right = _affine_forms(expression[2])
        if left is None or right is None:
            return None
        return frozenset(
            (
                lc + rc,
                _add_coefficients(ls, rs),
                _add_coefficients(la, ra),
            )
            for lc, ls, la in left
            for rc, rs, ra in right
        )
    if opcode == "E07":
        left = _affine_forms(expression[1])
        right = _affine_forms(expression[2])
        return None if left is None or right is None else left | right
    return None


def _translation_deltas(assignment, actions):
    forms = _affine_forms(assignment["expression"])
    target = assignment["target_column"]
    if forms is None or any(state != ((target, 1),) for _constant, state, _action in forms):
        return None
    return tuple(
        sorted(
            {
                constant
                + sum(coefficient * action.fields[field] for field, coefficient in action_terms)
                for constant, _state, action_terms in forms
                for action in actions
            }
        )
    )


def _terminal_rules_v123(
    candidate: PartialFactorCandidateV15,
    accepting_values: tuple[tuple[int, tuple[int, ...]], ...],
    actions: tuple[FlatRawActionV4, ...],
) -> tuple[dict[str, Any], ...]:
    by_target = dict(accepting_values)
    if not by_target or any(not by_target.get(row["target_column"]) for row in candidate.assignments):
        _fail("V123 partial observations exposed no accepting projection")
    rules = []
    for assignment in candidate.assignments:
        target = assignment["target_column"]
        values = by_target[target]
        deltas = _translation_deltas(assignment, actions)
        if target not in assignment["state_dependencies"] or deltas is None:
            rule = {"kind": "UNCONSTRAINED"}
        elif all(delta == 0 for delta in deltas):
            rule = (
                {"kind": "EQUAL", "value": values[0]}
                if len(values) == 1
                else {"kind": "UNCONSTRAINED"}
            )
        elif all(delta >= 0 for delta in deltas):
            rule = {"kind": "AT_LEAST", "value": min(values)}
        elif all(delta <= 0 for delta in deltas):
            rule = {"kind": "AT_MOST", "value": max(values)}
        else:
            rule = {"kind": "OBSERVED_SET", "values": list(values)}
        rules.append({"target_column": target, **rule})
    return tuple(rules)


def _model_document_v123(
    candidate: PartialFactorCandidateV15,
    raw_keys: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
    contexts: frozenset[tuple[tuple[int, ...], int]],
    edges: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]],
    terminal_memberships: frozenset[tuple[tuple[int, ...], str]],
    checks: int,
) -> dict[str, Any]:
    edge_rows = [
        {"projected_pre": list(pre), "action_key": key, "projected_post": list(post)}
        for pre, key, post in sorted(edges)
    ]
    terminal: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for state, terminal_class in terminal_memberships:
        terminal[state].add(terminal_class)
    terminal_rows = [
        {"projected_state": list(state), "observed_terminal_classes": sorted(classes)}
        for state, classes in sorted(terminal.items())
    ]
    public = candidate.public_document
    targets = [row["target_column"] for row in candidate.assignments]
    payload = {
        "schema": "acfqp.generic_observation_quotient_graph.v105",
        "partial_candidate_id": public["candidate_id"],
        "layout_id": public["layout"]["layout_id"],
        "projected_state_target_columns": targets,
        "quotiented_residual_target_columns": list(public["unknown_residual_target_columns"]),
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
            _MODEL_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def compile_generic_quotient_model_v123(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or type(catalogue) is not tuple
        or not catalogue
    ):
        _fail("V123 quotient compiler inventory changed")
    rows = _deduplicate(observed_rows)
    edges, terminal, contexts, _accepting, checks = _project_rows_v123(
        candidate, rows, catalogue
    )
    return _model_document_v123(
        candidate,
        frozenset(_raw_key(row) for row in rows),
        contexts,
        edges,
        terminal,
        checks,
    )


def _state_payload(model, rules, raw_keys):
    inventory = [
        {"pre": list(pre), "action_key": action, "post": list(post)}
        for pre, action, post in sorted(raw_keys)
    ]
    return {
        "quotient_graph_id": model["quotient_graph_id"],
        "terminal_projection_rule": [dict(row) for row in rules],
        "raw_row_identity_count": len(raw_keys),
        "raw_row_identity_sha256": hashlib.sha256(canonical_json_bytes(inventory)).hexdigest(),
    }


def _verify_state_v123(state, candidate, catalogue):
    if (
        type(state) is not v113.IncrementalAbstractSuccessorStateV113
        or state._issuer is not v113._ISSUER  # noqa: SLF001
        or type(candidate) is not PartialFactorCandidateV15
        or state.candidate_id != candidate.public_document["candidate_id"]
    ):
        _fail("V123 incremental state authority changed")
    model = _model_document_v123(
        candidate,
        state.raw_keys,
        state.contexts,
        state.edges,
        state.terminal_memberships,
        state.projected_program_checks,
    )
    rules = _terminal_rules_v123(candidate, state.accepting_values, _canonical_actions(candidate, catalogue))
    expected_id = hashlib.sha256(
        b"acfqp:generic-incremental-abstract-successor-state:v113\x00"
        + canonical_json_bytes(_state_payload(model, rules, state.raw_keys))
    ).hexdigest()
    if (
        canonical_json_bytes(model) != state.model_bytes
        or canonical_json_bytes(list(rules)) != state.terminal_rules_bytes
        or state.state_id != expected_id
    ):
        _fail("V123 incremental state reconstruction changed")
    return model, rules


def _make_state_v123(
    candidate,
    catalogue,
    *,
    raw_keys,
    contexts,
    edges,
    terminal_memberships,
    accepting_values,
    projected_program_checks,
):
    model = _model_document_v123(
        candidate, raw_keys, contexts, edges, terminal_memberships, projected_program_checks
    )
    rules = _terminal_rules_v123(candidate, accepting_values, _canonical_actions(candidate, catalogue))
    payload = _state_payload(model, rules, raw_keys)
    state = v113.IncrementalAbstractSuccessorStateV113(
        v113._ISSUER,  # noqa: SLF001
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
    _verify_state_v123(state, candidate, catalogue)
    return state


def generic_incremental_runtime_v123() -> SimpleNamespace:
    namespace = dict(v113.__dict__)
    namespace.update(
        _project_rows=_project_rows_v123,
        _terminal_rules=_terminal_rules_v123,
        _model_document=_model_document_v123,
        _verify_state=_verify_state_v123,
        _make_state=_make_state_v123,
        compile_observation_quotient_graph_v105=compile_generic_quotient_model_v123,
    )

    def clone(name):
        source = getattr(v113, name)
        result = FunctionType(
            source.__code__,
            namespace,
            name=source.__name__,
            argdefs=source.__defaults__,
            closure=source.__closure__,
        )
        result.__kwdefaults__ = source.__kwdefaults__
        return result

    return SimpleNamespace(
        initialize=clone("initialize_incremental_abstract_successor_v113"),
        advance=clone("advance_incremental_abstract_successor_v113"),
        verify=clone("verify_incremental_successor_against_full_rebuild_v113"),
        verify_state=_verify_state_v123,
    )


__all__ = (
    "compile_generic_quotient_model_v123",
    "generic_incremental_runtime_v123",
)
