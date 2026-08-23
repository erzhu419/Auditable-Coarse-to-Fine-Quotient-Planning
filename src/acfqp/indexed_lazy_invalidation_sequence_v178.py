"""Use issuance indices and lazy epoch catch-up for receipt-driven reuse.

V177 removed full graph and live dependency-projection scans from the model
epoch decision.  V178 removes the remaining historical issuance-event scan and
the eager rewrite of every retained graph-cache entry.  Transitions append one
immutable epoch receipt to an owner-bound ledger.  A retained entry consumes
only the missing suffix of that ledger immediately before an actual cache hit.

All receipts remain ordering/cache-maintenance evidence.  Query-local exact
support remains the only safety authority.
"""

from __future__ import annotations

import contextvars
import copy
from types import FunctionType, SimpleNamespace
from typing import Any, NoReturn

from acfqp import certified_memoized_planner_sequence_v154 as v154
from acfqp import construction_k7_domain_registry_extension_v178 as domains
from acfqp import generic_dependency_revalidated_quotient_sequence_v109 as v109
from acfqp import generic_identity_short_circuited_epoch_sequence_v111 as v111
from acfqp import online_typed_plan_receipt_sequence_v172 as v172
from acfqp import receipt_driven_minimal_invalidation_sequence_v174 as v174
from acfqp import certificate_delta_only_invalidation_sequence_v176 as v176
from acfqp.phase3e_ids import canonical_json_bytes


class IndexedLazyInvalidationSequenceV178Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise IndexedLazyInvalidationSequenceV178Error(message)


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
    contextvars.ContextVar("v178_indexed_lazy_delta_lifecycle", default=None)
)
_MAINTENANCE_ACTIVE: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar("v178_indexed_lazy_maintenance", default=None)
)


def _maintenance(lifecycle: dict[str, Any]) -> dict[str, Any]:
    active = _MAINTENANCE_ACTIVE.get()
    if active is None:
        _fail("V178 indexed maintenance has no owner-bound lifecycle")
    stored = lifecycle.setdefault("indexed_lazy_maintenance", active)
    if stored is not active:
        _fail("V178 indexed maintenance ownership changed")
    return active


def _advance_with_certificate_delta(state, candidate, new_rows, catalogue):
    lifecycle = _DELTA_ACTIVE.get()
    if lifecycle is None or lifecycle.get("pending_delta") is not None:
        _fail("V178 incremental update lacks a clean owner-bound delta lifecycle")
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
        _fail("V178 source delta did not close before translation")
    payload = {
        **{
            key: value
            for key, value in source.items()
            if key not in {"schema", "certificate_delta_receipt_id"}
        },
        "schema": "acfqp.certificate_local_model_delta.v178",
    }
    receipt = {
        **payload,
        "certificate_delta_receipt_id": domains.extension_content_id_v178(
            domains.CONSTRUCTION_K7_CERTIFICATE_DELTA_V178_DOMAIN, payload
        ),
    }
    lifecycle["certificate_deltas"].append(copy.deepcopy(receipt))
    lifecycle["pending_delta"] = copy.deepcopy(receipt)
    return next_state, update


