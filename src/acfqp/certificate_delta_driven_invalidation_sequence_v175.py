"""Drive dependency invalidation from certificate-local model deltas.

V174 used online receipt dependencies to minimize the set of invalidated cache
entries, but it still enumerated the full serialized quotient graphs to find
the changed-state frontier.  V175 captures the incremental state carrier's
new projected edges at update time and lets that certificate-local delta drive
the invalidation decision.  A later full-graph diff is retained only as a
matched control and is not charged to the decision path.
"""

from __future__ import annotations

from collections import defaultdict
import contextvars
import copy
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import certified_memoized_planner_sequence_v154 as v154
from acfqp import construction_k7_domain_registry_extension_v175 as domains
from acfqp import generic_identity_short_circuited_epoch_sequence_v111 as v111
from acfqp import receipt_driven_minimal_invalidation_sequence_v174 as v174
from acfqp.phase3e_ids import canonical_json_bytes


class CertificateDeltaDrivenInvalidationSequenceV175Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CertificateDeltaDrivenInvalidationSequenceV175Error(message)


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
    contextvars.ContextVar("v175_certificate_delta_lifecycle", default=None)
)
_BASE_ADVANCE = v154._RUN.__globals__[  # noqa: SLF001
    "advance_standalone_generic_model_v125"
]


def _edge_inventory(state):
    if not hasattr(state, "base_state") or not hasattr(state, "overlay_rows"):
        _fail("V175 incremental state lacks base/overlay edge indices")
    edges = set(state.base_state.edges)
    for row in state.overlay_rows:
        edges.add(
            (
                tuple(row["projected_pre"]),
                row["action_key"],
                tuple(row["projected_post"]),
            )
        )
    return edges


def _advance_with_certificate_delta(state, candidate, new_rows, catalogue):
    lifecycle = _DELTA_ACTIVE.get()
    if lifecycle is None:
        _fail("V175 model update lacks its owner-bound delta lifecycle")
    if lifecycle.get("pending_delta") is not None:
        _fail("V175 prior certificate delta was not consumed by an epoch transition")
    previous_edges = _edge_inventory(state)
    next_state, update = _BASE_ADVANCE(state, candidate, new_rows, catalogue)
    current_edges = _edge_inventory(next_state)
    inserted = sorted(current_edges - previous_edges)
    removed = sorted(previous_edges - current_edges)
    if removed:
        _fail("V175 registered monotone model update removed projected edges")
    changed_states = sorted({pre for pre, _action, _post in inserted})
    input_rows = [row.to_document() for row in new_rows]
    payload = {
        "schema": "acfqp.certificate_local_model_delta.v175",
        "previous_successor_state_id": state.state_id,
        "current_successor_state_id": next_state.state_id,
        "previous_quotient_graph_id": state.model["quotient_graph_id"],
        "current_quotient_graph_id": next_state.model["quotient_graph_id"],
        "source_incremental_update_receipt_id": update["update_receipt_id"],
        "delta_input_raw_row_count": len(input_rows),
        "delta_input_raw_rows_sha256": v174._sha(input_rows),  # noqa: SLF001
        "inserted_projected_edge_rows": [
            {
                "projected_pre": list(pre),
                "action_key": action,
                "projected_post": list(post),
            }
            for pre, action, post in inserted
        ],
        "inserted_projected_edge_count": len(inserted),
        "removed_projected_edge_count": 0,
        "changed_projected_states": [list(state) for state in changed_states],
        "changed_projected_state_count": len(changed_states),
        "previous_terminal_projection_rule": [
            dict(row) for row in state.terminal_rules
        ],
        "current_terminal_projection_rule": [
            dict(row) for row in next_state.terminal_rules
        ],
        "terminal_projection_rule_changed": list(state.terminal_rules)
        != list(next_state.terminal_rules),
        "delta_derivation_compute_events": len(input_rows) + len(inserted),
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "changed_state_frontier_derived_from_incremental_state_indices": True,
        "only_certificate_local_post_failure_rows_enter_delta": True,
        "delta_receipt_is_cache_maintenance_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    receipt = {
        **payload,
        "certificate_delta_receipt_id": domains.extension_content_id_v175(
            domains.CONSTRUCTION_K7_CERTIFICATE_DELTA_V175_DOMAIN, payload
        ),
    }
    lifecycle["certificate_deltas"].append(copy.deepcopy(receipt))
    lifecycle["pending_delta"] = copy.deepcopy(receipt)
    return next_state, update


