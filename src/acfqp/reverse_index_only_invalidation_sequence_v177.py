"""Select invalidations from certificate-maintained reverse indices only."""

from __future__ import annotations

import contextvars
import copy
from types import FunctionType, SimpleNamespace
from typing import Any, NoReturn

from acfqp import certified_memoized_planner_sequence_v154 as v154
from acfqp import construction_k7_domain_registry_extension_v177 as domains
from acfqp import generic_identity_short_circuited_epoch_sequence_v111 as v111
from acfqp import receipt_driven_minimal_invalidation_sequence_v174 as v174
from acfqp import certificate_delta_only_invalidation_sequence_v176 as v176


class ReverseIndexOnlyInvalidationSequenceV177Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ReverseIndexOnlyInvalidationSequenceV177Error(message)


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


_DELTA_ACTIVE: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar("v177_reverse_index_delta_lifecycle", default=None)
)


def _advance_with_certificate_delta(state, candidate, new_rows, catalogue):
    lifecycle = _DELTA_ACTIVE.get()
    if lifecycle is None or lifecycle.get("pending_delta") is not None:
        _fail("V177 incremental update lacks a clean owner-bound delta lifecycle")
    temporary = {
        "certificate_deltas": [],
        "transition_joins": [],
        "pending_delta": None,
    }
    token = v176._DELTA_ACTIVE.set(temporary)  # noqa: SLF001
    try:
        next_state, update = v176._advance_with_certificate_delta(  # noqa: SLF001
            state, candidate, new_rows, catalogue
        )
    finally:
        v176._DELTA_ACTIVE.reset(token)  # noqa: SLF001
    source = temporary["pending_delta"]
    if source is None or len(temporary["certificate_deltas"]) != 1:
        _fail("V177 source delta did not close before translation")
    payload = {
        **{
            key: value
            for key, value in source.items()
            if key not in {"schema", "certificate_delta_receipt_id"}
        },
        "schema": "acfqp.certificate_local_model_delta.v177",
    }
    receipt = {
        **payload,
        "certificate_delta_receipt_id": domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_CERTIFICATE_DELTA_V177_DOMAIN, payload
        ),
    }
    lifecycle["certificate_deltas"].append(copy.deepcopy(receipt))
    lifecycle["pending_delta"] = copy.deepcopy(receipt)
    return next_state, update


