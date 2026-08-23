"""Let online typed receipts authorize minimal cache invalidation and reuse.

V172 issued a typed receipt before an abstract plan crossed the orderer return
boundary.  V174 gives that receipt a normalized dependency projection and uses
the projection inventory, rather than the full graph identity, to decide which
quotient cache entries are invalidated at the next model epoch.  Compiled
program memo entries retain their exact successor-state dependency and are
closed only when that declared state changes.

The receipts remain ordering/cache-maintenance evidence.  Exact query-local
ground support remains the only safety authority.
"""

from __future__ import annotations

from collections import defaultdict
import contextvars
import copy
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import certified_memoized_planner_sequence_v154 as v154
from acfqp import construction_k7_domain_registry_extension_v109 as domains_v109
from acfqp import construction_k7_domain_registry_extension_v174 as domains
from acfqp import generic_dependency_revalidated_quotient_sequence_v109 as v109
from acfqp import generic_identity_short_circuited_epoch_sequence_v111 as v111
from acfqp import online_typed_plan_receipt_sequence_v172 as v172
from acfqp.phase3e_ids import canonical_json_bytes


GRAPH_DEPENDENCY = "MINIMAL_QUOTIENT_BFS_DEPENDENCY"
COMPILED_STATE_DEPENDENCY = "EXACT_COMPILED_SUCCESSOR_STATE_DEPENDENCY"


class ReceiptDrivenMinimalInvalidationSequenceV174Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ReceiptDrivenMinimalInvalidationSequenceV174Error(message)


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


def _sha(document: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _dependency_receipt(document: Mapping[str, Any]) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V174 quotient dependency receipt type changed")
    payload = {
        key: value for key, value in document.items() if key != "dependency_receipt_id"
    }
    if not (
        document.get("schema")
        == "acfqp.generic_quotient_plan_dependency_receipt.v109"
        and document.get("dependency_receipt_id")
        == domains_v109.extension_content_id_v109(
            domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_DEPENDENCY_V109_DOMAIN,
            payload,
        )
        and document.get("dependency_row_count")
        == len(document.get("ordered_bfs_dependency_rows", ()))
        and document.get("receipt_is_ordering_dependency_not_safety_authority")
        is True
        and document.get(
            "query_local_exact_certificate_remains_only_safety_authority"
        )
        is True
    ):
        _fail("V174 quotient dependency receipt identity changed")
    return dict(document)


def _graph_projection(
    plan: Mapping[str, Any],
    dependency: Mapping[str, Any],
    *,
    legal: tuple[int, ...],
) -> dict[str, Any]:
    dependency = _dependency_receipt(dependency)
    plan_id = v172._plan_id(plan)  # noqa: SLF001
    if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
        chain = []
        current_graph = dependency["source_quotient_graph_id"]
        if dependency["source_quotient_plan_id"] != plan_id:
            _fail("V174 direct quotient dependency source plan changed")
    else:
        validation = plan.get("dependency_revalidation")
        if type(validation) is not dict:
            _fail("V174 revalidated plan lacks dependency validation")
        chain = validation.get("epoch_authorization_chain")
        current_graph = validation.get("current_quotient_graph_id")
        if not (
            type(chain) is list
            and chain
            and validation.get("dependency_receipt_id")
            == dependency["dependency_receipt_id"]
            and validation.get("per_hit_dependency_rescan_performed") is False
            and validation.get("dependency_validation_check_count") == 0
            and chain[-1].get("current_quotient_graph_id") == current_graph
        ):
            _fail("V174 incremental quotient authorization chain changed")
    states = [row["projected_state"] for row in dependency["ordered_bfs_dependency_rows"]]
    if len(states) != len({tuple(state) for state in states}):
        _fail("V174 quotient dependency projected states are ambiguous")
    payload = {
        "schema": "acfqp.online_plan_dependency_projection.v174",
        "dependency_kind": GRAPH_DEPENDENCY,
        "typed_plan_source": v172.TAXONOMY[(plan["schema"], plan["planning_source"])],
        "source_plan_id": plan_id,
        "partial_candidate_id": plan["partial_candidate_id"],
        "current_quotient_graph_id": current_graph,
        "exact_legal_action_keys_sha256": _sha(list(legal)),
        "quotient_dependency_receipt_id": dependency["dependency_receipt_id"],
        "dependency_source_plan_id": dependency["source_quotient_plan_id"],
        "source_quotient_graph_id": dependency["source_quotient_graph_id"],
        "ordered_projected_state_dependencies": copy.deepcopy(states),
        "ordered_projected_state_dependencies_sha256": _sha(states),
        "terminal_projection_rule_sha256": _sha(
            dependency["terminal_projection_rule"]
        ),
        "epoch_authorization_chain_ids": [
            row["epoch_transition_receipt_id"] for row in chain
        ],
        "minimal_dependency_projection_excludes_unrelated_graph_edges": True,
        "dependency_projection_is_ordering_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "dependency_projection_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_DEPENDENCY_PROJECTION_V174_DOMAIN, payload
        ),
    }