def _adjacency(model: Mapping[str, Any]):
    staged: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = defaultdict(
        set
    )
    for row in model["projected_edge_rows"]:
        staged[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    return {state: tuple(sorted(edges)) for state, edges in staged.items()}


def _delta_driven_transition(
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
        _fail("V175 epoch transition lacks its two owner-bound lifecycles")
    delta = delta_lifecycle.get("pending_delta")
    if delta is None:
        _fail("V175 epoch transition lacks a certificate-local delta receipt")
    if not (
        delta["previous_quotient_graph_id"] == previous_model["quotient_graph_id"]
        and delta["current_quotient_graph_id"] == current_model["quotient_graph_id"]
        and delta["previous_terminal_projection_rule"]
        == [dict(row) for row in previous_rules]
        and delta["current_terminal_projection_rule"]
        == [dict(row) for row in current_rules]
    ):
        _fail("V175 certificate delta/model epoch join changed")
    same_identity = (
        previous_model["quotient_graph_id"] == current_model["quotient_graph_id"]
    )
    delta_changed = tuple(
        tuple(row) for row in delta["changed_projected_states"]
    )
    rules_changed = list(previous_rules) != list(current_rules)
    all_ids = set(entries)
    projections_by_dependency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for projection in receipt_lifecycle["projections"].values():
        if projection["dependency_kind"] == v174.GRAPH_DEPENDENCY:
            projections_by_dependency[
                projection["quotient_dependency_receipt_id"]
            ].append(projection)
    dependency_states = {}
    projection_ids = {}
    for identity in all_ids:
        projections = projections_by_dependency.get(identity, [])
        if not projections:
            _fail("V175 live graph cache entry lacks an online dependency projection")
        expected = {
            tuple(row["projected_state"])
            for row in entries[identity]["dependency"]["ordered_bfs_dependency_rows"]
        }
        if any(
            {tuple(state) for state in row["ordered_projected_state_dependencies"]}
            != expected
            for row in projections
        ):
            _fail("V175 live dependency differs from its online projection")
        dependency_states[identity] = expected
        projection_ids[identity] = sorted(
            row["dependency_projection_id"] for row in projections
        )
    if rules_changed:
        invalidated = set(all_ids)
    else:
        changed_set = set(delta_changed)
        invalidated = {
            identity
            for identity, states in dependency_states.items()
            if states & changed_set
        }
    retained = all_ids - invalidated
    # The following full diff is deliberately after the delta-based decision.
    before = _adjacency(previous_model)
    after = _adjacency(current_model)
    all_states = tuple(sorted(set(before) | set(after)))
    matched_changed = tuple(
        state
        for state in all_states
        if before.get(state, ()) != after.get(state, ())
    )
    matched_checks = sum(
        1 + len(before.get(state, ())) + len(after.get(state, ()))
        for state in all_states
    ) + len(previous_rules) + len(current_rules)
    if matched_changed != delta_changed:
        _fail(
            "V175 delta frontier differs from the retained full-diff control: "
            f"delta={len(delta_changed)} matched={len(matched_changed)} "
            f"delta_only={len(set(delta_changed) - set(matched_changed))} "
            f"matched_only={len(set(matched_changed) - set(delta_changed))}"
        )
    indexed = set()
    for state in delta_changed:
        indexed.update(reverse_index.get(state, set()))
    if rules_changed:
        indexed = set(all_ids)
    if indexed != invalidated:
        _fail("V175 delta invalidation differs from reverse-index control")
    changed_rows = [
        {
            "projected_state": list(state),
            "previous_outgoing_edges": [
                {"action_key": key, "projected_post": list(post)}
                for key, post in before.get(state, ())
            ],
            "current_outgoing_edges": [
                {"action_key": key, "projected_post": list(post)}
                for key, post in after.get(state, ())
            ],
        }
        for state in delta_changed
    ]
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
        "schema": "acfqp.delta_driven_model_epoch_transition.v175",
        "certificate_delta_receipt_id": delta["certificate_delta_receipt_id"],
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "quotient_graph_identity_equal": same_identity,
        "identity_short_circuit_applied": same_identity and not rules_changed,
        "previous_terminal_projection_rule": [dict(row) for row in previous_rules],
        "current_terminal_projection_rule": [dict(row) for row in current_rules],
        "terminal_projection_rule_changed": rules_changed,
        "delta_derived_changed_projected_state_rows": changed_rows,
        "delta_derived_changed_projected_state_count": len(changed_rows),
        "cache_entry_ids_before_transition": sorted(all_ids),
        "dependency_projection_ids_by_dependency_receipt_id": {
            identity: projection_ids[identity]
            for identity in sorted(projection_ids)
        },
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "invalidated_online_plan_issuance_receipt_ids": affected_receipts,
        "retained_online_plan_issuance_receipt_ids": retained_receipts,
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": 0,
        "delta_dependency_projection_checks": sum(
            len(dependency_states[identity]) for identity in all_ids
        ),
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "matched_full_graph_diff_checks": matched_checks,
        "matched_full_graph_diff_changed_states": [
            list(state) for state in matched_changed
        ],
        "delta_decision_precedes_matched_full_graph_diff": True,
        "matched_full_graph_diff_used_only_as_uncharged_control": True,
        "reverse_dependency_index_lookups": len(delta_changed),
        "receipt_dependency_projection_drove_invalidation": True,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    transition = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v175(
            domains.CONSTRUCTION_K7_EPOCH_TRANSITION_V175_DOMAIN, payload
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
        "schema": "acfqp.certificate_delta_transition_join.v175",
        "join_ordinal": len(delta_lifecycle["transition_joins"]),
        "certificate_delta_receipt_id": delta["certificate_delta_receipt_id"],
        "epoch_transition_receipt_id": transition["epoch_transition_receipt_id"],
        "delta_changed_projected_states": copy.deepcopy(
            delta["changed_projected_states"]
        ),
        "transition_changed_projected_states": [
            list(state) for state in delta_changed
        ],
        "delta_issued_before_transition_decision": True,
        "delta_frontier_exactly_drives_transition": True,
        "join_is_cache_maintenance_not_safety_authority": True,
    }
    join = {
        **join_payload,
        "delta_transition_join_id": domains.extension_content_id_v175(
            domains.CONSTRUCTION_K7_DELTA_TRANSITION_JOIN_V175_DOMAIN,
            join_payload,
        ),
    }
    delta_lifecycle["transition_joins"].append(join)
    delta_lifecycle["pending_delta"] = None
    receipt_lifecycle["epoch_transitions"].append(copy.deepcopy(transition))
    return transition


_V111_PROXY = SimpleNamespace(**v111.__dict__)
_V111_PROXY._identity_short_circuited_transition = _delta_driven_transition
_RUN_GLOBALS = dict(v154._RUN.__globals__)  # noqa: SLF001
_RUN_GLOBALS.update(
    _owned_orderer=v174._online_orderer,  # noqa: SLF001
    advance_standalone_generic_model_v125=_advance_with_certificate_delta,
    v111=_V111_PROXY,
)
_DELTA_RUN = _clone(v154._RUN, _RUN_GLOBALS)  # noqa: SLF001
_V154_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v154=domains.extension_content_id_v175,
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN,
)
_V154_GLOBALS = dict(v154.__dict__)
_V154_GLOBALS.update(_RUN=_DELTA_RUN, domains=_V154_DOMAIN_PROXY)
_DELTA_V154 = _clone(
    v154.run_certified_memoized_planner_sequence_v154, _V154_GLOBALS
)
_V174_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v174=domains.extension_content_id_v175,
    CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN,
)
_V174_GLOBALS = dict(v174.run_receipt_driven_minimal_invalidation_sequence_v174.__globals__)
_V174_GLOBALS.update(_RECEIPT_V154=_DELTA_V154, domains=_V174_DOMAIN_PROXY)
_DELTA_V174_SHAPE = _clone(
    v174.run_receipt_driven_minimal_invalidation_sequence_v174,
    _V174_GLOBALS,
)