def _reverse_index_transition(
    *,
    previous_model,
    current_model,
    previous_rules,
    current_rules,
    cache,
    entries,
    reverse_index,
):
    receipt_lifecycle = v174._ACTIVE.get()  # noqa: SLF001
    delta_lifecycle = _DELTA_ACTIVE.get()
    if receipt_lifecycle is None or delta_lifecycle is None:
        _fail("V177 transition lacks its owner-bound lifecycles")
    delta = delta_lifecycle.get("pending_delta")
    if delta is None or not (
        delta["previous_quotient_graph_id"] == previous_model["quotient_graph_id"]
        and delta["current_quotient_graph_id"] == current_model["quotient_graph_id"]
        and delta["previous_terminal_projection_rule"]
        == [dict(row) for row in previous_rules]
        and delta["current_terminal_projection_rule"]
        == [dict(row) for row in current_rules]
    ):
        _fail("V177 certificate delta/model epoch join changed")
    changed = tuple(tuple(row) for row in delta["changed_projected_states"])
    rules_changed = list(previous_rules) != list(current_rules)
    all_ids = set(entries)
    if rules_changed:
        invalidated = set(all_ids)
    else:
        invalidated = set()
        for state in changed:
            invalidated.update(reverse_index.get(state, ()))
    if not invalidated <= all_ids:
        _fail("V177 reverse index references a non-live cache entry")
    retained = all_ids - invalidated
    affected_receipts = sorted(
        event["receipt"]["online_plan_issuance_receipt_id"]
        for event in receipt_lifecycle["events"]
        if event["dependency"].get("quotient_dependency_receipt_id") in invalidated
    )
    retained_receipts = sorted(
        event["receipt"]["online_plan_issuance_receipt_id"]
        for event in receipt_lifecycle["events"]
        if event["dependency"].get("quotient_dependency_receipt_id") in retained
    )
    payload = {
        "schema": "acfqp.reverse_index_model_epoch_transition.v177",
        "certificate_delta_receipt_id": delta["certificate_delta_receipt_id"],
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "quotient_graph_identity_equal": previous_model["quotient_graph_id"]
        == current_model["quotient_graph_id"],
        "identity_short_circuit_applied": previous_model["quotient_graph_id"]
        == current_model["quotient_graph_id"]
        and not rules_changed,
        "previous_terminal_projection_rule": [dict(row) for row in previous_rules],
        "current_terminal_projection_rule": [dict(row) for row in current_rules],
        "terminal_projection_rule_changed": rules_changed,
        "delta_changed_projected_states": copy.deepcopy(
            delta["changed_projected_states"]
        ),
        "delta_inserted_projected_edge_rows": copy.deepcopy(
            delta["inserted_projected_edge_rows"]
        ),
        "cache_entry_ids_before_transition": sorted(all_ids),
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "invalidated_online_plan_issuance_receipt_ids": affected_receipts,
        "retained_online_plan_issuance_receipt_ids": retained_receipts,
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": 0,
        "production_full_graph_diff_checks": 0,
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_live_cache_identity_enumeration_count": len(all_ids),
        "production_prior_receipt_event_scan_count": len(
            receipt_lifecycle["events"]
        ),
        "retained_authorization_metadata_updates": len(retained),
        "reverse_dependency_index_lookups": len(changed),
        "receipt_reverse_index_drove_invalidation": True,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "producer_free_dependency_and_full_graph_controls_required": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    transition = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_EPOCH_TRANSITION_V177_DOMAIN, payload
        ),
    }
    for key in tuple(cache):
        cache[key] = [
            entry
            for entry in cache[key]
            if entry["dependency"]["dependency_receipt_id"] not in invalidated
        ]
        if not cache[key]:
            del cache[key]
    for identity in invalidated:
        entry = entries.pop(identity)
        for row in entry["dependency"]["ordered_bfs_dependency_rows"]:
            state = tuple(row["projected_state"])
            reverse_index[state].discard(identity)
            if not reverse_index[state]:
                del reverse_index[state]
    for identity in retained:
        entry = entries[identity]
        entry["authorized_quotient_graph_id"] = current_model["quotient_graph_id"]
        entry["epoch_authorization_chain"].append(copy.deepcopy(transition))
    join_payload = {
        "schema": "acfqp.certificate_delta_transition_join.v177",
        "join_ordinal": len(delta_lifecycle["transition_joins"]),
        "certificate_delta_receipt_id": delta["certificate_delta_receipt_id"],
        "epoch_transition_receipt_id": transition["epoch_transition_receipt_id"],
        "delta_changed_projected_states": copy.deepcopy(
            delta["changed_projected_states"]
        ),
        "delta_issued_before_transition_decision": True,
        "delta_frontier_exactly_drives_transition": True,
        "production_full_graph_control_absent": True,
        "production_live_dependency_projection_scan_absent": True,
        "join_is_cache_maintenance_not_safety_authority": True,
    }
    join = {
        **join_payload,
        "delta_transition_join_id": domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_DELTA_TRANSITION_JOIN_V177_DOMAIN,
            join_payload,
        ),
    }
    delta_lifecycle["transition_joins"].append(join)
    delta_lifecycle["pending_delta"] = None
    receipt_lifecycle["epoch_transitions"].append(copy.deepcopy(transition))
    return transition