def _indexed_program_invalidation(state, stats, lifecycle) -> None:
    prior_state = stats.get("_program_cache_successor_state_id")
    if prior_state is None or prior_state == state.state_id:
        return
    maintenance = _maintenance(lifecycle)
    program_cache = stats.setdefault("_program_cache", {})
    branch_cache = stats.setdefault("_program_branch_cache", {})
    source_plan_ids = sorted(
        v172._plan_id(entry["source_plan"])  # noqa: SLF001
        for entry in program_cache.values()
    )
    affected: set[str] = set()
    for source_plan_id in source_plan_ids:
        maintenance["program_receipt_index_lookups"] += 1
        affected.update(
            maintenance["program_receipts_by_state_and_plan"].get(
                (prior_state, source_plan_id), ()
            )
        )
    if source_plan_ids and not affected:
        _fail("V178 compiled cache invalidation lacks indexed prior receipt")
    payload = {
        "schema": "acfqp.indexed_program_cache_invalidation.v178",
        "previous_successor_state_id": prior_state,
        "current_successor_state_id": state.state_id,
        "compiled_program_cache_entry_count_before": len(program_cache),
        "invalidated_source_plan_ids": source_plan_ids,
        "authorizing_online_plan_issuance_receipt_ids": sorted(affected),
        "program_cache_entry_count_after": 0,
        "production_prior_receipt_event_scan_count": 0,
        "prior_receipt_reverse_index_lookups": len(source_plan_ids),
        "exact_declared_successor_state_changed": True,
        "receipt_dependency_projection_drove_invalidation": True,
        "invalidation_is_cache_maintenance_not_safety_authority": True,
    }
    receipt = {
        **payload,
        "program_invalidation_receipt_id": domains.extension_content_id_v178(
            domains.CONSTRUCTION_K7_PROGRAM_INVALIDATION_V178_DOMAIN, payload
        ),
    }
    program_cache.clear()
    stats["_cross_epoch_retained_branch_entry_count"] = stats.get(
        "_cross_epoch_retained_branch_entry_count", 0
    ) + len(branch_cache)
    stats["_program_cache_successor_state_id"] = state.state_id
    lifecycle["program_transitions"].append(receipt)


def _lazy_authorize_entry(entry, model, maintenance):
    cursor = entry.get("v178_epoch_cursor")
    ledger = maintenance["epoch_ledger"]
    if type(cursor) is not int or not 0 <= cursor <= len(ledger):
        _fail("V178 retained entry lacks an exact epoch cursor")
    if cursor == len(ledger):
        return None
    dependency_id = entry["dependency"]["dependency_receipt_id"]
    suffix = ledger[cursor:]
    if any(
        dependency_id in transition["invalidated_dependency_receipt_ids"]
        for transition in suffix
    ):
        _fail("V178 invalidated dependency reached lazy authorization")
    prior_graph_id = entry["authorized_quotient_graph_id"]
    entry["epoch_authorization_chain"].extend(copy.deepcopy(suffix))
    entry["authorized_quotient_graph_id"] = model["quotient_graph_id"]
    entry["v178_epoch_cursor"] = len(ledger)
    payload = {
        "schema": "acfqp.lazy_epoch_authorization.v178",
        "quotient_dependency_receipt_id": dependency_id,
        "source_epoch_cursor": cursor,
        "current_epoch_cursor": len(ledger),
        "consumed_epoch_transition_receipt_ids": [
            row["epoch_transition_receipt_id"] for row in suffix
        ],
        "previous_authorized_quotient_graph_id": prior_graph_id,
        "current_authorized_quotient_graph_id": model["quotient_graph_id"],
        "dependency_projection_rescan_count": 0,
        "prior_receipt_event_scan_count": 0,
        "authorization_metadata_updated_only_on_actual_cache_hit": True,
        "lazy_authorization_is_ordering_not_safety_authority": True,
    }
    receipt = {
        **payload,
        "lazy_authorization_receipt_id": domains.extension_content_id_v178(
            domains.CONSTRUCTION_K7_LAZY_AUTHORIZATION_V178_DOMAIN, payload
        ),
    }
    maintenance["lazy_authorizations"].append(receipt)
    maintenance["lazy_authorization_metadata_updates"] += 1
    maintenance["lazy_epoch_receipt_appends"] += len(suffix)
    return receipt


_BASE_ORDERER = v174._BASE_ORDERER  # noqa: SLF001


