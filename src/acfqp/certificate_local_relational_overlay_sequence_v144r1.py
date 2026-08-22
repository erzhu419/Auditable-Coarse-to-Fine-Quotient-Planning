"""Replan with exact edges acquired only after certificate failure.

The source partial program remains immutable.  Program-compatible local rows
advance the retained V125 model.  A row outside that program is retained as an
exact projected edge in a separate content-addressed overlay; it is never
promoted to global dynamics or safety authority.  Later abstract searches use
the merged graph, while the certificate layer remains the only admission
authority.
"""

from __future__ import annotations

from collections import defaultdict, deque
import copy
from dataclasses import dataclass, field
import hashlib
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v144r1 as domains
from acfqp import generic_compiled_quotient_model_v123 as generic
from acfqp import standalone_generic_model_epoch_v125 as v125
from acfqp import standalone_generic_owned_sequence_v126 as v126
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_compiled_factor_planner_v122 import (
    derive_generic_terminal_rules_v122,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class CertificateLocalRelationalOverlaySequenceV144R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CertificateLocalRelationalOverlaySequenceV144R1Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v144r1(domain, payload)}


def _terminal_class(row: FlatRawTransitionV4) -> str:
    return (
        "ACTIVE"
        if row.legal_after
        else "ACCEPT"
        if row.terminal_acceptance_after is True
        else "REJECT"
    )


def _overlay_row(
    candidate: PartialFactorCandidateV15,
    row: FlatRawTransitionV4,
    catalogue: tuple[Any, ...],
) -> dict[str, Any]:
    aligned, _actions = align_generic_occurrence_v5(
        (row,), catalogue, candidate.layout, canonical_occurrence=0
    )
    current = aligned[0]
    targets = tuple(item["target_column"] for item in candidate.assignments)
    payload = {
        "projected_pre": [current.pre[target] for target in targets],
        "action_key": current.action.key,
        "projected_post": [current.post[target] for target in targets],
        "terminal_class": _terminal_class(current),
        "source_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(row.to_document())
        ).hexdigest(),
        "source_acquired_after_failed_certificate": True,
        "query_local_exact_edge_not_global_dynamics": True,
    }
    return payload


def _partition(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[Any, ...],
) -> tuple[tuple[FlatRawTransitionV4, ...], tuple[dict[str, Any], ...]]:
    compatible = []
    overlay = []
    for row in rows:
        try:
            generic._project_rows_v123(candidate, (row,), catalogue)  # noqa: SLF001
        except generic.GenericCompiledQuotientModelV123Error:
            overlay.append(_overlay_row(candidate, row, catalogue))
        else:
            compatible.append(row)
    return tuple(compatible), tuple(overlay)


def _merge_model(
    base: Mapping[str, Any], overlay_rows: tuple[Mapping[str, Any], ...]
) -> dict[str, Any]:
    edges = {
        (
            tuple(row["projected_pre"]),
            row["action_key"],
            tuple(row["projected_post"]),
        )
        for row in base["projected_edge_rows"]
    }
    terminals: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for row in base["projected_terminal_rows"]:
        terminals[tuple(row["projected_state"])].update(
            row["observed_terminal_classes"]
        )
    overlay_edge_keys = set()
    for row in overlay_rows:
        key = (
            tuple(row["projected_pre"]),
            row["action_key"],
            tuple(row["projected_post"]),
        )
        edges.add(key)
        overlay_edge_keys.add(key)
        terminals[key[2]].add(row["terminal_class"])
    edge_documents = [
        {
            "projected_pre": list(pre),
            "action_key": action,
            "projected_post": list(post),
        }
        for pre, action, post in sorted(edges)
    ]
    terminal_documents = [
        {
            "projected_state": list(state),
            "observed_terminal_classes": sorted(classes),
        }
        for state, classes in sorted(terminals.items())
    ]
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_quotient_graph.v144r1",
        "base_quotient_graph_id": base["quotient_graph_id"],
        "partial_candidate_id": base["partial_candidate_id"],
        "layout_id": base["layout_id"],
        "projected_state_target_columns": list(
            base["projected_state_target_columns"]
        ),
        "quotiented_residual_target_columns": list(
            base["quotiented_residual_target_columns"]
        ),
        "projected_state_width": base["projected_state_width"],
        "projected_edge_rows": edge_documents,
        "projected_edge_count": len(edge_documents),
        "projected_terminal_rows": terminal_documents,
        "projected_terminal_state_count": len(terminal_documents),
        "source_ground_support_label_count": base[
            "source_ground_support_label_count"
        ]
        + len(overlay_rows),
        "source_raw_transition_row_count": base["source_raw_transition_row_count"]
        + len(overlay_rows),
        "source_projected_edge_program_checks": base[
            "source_projected_edge_program_checks"
        ],
        "query_local_exact_overlay_edge_count": len(overlay_edge_keys),
        "query_local_exact_overlay_rows": [copy.deepcopy(dict(row)) for row in overlay_rows],
        "all_overlay_rows_acquired_after_failed_certificate": all(
            row["source_acquired_after_failed_certificate"] is True
            for row in overlay_rows
        ),
        "compiled_factor_program_checked_each_abstract_edge": not overlay_edge_keys,
        "uncompiled_edges_are_query_local_exact_observations": bool(
            overlay_edge_keys
        ),
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_overlay_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_claimed": False,
    }
    return _identifier(
        domains.CONSTRUCTION_K7_RELATIONAL_OVERLAY_MODEL_V144R1_DOMAIN,
        payload,
        "quotient_graph_id",
    )