def _compiled_projection(
    plan: Mapping[str, Any],
    *,
    legal: tuple[int, ...],
    program_cache: Mapping[Any, Any],
) -> dict[str, Any]:
    plan_id = v172._plan_id(plan)  # noqa: SLF001
    if plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK":
        matches = [
            entry
            for entry in program_cache.values()
            if v172._plan_id(entry["source_plan"]) == plan_id  # noqa: SLF001
        ]
        if len(matches) != 1:
            _fail("V174 direct program plan lacks one live memo dependency")
        source_state = current_state = matches[0]["successor_state_id"]
        terminal_sha = matches[0]["terminal_rule_sha256"]
        source_plan_id = plan_id
    else:
        source_state = plan.get("source_successor_state_id")
        current_state = plan.get("current_successor_state_id")
        terminal_sha = plan.get("terminal_projection_rule_sha256")
        source_plan_id = plan.get("source_compiled_factor_program_plan_id")
        if not (
            source_state == current_state
            and type(source_state) is str
            and len(source_state) == 64
            and type(terminal_sha) is str
            and len(terminal_sha) == 64
        ):
            _fail("V174 memoized program dependency changed")
    payload = {
        "schema": "acfqp.online_plan_dependency_projection.v174",
        "dependency_kind": COMPILED_STATE_DEPENDENCY,
        "typed_plan_source": v172.TAXONOMY[(plan["schema"], plan["planning_source"])],
        "source_plan_id": plan_id,
        "partial_candidate_id": plan["partial_candidate_id"],
        "current_quotient_graph_id": plan["quotient_graph_id"],
        "exact_legal_action_keys_sha256": _sha(list(legal)),
        "source_compiled_program_plan_id": source_plan_id,
        "source_successor_state_id": source_state,
        "current_successor_state_id": current_state,
        "terminal_projection_rule_sha256": terminal_sha,
        "exact_compiled_state_change_invalidates_program_memo": True,
        "dependency_projection_is_ordering_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "dependency_projection_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_DEPENDENCY_PROJECTION_V174_DOMAIN, payload
        ),
    }


def _projection(
    plan: Mapping[str, Any],
    *,
    legal: tuple[int, ...],
    entries: Mapping[str, Mapping[str, Any]],
    program_cache: Mapping[Any, Any],
) -> dict[str, Any]:
    source = v172.TAXONOMY.get((plan.get("schema"), plan.get("planning_source")))
    if source is None:
        _fail("V174 plan escaped the complete receipt taxonomy")
    if source in (
        "OBSERVATION_DERIVED_QUOTIENT_ORDER",
        "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
    ):
        if source == "OBSERVATION_DERIVED_QUOTIENT_ORDER":
            plan_id = v172._plan_id(plan)  # noqa: SLF001
            matches = [
                entry["dependency"]
                for entry in entries.values()
                if v172._plan_id(entry["source_plan"]) == plan_id  # noqa: SLF001
            ]
            if len(matches) != 1:
                _fail("V174 observation plan lacks one live graph dependency")
            dependency = matches[0]
        else:
            dependency = plan.get("quotient_plan_dependency_receipt")
        return _graph_projection(plan, dependency, legal=legal)
    return _compiled_projection(plan, legal=legal, program_cache=program_cache)


_ACTIVE: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "v174_receipt_dependency_lifecycle", default=None
)
_BASE_ORDERER = v154._RUN.__globals__["_owned_orderer"]  # noqa: SLF001