def _indexed_lazy_orderer(
    adapter,
    candidate,
    state,
    cache,
    entries,
    reverse_index,
    stats,
    *,
    maximum_abstract_depth,
):
    lifecycle = v174._ACTIVE.get()  # noqa: SLF001
    if lifecycle is None:
        _fail("V178 orderer has no owner-bound receipt lifecycle")
    maintenance = _maintenance(lifecycle)
    _indexed_program_invalidation(state, stats, lifecycle)
    delegate = _BASE_ORDERER(
        adapter,
        candidate,
        state,
        cache,
        entries,
        reverse_index,
        stats,
        maximum_abstract_depth=maximum_abstract_depth,
    )

    def order(raw, legal, legality_support_source, legality_failure_index):
        key = v109._stable_key(candidate, raw, legal)  # noqa: SLF001
        cached = cache.get(key, ())
        if len(cached) > 1:
            _fail("V178 cache key resolved to multiple graph dependencies")
        lazy_authorization = None
        if cached:
            lazy_authorization = _lazy_authorize_entry(
                cached[0], state.model, maintenance
            )
        plan = delegate(raw, legal, legality_support_source, legality_failure_index)
        if plan is None:
            return None
        if cache.get(key):
            entry = cache[key][0]
            if "v178_epoch_cursor" not in entry:
                entry["v178_epoch_cursor"] = len(maintenance["epoch_ledger"])
        before = canonical_json_bytes(plan)
        dependency = v174._projection(  # noqa: SLF001
            plan,
            candidate=candidate,
            raw=raw,
            legal=legal,
            cache=cache,
            entries=entries,
            program_cache=stats["_program_cache"],
        )
        identity = dependency["dependency_projection_id"]
        previous = lifecycle["projections"].get(identity)
        if previous is not None and canonical_json_bytes(previous) != canonical_json_bytes(
            dependency
        ):
            _fail("V178 dependency projection identity collision")
        lifecycle["projections"][identity] = copy.deepcopy(dependency)
        wrapper_bytes, receipt = v174._issuance_receipt(  # noqa: SLF001
            raw,
            legal,
            legality_support_source,
            legality_failure_index,
            plan,
            dependency,
            len(lifecycle["events"]),
            before,
        )
        if canonical_json_bytes(plan) != before:
            _fail("V178 receipt issuance mutated the delegate plan")
        event = {
            "wrapper_bytes": wrapper_bytes,
            "receipt": receipt,
            "dependency": copy.deepcopy(dependency),
        }
        lifecycle["events"].append(event)
        receipt_id = receipt["online_plan_issuance_receipt_id"]
        if lazy_authorization is not None:
            join_payload = {
                "schema": "acfqp.lazy_authorization_issuance_join.v178",
                "join_ordinal": len(maintenance["lazy_authorization_joins"]),
                "lazy_authorization_receipt_id": lazy_authorization[
                    "lazy_authorization_receipt_id"
                ],
                "online_plan_issuance_receipt_id": receipt_id,
                "quotient_dependency_receipt_id": lazy_authorization[
                    "quotient_dependency_receipt_id"
                ],
                "dependency_projection_id": dependency["dependency_projection_id"],
                "authorization_completed_before_issuance": True,
                "issuance_completed_before_orderer_return": True,
                "join_is_ordering_not_safety_authority": True,
            }
            maintenance["lazy_authorization_joins"].append(
                {
                    **join_payload,
                    "lazy_authorization_issuance_join_id": (
                        domains.extension_content_id_v178(
                            domains.CONSTRUCTION_K7_LAZY_AUTHORIZATION_JOIN_V178_DOMAIN,
                            join_payload,
                        )
                    ),
                }
            )
        if dependency["dependency_kind"] == v174.GRAPH_DEPENDENCY:
            dependency_id = dependency["quotient_dependency_receipt_id"]
            maintenance["graph_receipts_by_dependency"].setdefault(
                dependency_id, []
            ).append(receipt_id)
            maintenance["graph_receipt_index_updates"] += 1
        else:
            index_key = (
                dependency["current_successor_state_id"],
                receipt["source_plan_id"],
            )
            maintenance["program_receipts_by_state_and_plan"].setdefault(
                index_key, []
            ).append(receipt_id)
            maintenance["program_receipt_index_updates"] += 1
        return plan

    return order