def _rules(candidate: PartialFactorCandidateV15, model: Mapping[str, Any]):
    return derive_generic_terminal_rules_v122(
        candidate, model["projected_edge_rows"], model["projected_terminal_rows"]
    )


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationalOverlayModelStateV144R1:
    _issuer: object = field(repr=False, compare=False)
    base_state: v125.StandaloneGenericModelEpochStateV125
    overlay_rows_bytes: bytes = field(repr=False)
    model_bytes: bytes = field(repr=False)
    terminal_rules_bytes: bytes = field(repr=False)
    state_id: str

    @property
    def overlay_rows(self) -> tuple[dict[str, Any], ...]:
        rows = loads_canonical_json(self.overlay_rows_bytes)
        return tuple(rows)

    @property
    def model(self) -> dict[str, Any]:
        return loads_canonical_json(self.model_bytes)

    @property
    def terminal_rules(self) -> tuple[dict[str, Any], ...]:
        return tuple(loads_canonical_json(self.terminal_rules_bytes))


def _make_state(
    base_state: v125.StandaloneGenericModelEpochStateV125,
    overlay_rows: tuple[Mapping[str, Any], ...],
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[Any, ...],
) -> RelationalOverlayModelStateV144R1:
    base, _base_rules = v125.verify_standalone_generic_model_state_v125(
        base_state, candidate, catalogue
    )
    unique = {
        (
            tuple(row["projected_pre"]),
            row["action_key"],
            tuple(row["projected_post"]),
            row["terminal_class"],
        ): copy.deepcopy(dict(row))
        for row in overlay_rows
    }
    frozen = tuple(unique[key] for key in sorted(unique))
    model = _merge_model(base, frozen)
    rules = _rules(candidate, model)
    payload = {
        "base_successor_state_id": base_state.state_id,
        "relational_overlay_model_id": model["quotient_graph_id"],
        "overlay_rows": list(frozen),
        "terminal_projection_rule": [dict(row) for row in rules],
    }
    state = RelationalOverlayModelStateV144R1(
        _ISSUER,
        base_state,
        canonical_json_bytes(list(frozen)),
        canonical_json_bytes(model),
        canonical_json_bytes(list(rules)),
        domains.extension_content_id_v144r1(
            domains.CONSTRUCTION_K7_RELATIONAL_OVERLAY_STATE_V144R1_DOMAIN,
            payload,
        ),
    )
    _verify_state(state, candidate, catalogue)
    return state


def _verify_state(state, candidate, catalogue):
    if type(state) is not RelationalOverlayModelStateV144R1 or state._issuer is not _ISSUER:
        _fail("V144R1 relational-overlay state authority changed")
    expected = _make_state_unchecked(
        state.base_state, state.overlay_rows, candidate, catalogue
    )
    if (
        state.model_bytes != expected.model_bytes
        or state.terminal_rules_bytes != expected.terminal_rules_bytes
        or state.overlay_rows_bytes != expected.overlay_rows_bytes
        or state.state_id != expected.state_id
    ):
        _fail("V144R1 relational-overlay state reconstruction changed")
    return state.model, state.terminal_rules