def _program_invalidation(
    state,
    stats: dict[str, Any],
    lifecycle: dict[str, Any],
) -> None:
    prior_state = stats.get("_program_cache_successor_state_id")
    if prior_state is None or prior_state == state.state_id:
        return
    program_cache = stats.setdefault("_program_cache", {})
    branch_cache = stats.setdefault("_program_branch_cache", {})
    source_plan_ids = sorted(
        v172._plan_id(entry["source_plan"])  # noqa: SLF001
        for entry in program_cache.values()
    )
    affected = sorted(
        event["receipt"]["online_plan_issuance_receipt_id"]
        for event in lifecycle["events"]
        if event["dependency"]["dependency_kind"] == COMPILED_STATE_DEPENDENCY
        and event["dependency"].get("current_successor_state_id") == prior_state
        and event["receipt"]["source_plan_id"] in source_plan_ids
    )
    if source_plan_ids and not affected:
        _fail("V174 compiled cache invalidation lacks prior online receipt")
    payload = {
        "schema": "acfqp.receipt_driven_program_cache_invalidation.v174",
        "previous_successor_state_id": prior_state,
        "current_successor_state_id": state.state_id,
        "compiled_program_cache_entry_count_before": len(program_cache),
        "invalidated_source_plan_ids": source_plan_ids,
        "authorizing_online_plan_issuance_receipt_ids": affected,
        "program_cache_entry_count_after": 0,
        "exact_declared_successor_state_changed": True,
        "receipt_dependency_projection_drove_invalidation": True,
        "invalidation_is_cache_maintenance_not_safety_authority": True,
    }
    receipt = {
        **payload,
        "program_invalidation_receipt_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_PROGRAM_INVALIDATION_V174_DOMAIN, payload
        ),
    }
    program_cache.clear()
    stats["_cross_epoch_retained_branch_entry_count"] = stats.get(
        "_cross_epoch_retained_branch_entry_count", 0
    ) + len(branch_cache)
    stats["_program_cache_successor_state_id"] = state.state_id
    lifecycle["program_transitions"].append(receipt)


def _issuance_receipt(
    raw,
    legal,
    support_source,
    failure_index,
    plan,
    dependency,
    ordinal,
    delegate_plan_bytes,
):
    typed_source = v172.TAXONOMY[(plan["schema"], plan["planning_source"])]
    plan_id = v172._plan_id(plan)  # noqa: SLF001
    if not (
        plan["legality_conditioned_quotient_plan_id"] == plan_id
        and plan["initial_action_key"] in legal
        and plan["query_local_exact_overlay_remains_only_safety_authority"] is True
        and plan["complete_ground_world_model_claimed"] is False
    ):
        _fail("V174 online plan identity or authority boundary changed")
    wrapper_bytes = canonical_json_bytes(
        {"raw_state": list(raw), "abstract_plan": plan}
    )
    payload = {
        "schema": "acfqp.online_dependent_abstract_plan_issuance_receipt.v174",
        "issuance_ordinal": ordinal,
        "plan_schema": plan["schema"],
        "planning_source": plan["planning_source"],
        "typed_plan_source": typed_source,
        "source_plan_id": plan_id,
        "source_plan_wrapper_sha256": hashlib.sha256(wrapper_bytes).hexdigest(),
        "raw_state_sha256": _sha(list(raw)),
        "exact_legal_action_keys": list(legal),
        "exact_legal_action_keys_sha256": _sha(list(legal)),
        "legality_support_source": support_source,
        "legality_failure_index": failure_index,
        "initial_action_key": plan["initial_action_key"],
        "dependency_kind": dependency["dependency_kind"],
        "dependency_projection_id": dependency["dependency_projection_id"],
        "delegate_plan_sha256_before_receipt": hashlib.sha256(
            delegate_plan_bytes
        ).hexdigest(),
        "receipt_issued_before_orderer_return": True,
        "caller_has_not_received_plan_at_receipt_issuance": True,
        "delegate_plan_returned_byte_exact": True,
        "receipt_drives_future_cache_authorization": True,
        "receipt_changes_selected_action_order": False,
        "receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return wrapper_bytes, {
        **payload,
        "online_plan_issuance_receipt_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_ONLINE_PLAN_ISSUANCE_V174_DOMAIN, payload
        ),
    }


