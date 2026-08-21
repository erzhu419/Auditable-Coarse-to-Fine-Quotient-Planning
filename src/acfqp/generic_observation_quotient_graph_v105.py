"""Observation-derived quotient graph used only to order certified actions.

The graph contains projected states and action-labelled projected edges.  Raw
residual coordinates are deliberately quotiented out rather than filled with
an invented completion.  Every edge is checked against the compiled V15
factor program before it enters the graph.  The graph is fallible and never
discharges legality, transition-support, or terminal certificates.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    partial_factor_successor_projections_v15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.phase3e_ids import canonical_json_bytes


_MODEL_DOMAIN = b"acfqp:generic-observation-quotient-graph:v105\x00"
_PLAN_DOMAIN = b"acfqp:generic-observation-quotient-plan:v105\x00"


class GenericObservationQuotientGraphV105Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericObservationQuotientGraphV105Error(message)


def _identifier(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique = {}
    for row in rows:
        unique[(row.pre, row.action.key, row.post)] = row
    return tuple(unique[key] for key in sorted(unique))


def _projected_inventory(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    actions = {action.key: action for action in aligned_catalogue}
    targets = tuple(row["target_column"] for row in candidate.assignments)
    edges = set()
    terminal: dict[tuple[int, ...], set[str]] = {}
    checks = 0
    for row in aligned_rows:
        pre = tuple(row.pre[target] for target in targets)
        post = tuple(row.post[target] for target in targets)
        predicted = partial_factor_successor_projections_v15(
            candidate, pre, actions[row.action.key]
        )
        checks += len(predicted)
        if post not in predicted:
            _fail("V105 projected observation escaped the compiled factor program")
        edges.add((pre, row.action.key, post))
        terminal.setdefault(post, set()).add(
            "ACTIVE"
            if row.legal_after
            else "ACCEPT"
            if row.terminal_acceptance_after is True
            else "REJECT"
        )
    edge_rows = [
        {
            "projected_pre": list(pre),
            "action_key": key,
            "projected_post": list(post),
        }
        for pre, key, post in sorted(edges)
    ]
    terminal_rows = [
        {
            "projected_state": list(state),
            "observed_terminal_classes": sorted(classes),
        }
        for state, classes in sorted(terminal.items())
    ]
    return edge_rows, terminal_rows, checks


def compile_observation_quotient_graph_v105(
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
        _fail("V105 quotient compiler inventory changed")
    rows = _deduplicate(observed_rows)
    edge_rows, terminal_rows, checks = _projected_inventory(
        candidate, rows, catalogue
    )
    document = candidate.public_document
    targets = [row["target_column"] for row in candidate.assignments]
    residual = document["unknown_residual_target_columns"]
    contexts = {(row.pre, row.action.key) for row in rows}
    payload = {
        "schema": "acfqp.generic_observation_quotient_graph.v105",
        "partial_candidate_id": document["candidate_id"],
        "layout_id": document["layout"]["layout_id"],
        "projected_state_target_columns": targets,
        "quotiented_residual_target_columns": list(residual),
        "projected_state_width": len(targets),
        "projected_edge_rows": edge_rows,
        "projected_edge_count": len(edge_rows),
        "projected_terminal_rows": terminal_rows,
        "projected_terminal_state_count": len(terminal_rows),
        "source_ground_support_label_count": len(contexts),
        "source_raw_transition_row_count": len(rows),
        "source_projected_edge_program_checks": checks,
        "source_projected_rows_sha256": hashlib.sha256(
            canonical_json_bytes(
                {
                    "edges": edge_rows,
                    "terminal": terminal_rows,
                }
            )
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
        "quotient_graph_id": _identifier(_MODEL_DOMAIN, payload),
    }


def verify_observation_quotient_graph_v105(
    model: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    expected = compile_observation_quotient_graph_v105(
        candidate, observed_rows, catalogue
    )
    if type(model) is not dict or model != expected:
        _fail("V105 quotient graph differs from exact reconstruction")
    return copy.deepcopy(expected)


def plan_observation_quotient_graph_v105(
    model: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    *,
    maximum_depth: int,
) -> dict[str, Any]:
    verified = verify_observation_quotient_graph_v105(
        model, candidate, observed_rows, catalogue
    )
    if type(initial_raw_state) is not tuple or maximum_depth <= 0:
        _fail("V105 quotient planner inventory changed")
    try:
        plan = plan_partial_factor_observation_graph_v15(
            candidate, _deduplicate(observed_rows), catalogue, initial_raw_state
        )
        source = "OBSERVATION_QUOTIENT_GRAPH"
    except Exception as first_error:
        if not first_error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        try:
            plan = plan_partial_factor_program_v15(
                candidate,
                _deduplicate(observed_rows),
                catalogue,
                initial_raw_state,
                maximum_depth=maximum_depth,
            )
            source = "COMPILED_FACTOR_PROGRAM_FALLBACK"
        except Exception as second_error:
            if not second_error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            _fail("V105 quotient model found no projected continuation")
    actions = plan.get("action_keys")
    if type(actions) is not list or not actions or any(type(key) is not int for key in actions):
        _fail("V105 quotient plan action path changed")
    payload = {
        "schema": "acfqp.generic_observation_quotient_plan.v105",
        "quotient_graph_id": verified["quotient_graph_id"],
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "planning_source": source,
        "initial_action_key": actions[0],
        "projected_action_path": list(actions),
        "abstract_support_branch_evaluations": plan.get(
            "projected_planning_compute_events", 0
        ),
        "embedded_projected_plan": copy.deepcopy(plan),
        "residual_coordinates_read_during_search": False,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "quotient_plan_id": _identifier(_PLAN_DOMAIN, payload),
    }


__all__ = (
    "GenericObservationQuotientGraphV105Error",
    "compile_observation_quotient_graph_v105",
    "plan_observation_quotient_graph_v105",
    "verify_observation_quotient_graph_v105",
)