def _make_state_unchecked(base_state, overlay_rows, candidate, catalogue):
    base, _ = v125.verify_standalone_generic_model_state_v125(
        base_state, candidate, catalogue
    )
    unique = {
        (
            tuple(row["projected_pre"]),
            row["action_key"],
            tuple(row["projected_post"]),
            row["terminal_class"],
        ): copy.deepcopy(dict(row))
        for row in overlay_rows
    }
    frozen = tuple(unique[key] for key in sorted(unique))
    model = _merge_model(base, frozen)
    rules = _rules(candidate, model)
    payload = {
        "base_successor_state_id": base_state.state_id,
        "relational_overlay_model_id": model["quotient_graph_id"],
        "overlay_rows": list(frozen),
        "terminal_projection_rule": [dict(row) for row in rules],
    }
    return RelationalOverlayModelStateV144R1(
        _ISSUER,
        base_state,
        canonical_json_bytes(list(frozen)),
        canonical_json_bytes(model),
        canonical_json_bytes(list(rules)),
        domains.extension_content_id_v144r1(
            domains.CONSTRUCTION_K7_RELATIONAL_OVERLAY_STATE_V144R1_DOMAIN,
            payload,
        ),
    )


def _initialize(candidate, observed_rows, catalogue):
    base_state, base_receipt = v125.initialize_standalone_generic_model_v125(
        candidate, observed_rows, catalogue
    )
    state = _make_state(base_state, (), candidate, catalogue)
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_bootstrap.v144r1",
        "successor_state_id": state.state_id,
        "relational_overlay_model_id": state.model["quotient_graph_id"],
        "base_bootstrap_receipt": base_receipt,
        "bootstrap_compilation_events": base_receipt[
            "bootstrap_compilation_events"
        ],
        "query_local_overlay_row_count": 0,
        "acquisition_rows_all_checked_by_compiled_program": True,
        "model_used_as_safety_authority": False,
    }
    return state, _identifier(
        domains.CONSTRUCTION_K7_RELATIONAL_OVERLAY_BOOTSTRAP_V144R1_DOMAIN,
        payload,
        "bootstrap_receipt_id",
    )


def _advance(state, candidate, new_rows, catalogue):
    previous_model, _ = _verify_state(state, candidate, catalogue)
    if type(new_rows) is not tuple:
        _fail("V144R1 overlay delta inventory changed")
    compatible, overlay = _partition(candidate, new_rows, catalogue)
    next_base, base_update = v125.advance_standalone_generic_model_v125(
        state.base_state, candidate, compatible, catalogue
    )
    next_state = _make_state(
        next_base, (*state.overlay_rows, *overlay), candidate, catalogue
    )
    overlay_insertions = len(next_state.overlay_rows) - len(state.overlay_rows)
    events = base_update["incremental_compilation_events"] + len(overlay) + overlay_insertions
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_update.v144r1",
        "previous_successor_state_id": state.state_id,
        "current_successor_state_id": next_state.state_id,
        "previous_generic_model_epoch_id": previous_model["quotient_graph_id"],
        "current_generic_model_epoch_id": next_state.model["quotient_graph_id"],
        "base_update_receipt": base_update,
        "delta_input_raw_row_count": len(new_rows),
        "delta_program_compatible_row_count": len(compatible),
        "delta_query_local_exact_overlay_row_count": len(overlay),
        "delta_query_local_exact_overlay_insertions": overlay_insertions,
        "incremental_compilation_events": events,
        "model_identity_changed": previous_model["quotient_graph_id"]
        != next_state.model["quotient_graph_id"],
        "all_overlay_rows_followed_failed_certificates": all(
            row["source_acquired_after_failed_certificate"] is True for row in overlay
        ),
        "source_partial_program_mutated": False,
        "overlay_promoted_to_global_dynamics": False,
        "model_used_as_safety_authority": False,
    }
    return next_state, _identifier(
        domains.CONSTRUCTION_K7_RELATIONAL_OVERLAY_UPDATE_V144R1_DOMAIN,
        payload,
        "update_receipt_id",
    )


def _full_rebuild(state, candidate, all_rows, catalogue, *, update_receipt):
    _verify_state(state, candidate, catalogue)
    compatible, overlay = _partition(candidate, all_rows, catalogue)
    base_state, _bootstrap = v125.initialize_standalone_generic_model_v125(
        candidate, compatible, catalogue
    )
    expected = _make_state(base_state, overlay, candidate, catalogue)
    if (
        expected.model_bytes != state.model_bytes
        or expected.terminal_rules_bytes != state.terminal_rules_bytes
        or expected.overlay_rows_bytes != state.overlay_rows_bytes
    ):
        _fail("V144R1 incremental overlay differs from full rebuild")
    full_events = len(all_rows) + state.model["source_projected_edge_program_checks"] + state.model["projected_edge_count"] + state.model["projected_terminal_state_count"]
    incremental = full_events if update_receipt is None else update_receipt["incremental_compilation_events"]
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_full_rebuild_match.v144r1",
        "successor_state_id": state.state_id,
        "generic_model_epoch_id": state.model["quotient_graph_id"],
        "update_receipt_id": None if update_receipt is None else update_receipt["update_receipt_id"],
        "incremental_compilation_events": incremental,
        "matched_full_rebuild_compilation_events": full_events,
        "compilation_events_avoided_against_full_rebuild": full_events - incremental,
        "program_compatible_row_count": len(compatible),
        "query_local_exact_overlay_row_count": len(overlay),
        "model_bytes_exactly_equal_full_generic_rebuild": True,
        "model_bytes_exactly_equal_full_v105_rebuild": True,
        "legacy_named_v105_match_field_is_sequence_compatibility_alias": True,
        "terminal_projection_rule_exactly_equal_full_rebuild": True,
        "raw_row_identity_inventory_exactly_equal_full_rebuild": True,
        "query_local_overlay_inventory_exactly_equal_full_rebuild": True,
        "matched_control_compute_not_charged_to_incremental_arm": True,
        "model_used_as_safety_authority": False,
    }
    return _identifier(
        domains.CONSTRUCTION_K7_RELATIONAL_OVERLAY_MATCH_V144R1_DOMAIN,
        payload,
        "match_receipt_id",
    )