def _online_orderer(
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
    lifecycle = _ACTIVE.get()
    if lifecycle is None:
        _fail("V174 orderer has no owner-bound dependency lifecycle")
    _program_invalidation(state, stats, lifecycle)
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
        plan = delegate(raw, legal, legality_support_source, legality_failure_index)
        if plan is None:
            return None
        before = canonical_json_bytes(plan)
        dependency = _projection(
            plan,
            legal=legal,
            entries=entries,
            program_cache=stats["_program_cache"],
        )
        identity = dependency["dependency_projection_id"]
        previous = lifecycle["projections"].get(identity)
        if previous is not None and canonical_json_bytes(previous) != canonical_json_bytes(
            dependency
        ):
            _fail("V174 dependency projection identity collision")
        lifecycle["projections"][identity] = copy.deepcopy(dependency)
        wrapper_bytes, receipt = _issuance_receipt(
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
            _fail("V174 receipt issuance mutated the delegate plan")
        lifecycle["events"].append(
            {
                "wrapper_bytes": wrapper_bytes,
                "receipt": receipt,
                "dependency": copy.deepcopy(dependency),
            }
        )
        return plan

    return order


def _adjacency(model: Mapping[str, Any]):
    staged: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = defaultdict(
        set
    )
    for row in model["projected_edge_rows"]:
        staged[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    return {state: tuple(sorted(edges)) for state, edges in staged.items()}


def _receipt_driven_transition(
    *,
    previous_model,
    current_model,
    previous_rules,
    current_rules,
    cache,
    entries,
    reverse_index,
):
    lifecycle = _ACTIVE.get()
    if lifecycle is None:
        _fail("V174 epoch transition has no owner-bound dependency lifecycle")
    same_identity = (
        previous_model["quotient_graph_id"] == current_model["quotient_graph_id"]
    )
    all_ids = set(entries)
    projections_by_dependency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for projection in lifecycle["projections"].values():
        if projection["dependency_kind"] == GRAPH_DEPENDENCY:
            projections_by_dependency[
                projection["quotient_dependency_receipt_id"]
            ].append(projection)
    dependency_states: dict[str, set[tuple[int, ...]]] = {}
    projection_ids: dict[str, list[str]] = {}
    for identity in all_ids:
        rows = projections_by_dependency.get(identity, [])
        if not rows:
            _fail("V174 live graph cache entry lacks an online receipt projection")
        expected_states = {
            tuple(row["projected_state"])
            for row in entries[identity]["dependency"]["ordered_bfs_dependency_rows"]
        }
        if any(
            {
                tuple(state)
                for state in row["ordered_projected_state_dependencies"]
            }
            != expected_states
            for row in rows
        ):
            _fail("V174 online receipt projection differs from live cache dependency")
        dependency_states[identity] = expected_states
        projection_ids[identity] = sorted(
            row["dependency_projection_id"] for row in rows
        )
    if same_identity:
        before = after = {}
        changed = ()
        changed_rows = []
        rules_changed = False
        diff_checks = 0
        invalidated: set[str] = set()
    else:
        before = _adjacency(previous_model)
        after = _adjacency(current_model)
        states = tuple(sorted(set(before) | set(after)))
        changed = tuple(
            state for state in states if before.get(state, ()) != after.get(state, ())
        )
        rules_changed = list(previous_rules) != list(current_rules)
        diff_checks = sum(
            1 + len(before.get(state, ())) + len(after.get(state, ()))
            for state in states
        ) + len(previous_rules) + len(current_rules)
        if rules_changed:
            invalidated = set(all_ids)
        else:
            changed_set = set(changed)
            invalidated = {
                identity
                for identity, dependencies in dependency_states.items()
                if dependencies & changed_set
            }
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
            for state in changed
        ]
    if rules_changed:
        indexed = set(all_ids)
        lookups = 0
    else:
        indexed = set()
        for state in changed:
            indexed.update(reverse_index.get(state, set()))
        lookups = len(changed)
    if indexed != invalidated:
        _fail("V174 receipt-derived invalidation differs from reverse-index control")
    retained = all_ids - invalidated
    affected_receipts = sorted(
        event["receipt"]["online_plan_issuance_receipt_id"]
        for event in lifecycle["events"]
        if event["dependency"].get("quotient_dependency_receipt_id") in invalidated
    )
    retained_receipts = sorted(
        event["receipt"]["online_plan_issuance_receipt_id"]
        for event in lifecycle["events"]
        if event["dependency"].get("quotient_dependency_receipt_id") in retained
    )
    payload = {
        "schema": "acfqp.receipt_driven_model_epoch_transition.v174",
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "quotient_graph_identity_equal": same_identity,
        "identity_short_circuit_applied": same_identity,
        "previous_terminal_projection_rule": [dict(row) for row in previous_rules],
        "current_terminal_projection_rule": [dict(row) for row in current_rules],
        "terminal_projection_rule_changed": rules_changed,
        "changed_projected_state_rows": changed_rows,
        "changed_projected_state_count": len(changed_rows),
        "cache_entry_ids_before_transition": sorted(all_ids),
        "dependency_projection_ids_by_dependency_receipt_id": {
            identity: projection_ids[identity] for identity in sorted(projection_ids)
        },
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "invalidated_online_plan_issuance_receipt_ids": affected_receipts,
        "retained_online_plan_issuance_receipt_ids": retained_receipts,
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": diff_checks,
        "reverse_dependency_index_lookups": lookups,
        "receipt_dependency_projection_checks": sum(
            len(dependency_states[identity]) for identity in all_ids
        ),
        "same_content_address_skips_full_graph_and_dependency_scan": same_identity,
        "changed_content_address_uses_exact_declared_dependency_delta": not same_identity,
        "receipt_dependency_projection_drove_invalidation": True,
        "reverse_index_used_only_as_matched_consistency_control": True,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    receipt = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_EPOCH_TRANSITION_V174_DOMAIN, payload
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
        entry["epoch_authorization_chain"].append(copy.deepcopy(receipt))
    lifecycle["epoch_transitions"].append(copy.deepcopy(receipt))
    return receipt


_V111_PROXY = SimpleNamespace(**v111.__dict__)
_V111_PROXY._identity_short_circuited_transition = _receipt_driven_transition
_RUN_GLOBALS = dict(v154._RUN.__globals__)  # noqa: SLF001
_RUN_GLOBALS.update(_owned_orderer=_online_orderer, v111=_V111_PROXY)
_RECEIPT_RUN = _clone(v154._RUN, _RUN_GLOBALS)  # noqa: SLF001
_V154_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v154=domains.extension_content_id_v174,
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN,
)
_V154_GLOBALS = dict(v154.__dict__)
_V154_GLOBALS.update(_RUN=_RECEIPT_RUN, domains=_V154_DOMAIN_PROXY)
_RECEIPT_V154 = _clone(
    v154.run_certified_memoized_planner_sequence_v154, _V154_GLOBALS
)


def _execution_join(sequence_id, execution, event, ordinal):
    source_payload = {
        key: value
        for key, value in execution.items()
        if key != "actual_dependency_revalidated_execution_receipt_id"
    }
    source_id = domains_v109.extension_content_id_v109(
        domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
        source_payload,
    )
    receipt = event["receipt"]
    if not (
        execution["actual_dependency_revalidated_execution_receipt_id"] == source_id
        and canonical_json_bytes(execution["quotient_plan_receipt"])
        == event["wrapper_bytes"]
        and execution["quotient_plan_id"] == receipt["source_plan_id"]
        and execution["quotient_proposed_action_key"] == receipt["initial_action_key"]
        and execution["query_local_exact_overlay_remains_only_safety_authority"]
        is True
    ):
        _fail("V174 online receipt/execution join changed")
    payload = {
        "schema": "acfqp.online_dependent_plan_execution_join.v174",
        "source_sequence_id": sequence_id,
        "execution_join_ordinal": ordinal,
        "episode_index": execution["episode_index"],
        "decision_index": execution["decision_index"],
        "source_v109_execution_receipt_id": source_id,
        "online_plan_issuance_receipt_id": receipt[
            "online_plan_issuance_receipt_id"
        ],
        "dependency_projection_id": receipt["dependency_projection_id"],
        "typed_plan_source": receipt["typed_plan_source"],
        "chosen_action_key": execution["chosen_action_key"],
        "quotient_proposed_action_key": execution["quotient_proposed_action_key"],
        "chosen_action_matches_admitted_quotient_proposal": execution[
            "chosen_action_matches_admitted_quotient_proposal"
        ],
        "receipt_was_issued_before_plan_return": True,
        "receipt_dependency_authorized_cache_path": True,
        "receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "online_execution_join_receipt_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_ONLINE_EXECUTION_JOIN_V174_DOMAIN, payload
        ),
    }


def run_receipt_driven_minimal_invalidation_sequence_v174(*args, **kwargs):
    lifecycle: dict[str, Any] = {
        "events": [],
        "projections": {},
        "epoch_transitions": [],
        "program_transitions": [],
    }
    token = _ACTIVE.set(lifecycle)
    try:
        historical = _RECEIPT_V154(*args, **kwargs)
    finally:
        _ACTIVE.reset(token)
    wrappers = [
        wrapper
        for episode in historical["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
    ]
    events = lifecycle["events"]
    if not (
        len(wrappers) == len(events)
        and all(
            canonical_json_bytes(wrapper) == event["wrapper_bytes"]
            for wrapper, event in zip(wrappers, events, strict=True)
        )
        and canonical_json_bytes(historical["model_epoch_transition_receipts"])
        == canonical_json_bytes(lifecycle["epoch_transitions"])
    ):
        _fail("V174 live dependency lifecycle escaped stored sequence evidence")
    index = {}
    cursor = 0
    for episode in historical["episodes"]:
        for wrapper in episode["abstract_plan_receipts"]:
            event = events[cursor]
            cursor += 1
            key = (episode["episode_index"], canonical_json_bytes(wrapper))
            if key in index:
                _fail("V174 online issuance wrapper identity is ambiguous")
            index[key] = event
    joins = []
    for execution in historical[
        "all_actual_legality_conditioned_execution_receipts"
    ]:
        event = index.get(
            (
                execution["episode_index"],
                canonical_json_bytes(execution["quotient_plan_receipt"]),
            )
        )
        if event is None:
            _fail("V174 executed action lacks a prior online dependency receipt")
        joins.append(
            _execution_join(historical["sequence_id"], execution, event, len(joins))
        )
    receipts = [event["receipt"] for event in events]
    projections = [
        lifecycle["projections"][identity]
        for identity in sorted(lifecycle["projections"])
    ]
    projection_ids = {row["dependency_projection_id"] for row in projections}
    if not all(row["dependency_projection_id"] in projection_ids for row in receipts):
        _fail("V174 issuance receipt lacks a retained dependency projection")
    histogram = {
        source: sum(row["typed_plan_source"] == source for row in receipts)
        for source in v172.TAXONOMY.values()
    }
    epoch_transitions = lifecycle["epoch_transitions"]
    program_transitions = lifecycle["program_transitions"]
    incremental = [
        row
        for row in receipts
        if row["typed_plan_source"]
        == "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE"
    ]
    payload = {
        **{
            key: value
            for key, value in historical.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.receipt_driven_minimal_invalidation_sequence.v174",
        "source_v154_shape_sequence_id": historical["sequence_id"],
        "online_dependency_projections": projections,
        "online_dependency_projection_count": len(projections),
        "online_plan_issuance_receipts": receipts,
        "online_plan_issuance_receipt_count": len(receipts),
        "online_execution_join_receipts": joins,
        "online_execution_join_receipt_count": len(joins),
        "online_typed_plan_source_histogram": histogram,
        "receipt_driven_model_epoch_transition_receipts": epoch_transitions,
        "receipt_driven_program_cache_invalidation_receipts": program_transitions,
        "receipt_driven_graph_dependency_invalidation_count": sum(
            len(row["invalidated_dependency_receipt_ids"])
            for row in epoch_transitions
        ),
        "receipt_driven_graph_dependency_retention_count": sum(
            len(row["retained_dependency_receipt_ids"])
            for row in epoch_transitions
        ),
        "receipt_driven_compiled_program_invalidation_count": sum(
            row["compiled_program_cache_entry_count_before"]
            for row in program_transitions
        ),
        "incrementally_revalidated_plan_receipt_count": len(incremental),
        "every_abstract_plan_receipt_issued_before_orderer_return": True,
        "every_executed_action_joins_prior_online_receipt": len(joins)
        == historical["execution_step_count"],
        "every_live_graph_cache_entry_has_prior_online_dependency_projection": True,
        "only_receipt_declared_dependencies_drive_graph_invalidation": True,
        "unaffected_graph_dependencies_reauthorized_without_per_hit_rescan": all(
            row["unaffected_dependency_receipts_retained_without_per_hit_rescan"]
            is True
            for row in epoch_transitions
        ),
        "compiled_program_memo_invalidated_only_on_exact_successor_state_change": all(
            row["exact_declared_successor_state_changed"] is True
            for row in program_transitions
        ),
        "incremental_revalidation_chain_issued_before_reused_plan_return": bool(
            incremental
        )
        and all(row["receipt_issued_before_orderer_return"] is True for row in incremental),
        "receipt_dependency_lifecycle_changes_cache_authorization_metadata": True,
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
        "sequence_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN, payload
        ),
    }


__all__ = (
    "COMPILED_STATE_DEPENDENCY",
    "GRAPH_DEPENDENCY",
    "run_receipt_driven_minimal_invalidation_sequence_v174",
)
