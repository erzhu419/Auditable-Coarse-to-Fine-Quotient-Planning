"""Producer-free verification of the corrected V178r1 campaign.

This verifier does not import the V178/V178r1 producer, campaign core, or
sequence implementation.  It reconstructs the certificate-local deltas,
dependency and issuance reverse indices, lazy epoch authorizations, issuance
joins, and verifier-only full graph/dependency controls from frozen bytes.
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v174 as domains_v174
from acfqp import construction_k7_domain_registry_extension_v178 as domains_v178
from acfqp import construction_k7_domain_registry_extension_v178r1 as domains
from acfqp import construction_k7_reverse_index_only_invalidation_independent_verifier_v177 as previous
from acfqp.generic_packet_batching_adapter_v134 import FAMILY as PACKET_FAMILY
from acfqp.generic_reservoir_dispatch_adapter_v171 import FAMILY as RESERVOIR_FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "a4ffe67949d0cad7f392f678b5b8c9c4d6631ebea5d9e49c95f61367f2b40064"
PREREGISTRATION_BYTE_COUNT = 4_618
PREREGISTRATION_SHA256 = "88bd8fc4a05b543394d7c5f5fe27d57c0d3a1ddffb9468fb40f03cf3bf5bcf45"
CAMPAIGN_ID = "0" * 64
CAMPAIGN_BYTE_COUNT = 0
CAMPAIGN_SHA256 = "0" * 64
V177_CAMPAIGN_ID = "cf9e0bf64ba285d3b1873e5d48636a4de0e68006d7c3e43d761ebbf4a9d5f985"
V177_VERIFICATION_ID = "1f062589b9db53758691431dec327c0d303f20d06bd6b44c647eca02a11c76dd"
V178_FAILURE_ID = "1c749090356db31c10a22d58bd88bb620c097e9ec730ef746c06800f50effa49"
CLASSIFIER_ID = "893a5b0597fe2c9d0544defcf3655ce6e186950e7c1342a7a7502de0d4f1378d"
TARGETS = (
    (PACKET_FAMILY, 1_181_951, "INDEXED_INVALIDATION_AND_LAZY_PROGRAM_AUTHORIZATION"),
    (PACKET_FAMILY, 1_181_952, "INDEXED_INVALIDATION_AND_LAZY_PROGRAM_AUTHORIZATION"),
    (RESERVOIR_FAMILY, 1_191_951, "INDEXED_RETENTION_AND_LAZY_GRAPH_AUTHORIZATION"),
    (RESERVOIR_FAMILY, 1_191_952, "INDEXED_RETENTION_AND_LAZY_GRAPH_AUTHORIZATION"),
)
EPISODES = (1_083, 1_084, 1_085, 1_086)
TARGET_WORKERS = 2
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7IndexedLazyInvalidationIndependentVerifierV178R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IndexedLazyInvalidationIndependentVerifierV178R1Error(
        message
    )


def _frozen(raw, *, count, digest, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V178r1 independent frozen {name} changed")
    return document


def _sequence_content_id(domain_tag, payload):
    if domain_tag == domains_v178.CONSTRUCTION_K7_SEQUENCE_V178_DOMAIN:
        return domains_v178.extension_content_id_v178(domain_tag, payload)
    return domains_v174.extension_content_id_v174(domain_tag, payload)


_SEQUENCE_DOMAINS = SimpleNamespace(**domains_v174.__dict__)
_SEQUENCE_DOMAINS.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN = (
    domains_v178.CONSTRUCTION_K7_SEQUENCE_V178_DOMAIN
)
_SEQUENCE_DOMAINS.extension_content_id_v174 = _sequence_content_id


_CONTEXT = None


def _adjacency(model: Mapping[str, Any]):
    return previous._adjacency(model)  # noqa: SLF001


def _expected_delta(sequence, offset, rules):
    source = previous._expected_delta(sequence, offset, rules)  # noqa: SLF001
    payload = {
        **{
            key: value
            for key, value in source.items()
            if key not in {"schema", "certificate_delta_receipt_id"}
        },
        "schema": "acfqp.certificate_local_model_delta.v178",
    }
    return {
        **payload,
        "certificate_delta_receipt_id": domains_v178.extension_content_id_v178(
            domains_v178.CONSTRUCTION_K7_CERTIFICATE_DELTA_V178_DOMAIN, payload
        ),
    }


def _program_expected(previous_state, current_state, direct_events):
    context = _CONTEXT
    if context is None:
        _fail("V178r1 independent program context is absent")
    cursor = context["program_cursor"]
    groups = context["program_groups"]
    if cursor >= len(groups):
        _fail("V178r1 independent program transition cardinality changed")
    group = groups[cursor]
    if not (
        group["previous_state"] == previous_state
        and group["current_state"] == current_state
    ):
        _fail("V178r1 independent program state transition changed")
    keys = set()
    source_plan_ids = []
    for wrapper, receipt in direct_events:
        key = (tuple(wrapper["raw_state"]), tuple(receipt["exact_legal_action_keys"]))
        if key in keys:
            _fail("V178r1 independent program cache key is not unique")
        keys.add(key)
        source_plan_ids.append(receipt["source_plan_id"])
    source_plan_ids = sorted(source_plan_ids)
    index = context["program_receipt_index"]
    for receipt in group["program_receipts"]:
        index[(previous_state, receipt["source_plan_id"])].add(
            receipt["online_plan_issuance_receipt_id"]
        )
    affected = set()
    for source_plan_id in source_plan_ids:
        affected.update(index.get((previous_state, source_plan_id), ()))
    payload = {
        "schema": "acfqp.indexed_program_cache_invalidation.v178",
        "previous_successor_state_id": previous_state,
        "current_successor_state_id": current_state,
        "compiled_program_cache_entry_count_before": len(keys),
        "invalidated_source_plan_ids": source_plan_ids,
        "authorizing_online_plan_issuance_receipt_ids": sorted(affected),
        "program_cache_entry_count_after": 0,
        "production_prior_receipt_event_scan_count": 0,
        "prior_receipt_reverse_index_lookups": len(source_plan_ids),
        "exact_declared_successor_state_changed": True,
        "receipt_dependency_projection_drove_invalidation": True,
        "invalidation_is_cache_maintenance_not_safety_authority": True,
    }
    context["program_cursor"] += 1
    return {
        **payload,
        "program_invalidation_receipt_id": domains_v178.extension_content_id_v178(
            domains_v178.CONSTRUCTION_K7_PROGRAM_INVALIDATION_V178_DOMAIN,
            payload,
        ),
    }


def _transition_expected(
    previous_model,
    current_model,
    rules,
    active,
    dependencies,
    projection_ids,
    graph_events,
):
    del projection_ids
    context = _CONTEXT
    if context is None:
        _fail("V178r1 independent delta context is absent")
    offset = context["delta_cursor"]
    expected_delta = _expected_delta(context["sequence"], offset, rules)
    actual_delta = context["deltas"][offset]
    if canonical_json_bytes(expected_delta) != canonical_json_bytes(actual_delta):
        _fail("V178r1 independent certificate-local delta reconstruction changed")
    previous_adjacency = _adjacency(previous_model)
    current_adjacency = _adjacency(current_model)
    changed = tuple(tuple(row) for row in expected_delta["changed_projected_states"])
    all_states = tuple(sorted(set(previous_adjacency) | set(current_adjacency)))
    full_diff_changed = tuple(
        state
        for state in all_states
        if previous_adjacency.get(state, ()) != current_adjacency.get(state, ())
    )
    if changed != full_diff_changed:
        _fail("V178r1 independent delta/full-graph frontier mismatch")
    rules_changed = expected_delta["terminal_projection_rule_changed"]
    dependency_states = {
        identity: {
            tuple(row["projected_state"])
            for row in dependencies[identity]["ordered_bfs_dependency_rows"]
        }
        for identity in active
    }
    if rules_changed:
        full_dependency_invalidated = set(active)
    else:
        changed_set = set(changed)
        full_dependency_invalidated = {
            identity
            for identity, states in dependency_states.items()
            if states & changed_set
        }
    reverse_index = defaultdict(set)
    for identity, states in dependency_states.items():
        for state in states:
            reverse_index[state].add(identity)
    indexed_invalidated = set(active) if rules_changed else set()
    if not rules_changed:
        for state in changed:
            indexed_invalidated.update(reverse_index.get(state, ()))
    if indexed_invalidated != full_dependency_invalidated:
        _fail("V178r1 independent reverse-index/full-dependency mismatch")
    invalidated = indexed_invalidated
    retained = set(active) - invalidated
    receipt_index = defaultdict(set)
    for receipt, dependency_id in graph_events:
        receipt_index[dependency_id].add(
            receipt["online_plan_issuance_receipt_id"]
        )
    affected = set()
    for dependency_id in invalidated:
        affected.update(receipt_index.get(dependency_id, ()))
    payload = {
        "schema": "acfqp.indexed_lazy_model_epoch_transition.v178",
        "certificate_delta_receipt_id": expected_delta[
            "certificate_delta_receipt_id"
        ],
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "quotient_graph_identity_equal": previous_model["quotient_graph_id"]
        == current_model["quotient_graph_id"],
        "identity_short_circuit_applied": previous_model["quotient_graph_id"]
        == current_model["quotient_graph_id"]
        and not rules_changed,
        "previous_terminal_projection_rule": [dict(row) for row in rules],
        "current_terminal_projection_rule": [dict(row) for row in rules],
        "terminal_projection_rule_changed": rules_changed,
        "delta_changed_projected_states": expected_delta[
            "changed_projected_states"
        ],
        "delta_inserted_projected_edge_rows": expected_delta[
            "inserted_projected_edge_rows"
        ],
        "cache_entry_ids_before_transition": sorted(active),
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "invalidated_online_plan_issuance_receipt_ids": sorted(affected),
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
        "epoch_transition_receipt_id": domains_v178.extension_content_id_v178(
            domains_v178.CONSTRUCTION_K7_EPOCH_TRANSITION_V178_DOMAIN, payload
        ),
    }
    full_graph_checks = sum(
        1
        + len(previous_adjacency.get(state, ()))
        + len(current_adjacency.get(state, ()))
        for state in all_states
    ) + 2 * len(rules)
    full_dependency_checks = sum(len(states) for states in dependency_states.values())
    context["expected_transitions"].append(transition)
    context["verifier_full_graph_checks"].append(full_graph_checks)
    context["verifier_full_dependency_checks"].append(full_dependency_checks)
    context["rules"] = [dict(row) for row in rules]
    context["delta_cursor"] += 1
    return transition, invalidated, retained


_VERIFY_GLOBALS = dict(previous._VERIFY_HISTORICAL.__globals__)  # noqa: SLF001
_VERIFY_GLOBALS.update(
    domains=_SEQUENCE_DOMAINS,
    _transition_expected=_transition_expected,
    _program_expected=_program_expected,
    _fail=_fail,
)
_VERIFY_HISTORICAL = FunctionType(
    previous._VERIFY_HISTORICAL.__code__,  # noqa: SLF001
    _VERIFY_GLOBALS,
    name="_verify_v178r1_historical_receipt_lifecycle",
)


_V178_WRAPPER_FIELDS = {
    "source_v174_shape_sequence_id",
    "certificate_local_model_delta_receipts",
    "certificate_local_model_delta_receipt_count",
    "delta_transition_joins",
    "delta_transition_join_count",
    "terminal_delta_not_consumed_because_no_later_planning_epoch",
    "indexed_lazy_invalidation_decision_compute_events",
    "serialized_full_graph_rows_scanned_for_invalidation_decision",
    "production_full_graph_diff_checks",
    "production_live_dependency_projection_scan_count",
    "production_prior_receipt_event_scan_count",
    "retained_authorization_metadata_update_count",
    "lazy_authorization_receipts",
    "lazy_authorization_receipt_count",
    "lazy_authorization_issuance_joins",
    "lazy_authorization_issuance_join_count",
    "lazy_authorization_metadata_update_count",
    "lazy_epoch_receipt_append_count",
    "graph_receipt_reverse_index_update_count",
    "program_receipt_reverse_index_update_count",
    "graph_receipt_reverse_index_lookup_count",
    "program_receipt_reverse_index_lookup_count",
    "producer_free_dependency_and_full_graph_controls_required",
    "certificate_reverse_index_drives_minimal_invalidation",
    "prior_receipt_reverse_index_drives_issuance_lookup",
    "retained_authorization_is_lazy_on_actual_hit",
    "receipt_dependency_lifecycle_eagerly_updates_retained_metadata",
}


def _historical_view(sequence):
    historical = {
        key: value
        for key, value in sequence.items()
        if key not in previous.previous.previous._V168_WRAPPER_FIELDS  # noqa: SLF001
        and key not in _V178_WRAPPER_FIELDS
        and key not in {"schema", "sequence_id"}
    }
    historical["schema"] = "acfqp.receipt_driven_minimal_invalidation_sequence.v174"
    historical["sequence_id"] = sequence["source_v174_shape_sequence_id"]
    payload = {key: value for key, value in historical.items() if key != "sequence_id"}
    if historical["sequence_id"] != domains_v178.extension_content_id_v178(
        domains_v178.CONSTRUCTION_K7_SEQUENCE_V178_DOMAIN, payload
    ):
        _fail("V178r1 independent historical sequence projection changed")
    return historical


def _build_program_groups(sequence):
    receipts = sequence["online_plan_issuance_receipts"]
    ordinal = 0
    current_state = sequence["episodes"][0][
        "standalone_model_state_id_before_episode"
    ]
    program_receipts = []
    groups = []
    for episode in sequence["episodes"]:
        state = episode["standalone_model_state_id_before_episode"]
        if state != current_state:
            groups.append(
                {
                    "previous_state": current_state,
                    "current_state": state,
                    "program_receipts": program_receipts,
                }
            )
            current_state = state
            program_receipts = []
        for _wrapper in episode["abstract_plan_receipts"]:
            receipt = receipts[ordinal]
            if receipt["typed_plan_source"] in {
                "DIRECT_COMPILED_PROGRAM_ORDER",
                "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE",
            }:
                program_receipts.append(receipt)
            ordinal += 1
    if ordinal != len(receipts):
        _fail("V178r1 independent program receipt cardinality changed")
    return groups


def _verify_lazy_lifecycle(sequence, transitions):
    projections = {
        row["dependency_projection_id"]: row
        for row in sequence["online_dependency_projections"]
    }
    receipts = sequence["online_plan_issuance_receipts"]
    expected_lazy = []
    expected_joins = []
    authorization = {}
    ledger = []
    ordinal = 0
    graph_updates = program_updates = lazy_appends = 0
    for episode_offset, episode in enumerate(sequence["episodes"]):
        for _wrapper in episode["abstract_plan_receipts"]:
            receipt = receipts[ordinal]
            ordinal += 1
            typed = receipt["typed_plan_source"]
            if typed not in {
                "OBSERVATION_DERIVED_QUOTIENT_ORDER",
                "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
            }:
                program_updates += 1
                continue
            graph_updates += 1
            projection = projections.get(receipt["dependency_projection_id"])
            if projection is None:
                _fail("V178r1 independent lazy receipt projection is absent")
            dependency_id = projection["quotient_dependency_receipt_id"]
            if typed == "OBSERVATION_DERIVED_QUOTIENT_ORDER":
                if dependency_id in authorization:
                    _fail("V178r1 independent graph cache birth is duplicated")
                authorization[dependency_id] = {
                    "cursor": len(ledger),
                    "graph_id": projection["current_quotient_graph_id"],
                }
                continue
            state = authorization.get(dependency_id)
            if state is None:
                _fail("V178r1 independent lazy authorization has no live dependency")
            if state["cursor"] == len(ledger):
                continue
            suffix = ledger[state["cursor"] :]
            if any(
                dependency_id in row["invalidated_dependency_receipt_ids"]
                for row in suffix
            ):
                _fail("V178r1 invalidated dependency reached lazy reconstruction")
            payload = {
                "schema": "acfqp.lazy_epoch_authorization.v178",
                "quotient_dependency_receipt_id": dependency_id,
                "source_epoch_cursor": state["cursor"],
                "current_epoch_cursor": len(ledger),
                "consumed_epoch_transition_receipt_ids": [
                    row["epoch_transition_receipt_id"] for row in suffix
                ],
                "previous_authorized_quotient_graph_id": state["graph_id"],
                "current_authorized_quotient_graph_id": projection[
                    "current_quotient_graph_id"
                ],
                "dependency_projection_rescan_count": 0,
                "prior_receipt_event_scan_count": 0,
                "authorization_metadata_updated_only_on_actual_cache_hit": True,
                "lazy_authorization_is_ordering_not_safety_authority": True,
            }
            lazy = {
                **payload,
                "lazy_authorization_receipt_id": domains_v178.extension_content_id_v178(
                    domains_v178.CONSTRUCTION_K7_LAZY_AUTHORIZATION_V178_DOMAIN,
                    payload,
                ),
            }
            expected_lazy.append(lazy)
            join_payload = {
                "schema": "acfqp.lazy_authorization_issuance_join.v178",
                "join_ordinal": len(expected_joins),
                "lazy_authorization_receipt_id": lazy[
                    "lazy_authorization_receipt_id"
                ],
                "online_plan_issuance_receipt_id": receipt[
                    "online_plan_issuance_receipt_id"
                ],
                "quotient_dependency_receipt_id": dependency_id,
                "dependency_projection_id": receipt["dependency_projection_id"],
                "authorization_completed_before_issuance": True,
                "issuance_completed_before_orderer_return": True,
                "join_is_ordering_not_safety_authority": True,
            }
            expected_joins.append(
                {
                    **join_payload,
                    "lazy_authorization_issuance_join_id": (
                        domains_v178.extension_content_id_v178(
                            domains_v178.CONSTRUCTION_K7_LAZY_AUTHORIZATION_JOIN_V178_DOMAIN,
                            join_payload,
                        )
                    ),
                }
            )
            lazy_appends += len(suffix)
            state["cursor"] = len(ledger)
            state["graph_id"] = projection["current_quotient_graph_id"]
        if episode_offset < len(transitions):
            transition = transitions[episode_offset]
            for dependency_id in transition["invalidated_dependency_receipt_ids"]:
                authorization.pop(dependency_id, None)
            ledger.append(transition)
    if ordinal != len(receipts):
        _fail("V178r1 independent lazy issuance cardinality changed")
    if not (
        canonical_json_bytes(expected_lazy)
        == canonical_json_bytes(sequence["lazy_authorization_receipts"])
        and canonical_json_bytes(expected_joins)
        == canonical_json_bytes(sequence["lazy_authorization_issuance_joins"])
    ):
        _fail("V178r1 independent lazy authorization reconstruction changed")
    program_rows = sequence["receipt_driven_program_cache_invalidation_receipts"]
    return {
        "lazy_receipts": len(expected_lazy),
        "lazy_joins": len(expected_joins),
        "lazy_updates": len(expected_lazy),
        "lazy_epoch_appends": lazy_appends,
        "graph_index_updates": graph_updates,
        "program_index_updates": program_updates,
        "graph_index_lookups": sum(
            row["prior_receipt_reverse_index_lookups"] for row in transitions
        ),
        "program_index_lookups": sum(
            row["prior_receipt_reverse_index_lookups"] for row in program_rows
        ),
    }


def _verify_sequence(sequence, replayed):
    global _CONTEXT
    payload = {key: value for key, value in sequence.items() if key != "sequence_id"}
    if sequence.get("sequence_id") != domains_v178.extension_content_id_v178(
        domains_v178.CONSTRUCTION_K7_SEQUENCE_V178_DOMAIN, payload
    ):
        _fail("V178r1 independent sequence identity changed")
    deltas = sequence["certificate_local_model_delta_receipts"]
    if len(deltas) != len(sequence["episodes"]):
        _fail("V178r1 independent delta/episode cardinality changed")
    context = {
        "sequence": sequence,
        "deltas": deltas,
        "delta_cursor": 0,
        "rules": None,
        "expected_transitions": [],
        "verifier_full_graph_checks": [],
        "verifier_full_dependency_checks": [],
        "program_groups": _build_program_groups(sequence),
        "program_cursor": 0,
        "program_receipt_index": defaultdict(set),
    }
    if _CONTEXT is not None:
        _fail("V178r1 independent verifier is reentrant")
    _CONTEXT = context
    try:
        summary = _VERIFY_HISTORICAL(_historical_view(sequence), replayed)
    finally:
        _CONTEXT = None
    if not (
        context["delta_cursor"] == len(deltas) - 1
        and context["rules"] is not None
        and context["program_cursor"] == len(context["program_groups"])
    ):
        _fail("V178r1 independent transition consumption changed")
    final_delta = _expected_delta(sequence, len(deltas) - 1, context["rules"])
    if canonical_json_bytes(final_delta) != canonical_json_bytes(deltas[-1]):
        _fail("V178r1 independent terminal delta reconstruction changed")
    joins = []
    for ordinal, (delta, transition) in enumerate(
        zip(deltas, context["expected_transitions"], strict=False)
    ):
        join_payload = {
            "schema": "acfqp.certificate_delta_transition_join.v178",
            "join_ordinal": ordinal,
            "certificate_delta_receipt_id": delta["certificate_delta_receipt_id"],
            "epoch_transition_receipt_id": transition[
                "epoch_transition_receipt_id"
            ],
            "delta_changed_projected_states": delta["changed_projected_states"],
            "delta_issued_before_transition_decision": True,
            "delta_frontier_exactly_drives_transition": True,
            "production_full_graph_control_absent": True,
            "production_live_dependency_projection_scan_absent": True,
            "production_prior_receipt_event_scan_absent": True,
            "retained_metadata_eager_update_absent": True,
            "join_is_cache_maintenance_not_safety_authority": True,
        }
        joins.append(
            {
                **join_payload,
                "delta_transition_join_id": domains_v178.extension_content_id_v178(
                    domains_v178.CONSTRUCTION_K7_DELTA_TRANSITION_JOIN_V178_DOMAIN,
                    join_payload,
                ),
            }
        )
    decision_compute = sum(
        deltas[index]["delta_derivation_compute_events"]
        + context["expected_transitions"][index][
            "reverse_dependency_index_lookups"
        ]
        + context["expected_transitions"][index][
            "prior_receipt_reverse_index_lookups"
        ]
        for index in range(len(joins))
    )
    lazy = _verify_lazy_lifecycle(sequence, context["expected_transitions"])
    if not (
        canonical_json_bytes(joins)
        == canonical_json_bytes(sequence["delta_transition_joins"])
        and sequence["certificate_local_model_delta_receipt_count"] == len(deltas)
        and sequence["delta_transition_join_count"] == len(joins)
        and sequence["terminal_delta_not_consumed_because_no_later_planning_epoch"]
        == deltas[-1]["certificate_delta_receipt_id"]
        and sequence["indexed_lazy_invalidation_decision_compute_events"]
        == decision_compute
        and sequence["serialized_full_graph_rows_scanned_for_invalidation_decision"]
        == 0
        and sequence["production_full_graph_diff_checks"] == 0
        and sequence["production_live_dependency_projection_scan_count"] == 0
        and sequence["production_prior_receipt_event_scan_count"] == 0
        and sequence["retained_authorization_metadata_update_count"] == 0
        and sequence["lazy_authorization_receipt_count"] == lazy["lazy_receipts"]
        and sequence["lazy_authorization_issuance_join_count"] == lazy["lazy_joins"]
        and sequence["lazy_authorization_metadata_update_count"]
        == lazy["lazy_updates"]
        and sequence["lazy_epoch_receipt_append_count"] == lazy["lazy_epoch_appends"]
        and sequence["graph_receipt_reverse_index_update_count"]
        == lazy["graph_index_updates"]
        and sequence["program_receipt_reverse_index_update_count"]
        == lazy["program_index_updates"]
        and sequence["graph_receipt_reverse_index_lookup_count"]
        == lazy["graph_index_lookups"]
        and sequence["program_receipt_reverse_index_lookup_count"]
        == lazy["program_index_lookups"]
        and sequence["producer_free_dependency_and_full_graph_controls_required"]
        is True
        and sequence["certificate_reverse_index_drives_minimal_invalidation"]
        is True
        and sequence["prior_receipt_reverse_index_drives_issuance_lookup"] is True
        and sequence["retained_authorization_is_lazy_on_actual_hit"] is True
        and sequence[
            "receipt_dependency_lifecycle_eagerly_updates_retained_metadata"
        ]
        is False
        and sequence["receipt_dependency_lifecycle_is_model_or_safety_authority"]
        is False
        and sequence["query_local_exact_overlay_remains_only_safety_authority"]
        is True
    ):
        _fail("V178r1 independent indexed-lazy sequence accounting changed")
    return {
        **summary,
        "delta_receipts": len(deltas),
        "delta_transition_joins": len(joins),
        "indexed_lazy_decision_compute": decision_compute,
        "production_full_graph_diff_checks": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_prior_receipt_event_scan_count": 0,
        "retained_authorization_metadata_updates": 0,
        **lazy,
        "verifier_full_graph_diff_checks": sum(
            context["verifier_full_graph_checks"]
        ),
        "verifier_full_dependency_projection_checks": sum(
            context["verifier_full_dependency_checks"]
        ),
        "verified_control_transition_count": len(joins),
    }


def _replay(args):
    config, family, seed, bank_raw, verification_raw, classifier_raw = args
    return previous.previous.previous.previous.base._BASE_V168(  # noqa: SLF001
        config,
        family=family,
        seed=seed,
        episode_indices=EPISODES,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_raw,
    )


def _input_fact(preregistration, name):
    rows = [row for row in preregistration["frozen_input_facts"] if row["name"] == name]
    if len(rows) != 1:
        _fail(f"V178r1 independent preregistration input missing: {name}")
    return rows[0]


def _verify_input(raw, fact, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == fact["byte_count"]
        and hashlib.sha256(raw).hexdigest() == fact["sha256"]
        and fact[identity_key] == identity
        and document.get(identity_key) == identity
    ):
        _fail(f"V178r1 independent runtime input changed: {name}")
    return document


def _source_v178_occurrence(row):
    metrics = row["indexed_lazy_invalidation_metrics"]
    r1_gate = row["registered_gate"]
    base_gate = {
        key: value
        for key, value in r1_gate.items()
        if key
        not in {
            "passed",
            "receipt_reverse_indices_constructed",
            "receipt_reverse_index_lookup_matches_invalidation_demand",
            "zero_invalidation_requires_zero_receipt_lookup",
        }
    }
    base_gate["receipt_reverse_indices_are_live"] = (
        metrics["receipt_reverse_index_updates"] > 0
        and metrics["receipt_reverse_index_lookups"] > 0
    )
    base_gate["passed"] = all(
        value for value in base_gate.values() if type(value) is bool
    )
    payload = {
        **{
            key: value
            for key, value in row.items()
            if key
            not in {
                "schema",
                "occurrence_id",
                "source_v178_occurrence_id",
                "preserved_v178_failure_id",
                "registered_gate",
                "sample_tax_claim_scope",
            }
        },
        "schema": "acfqp.indexed_lazy_invalidation_occurrence.v178",
        "registered_gate": base_gate,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V178_CROSS_FAMILY_COHORT",
    }
    return domains_v178.extension_content_id_v178(
        domains_v178.CONSTRUCTION_K7_OCCURRENCE_V178_DOMAIN, payload
    ), base_gate


def verify_indexed_lazy_invalidation_campaign_v178r1(
    preregistration_raw: bytes,
    campaign_raw: bytes,
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v177_campaign_raw: bytes,
    v177_verification_raw: bytes,
    v178_failure_raw: bytes,
):
    preregistration = _frozen(
        preregistration_raw,
        count=PREREGISTRATION_BYTE_COUNT,
        digest=PREREGISTRATION_SHA256,
        identity_key="preregistration_id",
        identity=PREREGISTRATION_ID,
        name="preregistration",
    )
    campaign = _frozen(
        campaign_raw,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=CAMPAIGN_ID,
        name="campaign",
    )
    classifier = _verify_input(
        classifier_raw,
        _input_fact(preregistration, "v161_paid_path_prefix_classifier_receipt.json"),
        "classifier_receipt_id",
        CLASSIFIER_ID,
        "classifier",
    )
    bank = _verify_input(
        bank_raw,
        _input_fact(preregistration, "v146_anonymous_relational_factor_bank.json"),
        "bank_id",
        "78bb4dae4682ed0cedb7a7781caca4af04986f0db86d7086a0786166d07020b5",
        "bank",
    )
    bank_verification = _verify_input(
        bank_verification_raw,
        _input_fact(
            preregistration,
            "v146_anonymous_relational_factor_bank_verification.json",
        ),
        "verification_id",
        "7531dcc153b64ba8c23ae70fce84650b0be0550acaf3db915b106adf2bd6e63b",
        "bank verification",
    )
    predecessor = _verify_input(
        v177_campaign_raw,
        _input_fact(
            preregistration, "v177_reverse_index_only_invalidation_campaign.json"
        ),
        "campaign_id",
        V177_CAMPAIGN_ID,
        "V177 campaign",
    )
    predecessor_verification = _verify_input(
        v177_verification_raw,
        _input_fact(
            preregistration,
            "v177_reverse_index_only_invalidation_verification.json",
        ),
        "verification_id",
        V177_VERIFICATION_ID,
        "V177 verification",
    )
    failure = _verify_input(
        v178_failure_raw,
        _input_fact(preregistration, "v178_indexed_lazy_invalidation_failure.json"),
        "failure_id",
        V178_FAILURE_ID,
        "V178 failure",
    )
    campaign_payload = {
        key: value for key, value in campaign.items() if key != "campaign_id"
    }
    if not (
        campaign["campaign_id"]
        == domains.extension_content_id_v178r1(
            domains.CONSTRUCTION_K7_CAMPAIGN_V178R1_DOMAIN, campaign_payload
        )
        and campaign["preregistration_id"] == preregistration["preregistration_id"]
        and campaign["preserved_v178_failure_id"] == failure["failure_id"]
        and campaign["frozen_v177_campaign_id"] == predecessor["campaign_id"]
        and campaign["frozen_v177_verification_id"]
        == predecessor_verification["verification_id"]
        and predecessor["registered_gate"]["passed"] is True
        and predecessor_verification[
            "reverse_index_full_dependency_control_equality_independently_verified"
        ]
        is True
        and failure["same_identity_rerun_forbidden"] is True
        and failure["scientific_success_claimed"] is False
        and bank_verification["bank_id"] == bank["bank_id"]
        and classifier["classifier_receipt_id"] == CLASSIFIER_ID
        and preregistration["target_worker_count"] == TARGET_WORKERS
        and preregistration["target_episode_indices"] == list(EPISODES)
    ):
        _fail("V178r1 independent campaign ancestry changed")
    config = previous.previous.previous.previous.base._config()  # noqa: SLF001
    args = [
        (config, family, seed, bank_raw, bank_verification_raw, classifier_raw)
        for family, seed, _role in TARGETS
    ]
    with ProcessPoolExecutor(max_workers=TARGET_WORKERS) as executor:
        replayed = list(executor.map(_replay, args))
    rows = campaign["target_occurrences"]
    if len(rows) != len(replayed) or len(rows) != len(TARGETS):
        _fail("V178r1 independent target cardinality changed")
    histogram = {
        source: 0
        for source in previous.previous.previous.previous.TAXONOMY.values()
    }
    total_keys = (
        "issuance",
        "joins",
        "graph_invalidations",
        "graph_retentions",
        "program_invalidations",
        "incremental",
        "delta_receipts",
        "delta_transition_joins",
        "indexed_lazy_decision_compute",
        "production_full_graph_diff_checks",
        "production_live_dependency_projection_scan_count",
        "production_prior_receipt_event_scan_count",
        "retained_authorization_metadata_updates",
        "lazy_updates",
        "lazy_receipts",
        "lazy_joins",
        "graph_index_updates",
        "program_index_updates",
        "graph_index_lookups",
        "program_index_lookups",
        "verifier_full_graph_diff_checks",
        "verifier_full_dependency_projection_checks",
        "verified_control_transition_count",
    )
    totals = {key: 0 for key in total_keys}
    factor_avoided = query_avoided = 0
    occurrence_ids = []
    source_occurrence_ids = []
    roles = set()
    for (family, seed, role), replay, row in zip(
        TARGETS, replayed, rows, strict=True
    ):
        if not (
            row["target_family"] == family
            and row["seed"] == seed
            and row["episode_indices"] == list(EPISODES)
            and row["registered_indexed_lazy_role"] == role
            and canonical_json_bytes(row["progressive_prior_acquisition"])
            == canonical_json_bytes(replay["progressive_prior_acquisition"])
            and canonical_json_bytes(row["progressive_strict_acquisition"])
            == canonical_json_bytes(replay["progressive_strict_acquisition"])
            and row["factor_prior_sample_reduction_within_progressive_policy"]
            == replay["factor_prior_sample_reduction_within_progressive_policy"]
            and row["query_policy_sample_reduction_vs_legacy_path_first"]
            == replay["query_policy_sample_reduction_vs_legacy_path_first"]
        ):
            _fail("V178r1 independent occurrence target replay changed")
        prior = _verify_sequence(
            row["progressive_prior_sequence"], replay["progressive_prior_sequence"]
        )
        strict = _verify_sequence(
            row["progressive_strict_sequence"], replay["progressive_strict_sequence"]
        )
        summary = {key: prior[key] + strict[key] for key in total_keys}
        row_histogram = {
            source: prior["histogram"][source] + strict["histogram"][source]
            for source in histogram
        }
        source_occurrence_id, base_gate = _source_v178_occurrence(row)
        metrics = {
            "graph_invalidations": summary["graph_invalidations"],
            "graph_retentions": summary["graph_retentions"],
            "program_invalidations": summary["program_invalidations"],
            "incremental_revalidations": summary["incremental"],
            "delta_receipts": summary["delta_receipts"],
            "delta_transition_joins": summary["delta_transition_joins"],
            "indexed_lazy_decision_compute": summary[
                "indexed_lazy_decision_compute"
            ],
            "production_full_graph_diff_checks": 0,
            "production_live_dependency_projection_scan_count": 0,
            "production_prior_receipt_event_scan_count": 0,
            "retained_authorization_metadata_updates": 0,
            "lazy_authorization_metadata_updates": summary["lazy_updates"],
            "lazy_authorization_receipts": summary["lazy_receipts"],
            "lazy_authorization_issuance_joins": summary["lazy_joins"],
            "receipt_reverse_index_updates": summary["graph_index_updates"]
            + summary["program_index_updates"],
            "receipt_reverse_index_lookups": summary["graph_index_lookups"]
            + summary["program_index_lookups"],
        }
        expected_gate = {
            key: value
            for key, value in base_gate.items()
            if key not in {"passed", "receipt_reverse_indices_are_live"}
        }
        invalidations = metrics["graph_invalidations"] + metrics[
            "program_invalidations"
        ]
        expected_gate.update(
            receipt_reverse_indices_constructed=metrics[
                "receipt_reverse_index_updates"
            ]
            > 0,
            receipt_reverse_index_lookup_matches_invalidation_demand=(
                metrics["receipt_reverse_index_lookups"] > 0
                if invalidations > 0
                else metrics["receipt_reverse_index_lookups"] == 0
            ),
            zero_invalidation_requires_zero_receipt_lookup=(
                invalidations != 0
                or metrics["receipt_reverse_index_lookups"] == 0
            ),
        )
        expected_gate["passed"] = all(
            value for value in expected_gate.values() if type(value) is bool
        )
        row_payload = {key: value for key, value in row.items() if key != "occurrence_id"}
        if not (
            row["occurrence_id"]
            == domains.extension_content_id_v178r1(
                domains.CONSTRUCTION_K7_OCCURRENCE_V178R1_DOMAIN, row_payload
            )
            and row["source_v178_occurrence_id"] == source_occurrence_id
            and row["preserved_v178_failure_id"] == V178_FAILURE_ID
            and row["online_typed_plan_source_histogram"] == row_histogram
            and row["online_plan_issuance_receipt_count"] == summary["issuance"]
            and row["online_execution_join_receipt_count"] == summary["joins"]
            and row["indexed_lazy_invalidation_metrics"] == metrics
            and row["registered_gate"] == expected_gate
            and row["registered_gate"]["passed"] is True
            and row["production_prior_receipt_event_scan_present"] is False
            and row["eager_retained_authorization_update_present"] is False
            and row["producer_free_dependency_and_full_graph_controls_required"]
            is True
            and row["indexed_lazy_invalidation_is_model_or_safety_authority"]
            is False
        ):
            _fail("V178r1 independent occurrence accounting changed")
        for source in histogram:
            histogram[source] += row_histogram[source]
        for key in totals:
            totals[key] += summary[key]
        factor_avoided += row[
            "factor_prior_sample_reduction_within_progressive_policy"
        ]
        query_avoided += row["query_policy_sample_reduction_vs_legacy_path_first"]
        occurrence_ids.append(row["occurrence_id"])
        source_occurrence_ids.append(source_occurrence_id)
        roles.add(role)
    expected_metrics = {
        "graph_invalidations": totals["graph_invalidations"],
        "graph_retentions": totals["graph_retentions"],
        "program_invalidations": totals["program_invalidations"],
        "incremental_revalidations": totals["incremental"],
        "delta_receipts": totals["delta_receipts"],
        "delta_transition_joins": totals["delta_transition_joins"],
        "indexed_lazy_decision_compute": totals["indexed_lazy_decision_compute"],
        "production_full_graph_diff_checks": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_prior_receipt_event_scan_count": 0,
        "retained_authorization_metadata_updates": 0,
        "lazy_authorization_metadata_updates": totals["lazy_updates"],
        "lazy_authorization_receipts": totals["lazy_receipts"],
        "lazy_authorization_issuance_joins": totals["lazy_joins"],
        "receipt_reverse_index_updates": totals["graph_index_updates"]
        + totals["program_index_updates"],
        "receipt_reverse_index_lookups": totals["graph_index_lookups"]
        + totals["program_index_lookups"],
    }
    expected_accounting = {
        "online_plan_issuance_receipt_count": totals["issuance"],
        "online_execution_join_receipt_count": totals["joins"],
        **expected_metrics,
        "factor_prior_labels_avoided": factor_avoided,
        "query_policy_labels_avoided": query_avoided,
        "sample_labels_execution_steps_derivation_planning_receipt_delta_index_and_lazy_maintenance_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = campaign["registered_gate"]
    if not (
        campaign["target_occurrence_ids"] == occurrence_ids
        and campaign["online_typed_plan_source_histogram"] == histogram
        and campaign["accounting"] == expected_accounting
        and roles
        == {
            "INDEXED_INVALIDATION_AND_LAZY_PROGRAM_AUTHORIZATION",
            "INDEXED_RETENTION_AND_LAZY_GRAPH_AUTHORIZATION",
        }
        and gate["required_occurrence_count"] == len(rows)
        and gate["passed_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
        and gate["passed"] is True
        and all(histogram[source] > 0 for source in histogram)
        and totals["graph_invalidations"] > 0
        and totals["graph_retentions"] > 0
        and totals["program_invalidations"] > 0
        and totals["incremental"] > 0
        and totals["production_prior_receipt_event_scan_count"] == 0
        and totals["retained_authorization_metadata_updates"] == 0
        and totals["lazy_updates"] == totals["lazy_receipts"]
        == totals["lazy_joins"]
        > 0
        and totals["graph_index_updates"] + totals["program_index_updates"] > 0
        and totals["graph_index_lookups"] + totals["program_index_lookups"] > 0
        and totals["verifier_full_graph_diff_checks"] > 0
        and totals["verifier_full_dependency_projection_checks"] > 0
        and totals["verified_control_transition_count"]
        == totals["delta_transition_joins"]
        and factor_avoided > 0
        and query_avoided >= 0
        and campaign["indexed_lazy_invalidation_observed"] is True
        and campaign["factor_prior_sample_tax_reduction_observed"] is True
        and campaign["production_prior_receipt_event_scan_present"] is False
        and campaign["eager_retained_authorization_update_present"] is False
        and campaign["indexed_lazy_invalidation_changes_selected_action_order"]
        is False
        and campaign["indexed_lazy_invalidation_is_model_or_safety_authority"]
        is False
        and campaign["query_local_exact_overlay_remains_only_safety_authority"]
        is True
        and campaign["complete_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    ):
        _fail("V178r1 independent aggregate or claim boundary changed")
    verification_payload = {
        "schema": "acfqp.indexed_lazy_invalidation_verification.v178r1",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_id": CAMPAIGN_ID,
        "preserved_v178_failure_id": V178_FAILURE_ID,
        "frozen_v177_campaign_id": V177_CAMPAIGN_ID,
        "frozen_v177_verification_id": V177_VERIFICATION_ID,
        "classifier_receipt_id": CLASSIFIER_ID,
        "verified_target_families": [family for family, _seed, _role in TARGETS],
        "verified_target_seeds": [seed for _family, seed, _role in TARGETS],
        "verified_occurrence_ids": occurrence_ids,
        "verified_source_v178_occurrence_ids": source_occurrence_ids,
        "verified_online_plan_issuance_receipt_count": totals["issuance"],
        "verified_online_execution_join_receipt_count": totals["joins"],
        "verified_online_typed_plan_source_histogram": histogram,
        "verified_graph_dependency_invalidations": totals["graph_invalidations"],
        "verified_graph_dependency_retentions": totals["graph_retentions"],
        "verified_compiled_program_invalidations": totals["program_invalidations"],
        "verified_incrementally_revalidated_plan_receipts": totals["incremental"],
        "verified_certificate_local_delta_receipts": totals["delta_receipts"],
        "verified_delta_transition_joins": totals["delta_transition_joins"],
        "verified_indexed_lazy_decision_compute_events": totals[
            "indexed_lazy_decision_compute"
        ],
        "verified_production_full_graph_diff_checks": 0,
        "verified_production_live_dependency_projection_scan_count": 0,
        "verified_production_prior_receipt_event_scan_count": 0,
        "verified_retained_authorization_metadata_updates": 0,
        "verified_lazy_authorization_receipts": totals["lazy_receipts"],
        "verified_lazy_authorization_issuance_joins": totals["lazy_joins"],
        "verified_receipt_reverse_index_updates": totals["graph_index_updates"]
        + totals["program_index_updates"],
        "verified_receipt_reverse_index_lookups": totals["graph_index_lookups"]
        + totals["program_index_lookups"],
        "verified_producer_free_full_graph_diff_control_checks": totals[
            "verifier_full_graph_diff_checks"
        ],
        "verified_producer_free_full_dependency_projection_checks": totals[
            "verifier_full_dependency_projection_checks"
        ],
        "verified_reverse_index_full_control_equality_count": totals[
            "verified_control_transition_count"
        ],
        "verified_factor_prior_labels_avoided": factor_avoided,
        "verified_query_policy_labels_avoided": query_avoided,
        "producer_free_target_outcome_reexecution": True,
        "producer_free_certificate_delta_reconstruction": True,
        "producer_free_dependency_reverse_index_reconstruction": True,
        "producer_free_issuance_reverse_index_reconstruction": True,
        "producer_free_lazy_authorization_reconstruction": True,
        "producer_free_lazy_authorization_issuance_join_reconstruction": True,
        "producer_free_full_dependency_projection_control": True,
        "producer_free_full_graph_diff_control": True,
        "zero_production_full_graph_diff_control_independently_verified": True,
        "zero_production_live_dependency_projection_scan_independently_verified": True,
        "zero_production_prior_receipt_event_scan_independently_verified": True,
        "zero_eager_retained_authorization_update_independently_verified": True,
        "reverse_index_full_dependency_control_equality_independently_verified": True,
        "delta_frontier_full_diff_control_equality_independently_verified": True,
        "production_and_verifier_control_compute_axes_separate": True,
        "factor_prior_sample_tax_reduction_independently_verified": True,
        "indexed_lazy_lifecycle_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v178r1(
            domains.CONSTRUCTION_K7_VERIFICATION_V178R1_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V178r1 frozen independent verification changed")
    return document


__all__ = (
    "VERIFICATION_ID",
    "verify_indexed_lazy_invalidation_campaign_v178r1",
)