def _terminal_match(state, rules):
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


def _observation_graph_plan(model, rules, initial, legal, candidate):
    adjacency = defaultdict(set)
    for row in model["projected_edge_rows"]:
        adjacency[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    queue = deque((initial,))
    predecessor = {initial: None}
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
        raise v126.GenericIncrementalAbstractSuccessorV113Error(
            "V144R1 merged observation graph found no projected continuation"
        )
    actions = []
    cursor = goal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        actions.append(key)
        cursor = parent
    actions.reverse()
    return {
        "schema": "acfqp.certificate_local_relational_overlay_graph_plan.v144r1",
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
        "query_local_exact_overlay_edge_count": model[
            "query_local_exact_overlay_edge_count"
        ],
        "terminal_projection_rule": [dict(row) for row in rules],
        "action_keys": actions,
        "projected_planning_compute_events": evaluations,
        "compiled_factor_program_checked_each_abstract_edge": model[
            "compiled_factor_program_checked_each_abstract_edge"
        ],
        "uncompiled_edges_are_query_local_exact_observations": model[
            "uncompiled_edges_are_query_local_exact_observations"
        ],
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_overlay_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }


def _clone(function, namespace):
    clone = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


_PLAN_GLOBALS = dict(v126.__dict__)
_PLAN_GLOBALS.update(
    verify_standalone_generic_model_state_v125=_verify_state,
    _observation_graph_plan=_observation_graph_plan,
    _fail=_fail,
)
_PLAN = _clone(v126._plan_with_branch_cache_v126, _PLAN_GLOBALS)  # noqa: SLF001
_ORDERER_GLOBALS = dict(v126.__dict__)
_ORDERER_GLOBALS.update(_plan_with_branch_cache_v126=_PLAN, _fail=_fail)
_ORDERER = _clone(v126._owned_orderer, _ORDERER_GLOBALS)  # noqa: SLF001
_RUN_GLOBALS = dict(v126.__dict__)
_RUN_GLOBALS.update(
    initialize_standalone_generic_model_v125=_initialize,
    advance_standalone_generic_model_v125=_advance,
    verify_standalone_generic_model_full_rebuild_v125=_full_rebuild,
    _owned_orderer=_ORDERER,
    _fail=_fail,
)
_RUN = _clone(v126.run_standalone_generic_owned_sequence_v126, _RUN_GLOBALS)


def run_certificate_local_relational_overlay_sequence_v144r1(*args, **kwargs):
    historical = _RUN(*args, **kwargs)
    payload = {
        **{key: value for key, value in historical.items() if key not in {"schema", "sequence_id"}},
        "schema": "acfqp.certificate_local_relational_overlay_owned_sequence.v144r1",
        "query_local_relational_overlay_model_present": True,
        "source_partial_program_mutated_after_certificate_failure": False,
        "every_uncompiled_edge_is_certificate_local": all(
            model["all_overlay_rows_acquired_after_failed_certificate"] is True
            for model in historical["quotient_models_after_each_episode"]
        ),
        "total_query_local_exact_overlay_edge_count": max(
            model["query_local_exact_overlay_edge_count"]
            for model in historical["quotient_models_after_each_episode"]
        ),
        "overlay_promoted_to_global_dynamics": False,
        "query_local_overlay_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
    }
    return _identifier(
        domains.CONSTRUCTION_K7_RELATIONAL_OVERLAY_SEQUENCE_V144R1_DOMAIN,
        payload,
        "sequence_id",
    )


__all__ = ("run_certificate_local_relational_overlay_sequence_v144r1",)