def run_certificate_delta_driven_invalidation_sequence_v175(*args, **kwargs):
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
        _fail("V175 delta/transition lifecycle escaped the stored sequence")
    decision_delta_compute = sum(
        deltas[index]["delta_derivation_compute_events"]
        for index in range(len(joins))
    )
    control_checks = sum(
        row["matched_full_graph_diff_checks"] for row in transitions
    )
    payload = {
        **{
            key: value
            for key, value in historical.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.certificate_delta_driven_invalidation_sequence.v175",
        "source_v174_shape_sequence_id": historical["sequence_id"],
        "certificate_local_model_delta_receipts": deltas,
        "certificate_local_model_delta_receipt_count": len(deltas),
        "delta_transition_joins": joins,
        "delta_transition_join_count": len(joins),
        "terminal_delta_not_consumed_because_no_later_planning_epoch": deltas[-1][
            "certificate_delta_receipt_id"
        ],
        "delta_driven_invalidation_decision_compute_events": decision_delta_compute,
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "matched_full_graph_diff_control_checks": control_checks,
        "full_graph_diff_checks_avoided_on_invalidation_decision_path": control_checks,
        "certificate_local_delta_drives_changed_state_frontier": True,
        "matched_full_graph_diff_is_only_uncharged_control": True,
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
        "sequence_id": domains.extension_content_id_v175(
            domains.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN, payload
        ),
    }


__all__ = ("run_certificate_delta_driven_invalidation_sequence_v175",)