_V111_PROXY = SimpleNamespace(**v111.__dict__)
_V111_PROXY._identity_short_circuited_transition = _reverse_index_transition
_RUN_GLOBALS = dict(v154._RUN.__globals__)  # noqa: SLF001
_RUN_GLOBALS.update(
    _owned_orderer=v174._online_orderer,  # noqa: SLF001
    advance_standalone_generic_model_v125=_advance_with_certificate_delta,
    v111=_V111_PROXY,
)
_DELTA_RUN = _clone(v154._RUN, _RUN_GLOBALS)  # noqa: SLF001
_V154_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v154=domains.extension_content_id_v177,
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V177_DOMAIN,
)
_V154_GLOBALS = dict(v154.__dict__)
_V154_GLOBALS.update(_RUN=_DELTA_RUN, domains=_V154_DOMAIN_PROXY)
_DELTA_V154 = _clone(v154.run_certified_memoized_planner_sequence_v154, _V154_GLOBALS)
_V174_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v174=domains.extension_content_id_v177,
    CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V177_DOMAIN,
)
_V174_GLOBALS = dict(
    v174.run_receipt_driven_minimal_invalidation_sequence_v174.__globals__
)
_V174_GLOBALS.update(_RECEIPT_V154=_DELTA_V154, domains=_V174_DOMAIN_PROXY)
_DELTA_V174_SHAPE = _clone(
    v174.run_receipt_driven_minimal_invalidation_sequence_v174,
    _V174_GLOBALS,
)


def run_reverse_index_only_invalidation_sequence_v177(*args, **kwargs):
    lifecycle = {
        "certificate_deltas": [],
        "transition_joins": [],
        "pending_delta": None,
    }
    token = _DELTA_ACTIVE.set(lifecycle)
    try:
        historical = _DELTA_V174_SHAPE(*args, **kwargs)
    finally:
        _DELTA_ACTIVE.reset(token)
    deltas = lifecycle["certificate_deltas"]
    joins = lifecycle["transition_joins"]
    transitions = historical["receipt_driven_model_epoch_transition_receipts"]
    if not (
        len(deltas) == len(historical["episodes"])
        and len(joins) == len(transitions) == len(deltas) - 1
        and lifecycle["pending_delta"] == deltas[-1]
        and all(
            join["certificate_delta_receipt_id"]
            == deltas[index]["certificate_delta_receipt_id"]
            and join["epoch_transition_receipt_id"]
            == transitions[index]["epoch_transition_receipt_id"]
            for index, join in enumerate(joins)
        )
    ):
        _fail("V177 reverse-index lifecycle escaped stored evidence")
    decision_compute = sum(
        deltas[index]["delta_derivation_compute_events"]
        + transitions[index]["reverse_dependency_index_lookups"]
        for index in range(len(joins))
    )
    payload = {
        **{
            key: value
            for key, value in historical.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.reverse_index_only_invalidation_sequence.v177",
        "source_v174_shape_sequence_id": historical["sequence_id"],
        "certificate_local_model_delta_receipts": deltas,
        "certificate_local_model_delta_receipt_count": len(deltas),
        "delta_transition_joins": joins,
        "delta_transition_join_count": len(joins),
        "terminal_delta_not_consumed_because_no_later_planning_epoch": deltas[-1][
            "certificate_delta_receipt_id"
        ],
        "reverse_index_invalidation_decision_compute_events": decision_compute,
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "production_full_graph_diff_checks": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_prior_receipt_event_scan_count": sum(
            row["production_prior_receipt_event_scan_count"] for row in transitions
        ),
        "retained_authorization_metadata_update_count": sum(
            row["retained_authorization_metadata_updates"] for row in transitions
        ),
        "producer_free_dependency_and_full_graph_controls_required": True,
        "certificate_reverse_index_drives_minimal_invalidation": True,
        "receipt_dependency_lifecycle_changes_selected_action_order": False,
        "receipt_dependency_lifecycle_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_SEQUENCE_V177_DOMAIN, payload
        ),
    }


__all__ = ("run_reverse_index_only_invalidation_sequence_v177",)