def _indexed_lazy_transition(
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
        _fail("V178 transition lacks its owner-bound lifecycles")
    maintenance = _maintenance(receipt_lifecycle)
    delta = delta_lifecycle.get("pending_delta")
    if delta is None or not (
        delta["previous_quotient_graph_id"] == previous_model["quotient_graph_id"]
        and delta["current_quotient_graph_id"] == current_model["quotient_graph_id"]
        and delta["previous_terminal_projection_rule"]
        == [dict(row) for row in previous_rules]
        and delta["current_terminal_projection_rule"]
        == [dict(row) for row in current_rules]
    ):
        _fail("V178 certificate delta/model epoch join changed")
    changed = tuple(tuple(row) for row in delta["changed_projected_states"])
    rules_changed = list(previous_rules) != list(current_rules)
    all_ids = set(entries)
    if rules_changed:
        invalidated = set(all_ids)
    else:
        invalidated = set()
        for projected_state in changed:
            invalidated.update(reverse_index.get(projected_state, ()))
    if not invalidated <= all_ids:
        _fail("V178 reverse index references a non-live cache entry")
    retained = all_ids - invalidated
    affected_receipts: set[str] = set()
    for dependency_id in invalidated:
        maintenance["graph_receipt_index_lookups"] += 1
        affected_receipts.update(
            maintenance["graph_receipts_by_dependency"].get(dependency_id, ())
        )
    payload = {
        "schema": "acfqp.indexed_lazy_model_epoch_transition.v178",
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
        "invalidated_online_plan_issuance_receipt_ids": sorted(affected_receipts),
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": 0,
        "production_full_graph_diff_checks": 0,
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_prior_receipt_event_scan_count": 0,
        "retained_authorization_metadata_updates": 0,
        "prior_receipt_reverse_index_lookups": len(invalidated),
        "reverse_dependency_index_lookups": len(changed),
        "epoch_ledger_append_count": 1,
        "receipt_reverse_index_drove_invalidation": True,
        "retained_authorization_deferred_until_actual_cache_hit": True,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "producer_free_dependency_and_full_graph_controls_required": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    transition = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v178(
            domains.CONSTRUCTION_K7_EPOCH_TRANSITION_V178_DOMAIN, payload
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
            projected_state = tuple(row["projected_state"])
            reverse_index[projected_state].discard(identity)
            if not reverse_index[projected_state]:
                del reverse_index[projected_state]
    maintenance["epoch_ledger"].append(copy.deepcopy(transition))
    join_payload = {
        "schema": "acfqp.certificate_delta_transition_join.v178",
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
        "production_prior_receipt_event_scan_absent": True,
        "retained_metadata_eager_update_absent": True,
        "join_is_cache_maintenance_not_safety_authority": True,
    }
    join = {
        **join_payload,
        "delta_transition_join_id": domains.extension_content_id_v178(
            domains.CONSTRUCTION_K7_DELTA_TRANSITION_JOIN_V178_DOMAIN,
            join_payload,
        ),
    }
    delta_lifecycle["transition_joins"].append(join)
    delta_lifecycle["pending_delta"] = None
    receipt_lifecycle["epoch_transitions"].append(copy.deepcopy(transition))
    return transition


_V111_PROXY = SimpleNamespace(**v111.__dict__)
_V111_PROXY._identity_short_circuited_transition = _indexed_lazy_transition
_RUN_GLOBALS = dict(v154._RUN.__globals__)  # noqa: SLF001
_RUN_GLOBALS.update(
    _owned_orderer=_indexed_lazy_orderer,
    advance_standalone_generic_model_v125=_advance_with_certificate_delta,
    v111=_V111_PROXY,
)
_DELTA_RUN = _clone(v154._RUN, _RUN_GLOBALS)  # noqa: SLF001
_V154_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v154=domains.extension_content_id_v178,
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V178_DOMAIN,
)
_V154_GLOBALS = dict(v154.__dict__)
_V154_GLOBALS.update(_RUN=_DELTA_RUN, domains=_V154_DOMAIN_PROXY)
_DELTA_V154 = _clone(v154.run_certified_memoized_planner_sequence_v154, _V154_GLOBALS)
_V174_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v174=domains.extension_content_id_v178,
    CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V178_DOMAIN,
)
_V174_GLOBALS = dict(
    v174.run_receipt_driven_minimal_invalidation_sequence_v174.__globals__
)
_V174_GLOBALS.update(_RECEIPT_V154=_DELTA_V154, domains=_V174_DOMAIN_PROXY)
_DELTA_V174_SHAPE = _clone(
    v174.run_receipt_driven_minimal_invalidation_sequence_v174,
    _V174_GLOBALS,
)


def run_indexed_lazy_invalidation_sequence_v178(*args, **kwargs):
    lifecycle = {
        "certificate_deltas": [],
        "transition_joins": [],
        "pending_delta": None,
    }
    maintenance = {
        "epoch_ledger": [],
        "graph_receipts_by_dependency": {},
        "program_receipts_by_state_and_plan": {},
        "lazy_authorizations": [],
        "lazy_authorization_joins": [],
        "graph_receipt_index_updates": 0,
        "program_receipt_index_updates": 0,
        "graph_receipt_index_lookups": 0,
        "program_receipt_index_lookups": 0,
        "lazy_authorization_metadata_updates": 0,
        "lazy_epoch_receipt_appends": 0,
    }
    token = _DELTA_ACTIVE.set(lifecycle)
    maintenance_token = _MAINTENANCE_ACTIVE.set(maintenance)
    try:
        historical = _DELTA_V174_SHAPE(*args, **kwargs)
    finally:
        _MAINTENANCE_ACTIVE.reset(maintenance_token)
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
        _fail("V178 indexed-lazy lifecycle escaped stored evidence")
    if len(maintenance["epoch_ledger"]) != len(transitions):
        _fail("V178 epoch ledger escaped transition evidence")
    decision_compute = sum(
        deltas[index]["delta_derivation_compute_events"]
        + transitions[index]["reverse_dependency_index_lookups"]
        + transitions[index]["prior_receipt_reverse_index_lookups"]
        for index in range(len(joins))
    )
    payload = {
        **{
            key: value
            for key, value in historical.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.indexed_lazy_invalidation_sequence.v178",
        "source_v174_shape_sequence_id": historical["sequence_id"],
        "certificate_local_model_delta_receipts": deltas,
        "certificate_local_model_delta_receipt_count": len(deltas),
        "delta_transition_joins": joins,
        "delta_transition_join_count": len(joins),
        "terminal_delta_not_consumed_because_no_later_planning_epoch": deltas[-1][
            "certificate_delta_receipt_id"
        ],
        "indexed_lazy_invalidation_decision_compute_events": decision_compute,
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "production_full_graph_diff_checks": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_prior_receipt_event_scan_count": 0,
        "retained_authorization_metadata_update_count": 0,
        "lazy_authorization_receipts": maintenance["lazy_authorizations"],
        "lazy_authorization_receipt_count": len(
            maintenance["lazy_authorizations"]
        ),
        "lazy_authorization_issuance_joins": maintenance[
            "lazy_authorization_joins"
        ],
        "lazy_authorization_issuance_join_count": len(
            maintenance["lazy_authorization_joins"]
        ),
        "lazy_authorization_metadata_update_count": maintenance[
            "lazy_authorization_metadata_updates"
        ],
        "lazy_epoch_receipt_append_count": maintenance[
            "lazy_epoch_receipt_appends"
        ],
        "graph_receipt_reverse_index_update_count": maintenance[
            "graph_receipt_index_updates"
        ],
        "program_receipt_reverse_index_update_count": maintenance[
            "program_receipt_index_updates"
        ],
        "graph_receipt_reverse_index_lookup_count": maintenance[
            "graph_receipt_index_lookups"
        ],
        "program_receipt_reverse_index_lookup_count": maintenance[
            "program_receipt_index_lookups"
        ],
        "producer_free_dependency_and_full_graph_controls_required": True,
        "certificate_reverse_index_drives_minimal_invalidation": True,
        "prior_receipt_reverse_index_drives_issuance_lookup": True,
        "retained_authorization_is_lazy_on_actual_hit": True,
        "receipt_dependency_lifecycle_changes_cache_authorization_metadata": True,
        "receipt_dependency_lifecycle_eagerly_updates_retained_metadata": False,
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
        "sequence_id": domains.extension_content_id_v178(
            domains.CONSTRUCTION_K7_SEQUENCE_V178_DOMAIN, payload
        ),
    }


__all__ = ("run_indexed_lazy_invalidation_sequence_v178",)
