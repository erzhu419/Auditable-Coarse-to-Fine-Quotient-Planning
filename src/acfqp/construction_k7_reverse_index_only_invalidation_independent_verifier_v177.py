"""Producer-free verification of V177 reverse-index invalidation evidence."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v174 as domains_v174
from acfqp import construction_k7_domain_registry_extension_v177 as domains
from acfqp import construction_k7_certificate_delta_only_invalidation_independent_verifier_v176 as previous
from acfqp.generic_packet_batching_adapter_v134 import FAMILY as PACKET_FAMILY
from acfqp.generic_reservoir_dispatch_adapter_v171 import FAMILY as RESERVOIR_FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "cf84908966e68f5cb8f7a344aa44521564a0d8231b6e588c9f3c621adc2e9414"
PREREGISTRATION_BYTE_COUNT = 4_260
PREREGISTRATION_SHA256 = "2348808e08169b9a7c0369633b7d2e37d47a7fe725993ee3769b4134b00311a3"
CAMPAIGN_ID = "cf9e0bf64ba285d3b1873e5d48636a4de0e68006d7c3e43d761ebbf4a9d5f985"
CAMPAIGN_BYTE_COUNT = 51_141_161
CAMPAIGN_SHA256 = "0eb4c40eac1869ba85b24bb578eb746a37ae56d1f170ad21876bdeb8413dd478"
V176_CAMPAIGN_ID = "8d6d1348e67084b449debf5671cb568eb6b048eb56358bf3bbe20c4161255953"
V176_VERIFICATION_ID = "ac6b3a604c49423cbac35154bf1a0dbea15b65e6723e9471bd9990822de1968f"
CLASSIFIER_ID = "893a5b0597fe2c9d0544defcf3655ce6e186950e7c1342a7a7502de0d4f1378d"
TARGETS = (
    (PACKET_FAMILY, 1_179_851, "REVERSE_INDEX_GRAPH_AND_COMPILED_INVALIDATION"),
    (PACKET_FAMILY, 1_179_852, "REVERSE_INDEX_GRAPH_AND_COMPILED_INVALIDATION"),
    (
        RESERVOIR_FAMILY,
        1_189_851,
        "REVERSE_INDEX_RETENTION_AND_INCREMENTAL_REVALIDATION",
    ),
    (
        RESERVOIR_FAMILY,
        1_189_852,
        "REVERSE_INDEX_RETENTION_AND_INCREMENTAL_REVALIDATION",
    ),
)
EPISODES = (1_053, 1_054, 1_055, 1_056)
TARGET_WORKERS = 2
VERIFICATION_ID = "1f062589b9db53758691431dec327c0d303f20d06bd6b44c647eca02a11c76dd"
EXPECTED_CANONICAL_BYTE_COUNT = 3_611
EXPECTED_CANONICAL_SHA256 = "2d63f83a8ce12a200721107692768ff1e49f96d479e7d2809d35d9c4e8f1180d"


class ConstructionK7ReverseIndexOnlyInvalidationIndependentVerifierV177Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReverseIndexOnlyInvalidationIndependentVerifierV177Error(
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
        _fail(f"V177 independent frozen {name} changed")
    return document


def _sequence_content_id(domain_tag, payload):
    if domain_tag == domains.CONSTRUCTION_K7_SEQUENCE_V177_DOMAIN:
        return domains.extension_content_id_v177(domain_tag, payload)
    return domains_v174.extension_content_id_v174(domain_tag, payload)


_SEQUENCE_DOMAINS = SimpleNamespace(**domains_v174.__dict__)
_SEQUENCE_DOMAINS.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN = (
    domains.CONSTRUCTION_K7_SEQUENCE_V177_DOMAIN
)
_SEQUENCE_DOMAINS.extension_content_id_v174 = _sequence_content_id


_DELTA_CONTEXT = None


def _adjacency(model: Mapping[str, Any]):
    return previous.previous.previous._adjacency(model)  # noqa: SLF001


def _expected_delta(sequence, offset, rules):
    source = previous._expected_delta(sequence, offset, rules)  # noqa: SLF001
    payload = {
        **{
            key: value
            for key, value in source.items()
            if key not in {"schema", "certificate_delta_receipt_id"}
        },
        "schema": "acfqp.certificate_local_model_delta.v177",
    }
    return {
        **payload,
        "certificate_delta_receipt_id": domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_CERTIFICATE_DELTA_V177_DOMAIN, payload
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
    context = _DELTA_CONTEXT
    if context is None:
        _fail("V177 independent delta context is absent")
    offset = context["cursor"]
    expected_delta = _expected_delta(context["sequence"], offset, rules)
    actual_delta = context["deltas"][offset]
    if canonical_json_bytes(expected_delta) != canonical_json_bytes(actual_delta):
        _fail("V177 independent certificate-local delta reconstruction changed")
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
        _fail("V177 independent delta/full-graph frontier mismatch")
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
    reconstructed_reverse_index = defaultdict(set)
    for identity, states in dependency_states.items():
        for state in states:
            reconstructed_reverse_index[state].add(identity)
    reverse_index_invalidated = set(active) if rules_changed else set()
    if not rules_changed:
        for state in changed:
            reverse_index_invalidated.update(reconstructed_reverse_index.get(state, ()))
    if reverse_index_invalidated != full_dependency_invalidated:
        _fail("V177 independent reverse-index/full-dependency control mismatch")
    invalidated = reverse_index_invalidated
    retained = set(active) - invalidated
    affected_receipts = sorted(
        receipt["online_plan_issuance_receipt_id"]
        for receipt, dependency_id in graph_events
        if dependency_id in invalidated
    )
    retained_receipts = sorted(
        receipt["online_plan_issuance_receipt_id"]
        for receipt, dependency_id in graph_events
        if dependency_id in retained
    )
    event_count = sum(
        len(episode["abstract_plan_receipts"])
        for episode in context["sequence"]["episodes"][: offset + 1]
    )
    payload = {
        "schema": "acfqp.reverse_index_model_epoch_transition.v177",
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
        "invalidated_online_plan_issuance_receipt_ids": affected_receipts,
        "retained_online_plan_issuance_receipt_ids": retained_receipts,
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": 0,
        "production_full_graph_diff_checks": 0,
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_live_cache_identity_enumeration_count": len(active),
        "production_prior_receipt_event_scan_count": event_count,
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
    context["cursor"] += 1
    return transition, invalidated, retained


_VERIFY_GLOBALS = dict(previous._VERIFY_HISTORICAL.__globals__)  # noqa: SLF001
_VERIFY_GLOBALS.update(
    domains=_SEQUENCE_DOMAINS,
    _transition_expected=_transition_expected,
    _fail=_fail,
)
_VERIFY_HISTORICAL = FunctionType(
    previous._VERIFY_HISTORICAL.__code__,  # noqa: SLF001
    _VERIFY_GLOBALS,
    name="_verify_v177_historical_receipt_lifecycle",
)


_V177_WRAPPER_FIELDS = {
    "source_v174_shape_sequence_id",
    "certificate_local_model_delta_receipts",
    "certificate_local_model_delta_receipt_count",
    "delta_transition_joins",
    "delta_transition_join_count",
    "terminal_delta_not_consumed_because_no_later_planning_epoch",
    "reverse_index_invalidation_decision_compute_events",
    "serialized_full_graph_rows_scanned_for_invalidation_decision",
    "production_full_graph_diff_checks",
    "production_live_dependency_projection_scan_count",
    "production_prior_receipt_event_scan_count",
    "retained_authorization_metadata_update_count",
    "producer_free_dependency_and_full_graph_controls_required",
    "certificate_reverse_index_drives_minimal_invalidation",
}


def _historical_view(sequence):
    historical = {
        key: value
        for key, value in sequence.items()
        if key not in previous.previous._V168_WRAPPER_FIELDS  # noqa: SLF001
        and key not in _V177_WRAPPER_FIELDS
        and key not in {"schema", "sequence_id"}
    }
    historical["schema"] = "acfqp.receipt_driven_minimal_invalidation_sequence.v174"
    historical["sequence_id"] = sequence["source_v174_shape_sequence_id"]
    payload = {key: value for key, value in historical.items() if key != "sequence_id"}
    if historical["sequence_id"] != domains.extension_content_id_v177(
        domains.CONSTRUCTION_K7_SEQUENCE_V177_DOMAIN, payload
    ):
        _fail("V177 independent historical sequence projection changed")
    return historical


def _verify_sequence(sequence, replayed):
    global _DELTA_CONTEXT
    payload = {key: value for key, value in sequence.items() if key != "sequence_id"}
    if sequence.get("sequence_id") != domains.extension_content_id_v177(
        domains.CONSTRUCTION_K7_SEQUENCE_V177_DOMAIN, payload
    ):
        _fail("V177 independent sequence identity changed")
    deltas = sequence["certificate_local_model_delta_receipts"]
    if len(deltas) != len(sequence["episodes"]):
        _fail("V177 independent delta/episode cardinality changed")
    context = {
        "sequence": sequence,
        "deltas": deltas,
        "cursor": 0,
        "rules": None,
        "expected_transitions": [],
        "verifier_full_graph_checks": [],
        "verifier_full_dependency_checks": [],
    }
    if _DELTA_CONTEXT is not None:
        _fail("V177 independent delta verifier is reentrant")
    _DELTA_CONTEXT = context
    try:
        summary = _VERIFY_HISTORICAL(_historical_view(sequence), replayed)
    finally:
        _DELTA_CONTEXT = None
    if context["cursor"] != len(deltas) - 1 or context["rules"] is None:
        _fail("V177 independent transition/delta consumption changed")
    final_delta = _expected_delta(sequence, len(deltas) - 1, context["rules"])
    if canonical_json_bytes(final_delta) != canonical_json_bytes(deltas[-1]):
        _fail("V177 independent terminal delta reconstruction changed")
    joins = []
    for ordinal, (delta, transition) in enumerate(
        zip(deltas, context["expected_transitions"], strict=False)
    ):
        join_payload = {
            "schema": "acfqp.certificate_delta_transition_join.v177",
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
            "join_is_cache_maintenance_not_safety_authority": True,
        }
        joins.append(
            {
                **join_payload,
                "delta_transition_join_id": domains.extension_content_id_v177(
                    domains.CONSTRUCTION_K7_DELTA_TRANSITION_JOIN_V177_DOMAIN,
                    join_payload,
                ),
            }
        )
    decision_compute = sum(
        deltas[index]["delta_derivation_compute_events"]
        + context["expected_transitions"][index]["reverse_dependency_index_lookups"]
        for index in range(len(joins))
    )
    event_scans = sum(
        row["production_prior_receipt_event_scan_count"]
        for row in context["expected_transitions"]
    )
    retained_updates = sum(
        row["retained_authorization_metadata_updates"]
        for row in context["expected_transitions"]
    )
    if not (
        canonical_json_bytes(joins)
        == canonical_json_bytes(sequence["delta_transition_joins"])
        and sequence["certificate_local_model_delta_receipt_count"] == len(deltas)
        and sequence["delta_transition_join_count"] == len(joins)
        and sequence["terminal_delta_not_consumed_because_no_later_planning_epoch"]
        == deltas[-1]["certificate_delta_receipt_id"]
        and sequence["reverse_index_invalidation_decision_compute_events"]
        == decision_compute
        and sequence["serialized_full_graph_rows_scanned_for_invalidation_decision"]
        == 0
        and sequence["production_full_graph_diff_checks"] == 0
        and sequence["production_live_dependency_projection_scan_count"] == 0
        and sequence["production_prior_receipt_event_scan_count"] == event_scans
        and sequence["retained_authorization_metadata_update_count"]
        == retained_updates
        and sequence["producer_free_dependency_and_full_graph_controls_required"]
        is True
        and sequence["certificate_reverse_index_drives_minimal_invalidation"] is True
        and sequence["receipt_dependency_lifecycle_is_model_or_safety_authority"]
        is False
        and sequence["query_local_exact_overlay_remains_only_safety_authority"]
        is True
    ):
        _fail("V177 independent reverse-index sequence accounting changed")
    return {
        **summary,
        "delta_receipts": len(deltas),
        "delta_transition_joins": len(joins),
        "reverse_index_decision_compute": decision_compute,
        "production_full_graph_diff_checks": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_prior_receipt_event_scan_count": event_scans,
        "retained_authorization_metadata_updates": retained_updates,
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
    return previous.previous.previous.base._BASE_V168(  # noqa: SLF001
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
        _fail(f"V177 independent preregistration input missing: {name}")
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
        _fail(f"V177 independent runtime input changed: {name}")
    return document


def verify_reverse_index_only_invalidation_campaign_v177(
    preregistration_raw: bytes,
    campaign_raw: bytes,
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v176_campaign_raw: bytes,
    v176_verification_raw: bytes,
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
        v176_campaign_raw,
        _input_fact(
            preregistration,
            "v176_certificate_delta_only_invalidation_campaign.json",
        ),
        "campaign_id",
        V176_CAMPAIGN_ID,
        "V176 campaign",
    )
    predecessor_verification = _verify_input(
        v176_verification_raw,
        _input_fact(
            preregistration,
            "v176_certificate_delta_only_invalidation_verification.json",
        ),
        "verification_id",
        V176_VERIFICATION_ID,
        "V176 verification",
    )
    campaign_payload = {
        key: value for key, value in campaign.items() if key != "campaign_id"
    }
    if not (
        campaign["campaign_id"]
        == domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_CAMPAIGN_V177_DOMAIN, campaign_payload
        )
        and campaign["preregistration_id"] == preregistration["preregistration_id"]
        and campaign["frozen_v176_campaign_id"] == predecessor["campaign_id"]
        and campaign["frozen_v176_verification_id"]
        == predecessor_verification["verification_id"]
        and predecessor["registered_gate"]["passed"] is True
        and predecessor["accounting"]["production_full_graph_diff_checks"] == 0
        and predecessor_verification["verified_production_full_graph_diff_checks"]
        == 0
        and predecessor_verification[
            "delta_frontier_full_diff_control_equality_independently_verified"
        ]
        is True
        and bank_verification["bank_id"] == bank["bank_id"]
        and classifier["classifier_receipt_id"] == CLASSIFIER_ID
        and preregistration["target_worker_count"] == TARGET_WORKERS
        and preregistration["target_episode_indices"] == list(EPISODES)
    ):
        _fail("V177 independent campaign ancestry changed")
    config = previous.previous.previous.base._config()  # noqa: SLF001
    args = [
        (config, family, seed, bank_raw, bank_verification_raw, classifier_raw)
        for family, seed, _role in TARGETS
    ]
    with ProcessPoolExecutor(max_workers=TARGET_WORKERS) as executor:
        replayed = list(executor.map(_replay, args))
    rows = campaign["target_occurrences"]
    if len(rows) != len(replayed) or len(rows) != len(TARGETS):
        _fail("V177 independent target cardinality changed")
    histogram = {
        source: 0 for source in previous.previous.previous.TAXONOMY.values()
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
        "reverse_index_decision_compute",
        "production_full_graph_diff_checks",
        "production_live_dependency_projection_scan_count",
        "production_prior_receipt_event_scan_count",
        "retained_authorization_metadata_updates",
        "verifier_full_graph_diff_checks",
        "verifier_full_dependency_projection_checks",
        "verified_control_transition_count",
    )
    totals = {key: 0 for key in total_keys}
    factor_avoided = query_avoided = 0
    occurrence_ids = []
    roles = set()
    for (family, seed, role), replay, row in zip(
        TARGETS, replayed, rows, strict=True
    ):
        if not (
            row["target_family"] == family
            and row["seed"] == seed
            and row["episode_indices"] == list(EPISODES)
            and row["registered_delta_dependency_role"] == role
            and canonical_json_bytes(row["progressive_prior_acquisition"])
            == canonical_json_bytes(replay["progressive_prior_acquisition"])
            and canonical_json_bytes(row["progressive_strict_acquisition"])
            == canonical_json_bytes(replay["progressive_strict_acquisition"])
            and row["factor_prior_sample_reduction_within_progressive_policy"]
            == replay["factor_prior_sample_reduction_within_progressive_policy"]
            and row["query_policy_sample_reduction_vs_legacy_path_first"]
            == replay["query_policy_sample_reduction_vs_legacy_path_first"]
        ):
            _fail("V177 independent occurrence target replay changed")
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
        row_payload = {key: value for key, value in row.items() if key != "occurrence_id"}
        expected_metrics = {
            "graph_invalidations": summary["graph_invalidations"],
            "graph_retentions": summary["graph_retentions"],
            "program_invalidations": summary["program_invalidations"],
            "incremental_revalidations": summary["incremental"],
            "delta_receipts": summary["delta_receipts"],
            "delta_transition_joins": summary["delta_transition_joins"],
            "reverse_index_decision_compute": summary[
                "reverse_index_decision_compute"
            ],
            "production_full_graph_diff_checks": 0,
            "production_live_dependency_projection_scan_count": 0,
            "production_prior_receipt_event_scan_count": summary[
                "production_prior_receipt_event_scan_count"
            ],
            "retained_authorization_metadata_updates": summary[
                "retained_authorization_metadata_updates"
            ],
        }
        if not (
            row["occurrence_id"]
            == domains.extension_content_id_v177(
                domains.CONSTRUCTION_K7_OCCURRENCE_V177_DOMAIN, row_payload
            )
            and row["online_typed_plan_source_histogram"] == row_histogram
            and row["online_plan_issuance_receipt_count"] == summary["issuance"]
            and row["online_execution_join_receipt_count"] == summary["joins"]
            and row["delta_invalidation_metrics"] == expected_metrics
            and row["registered_gate"]["passed"] is True
            and row["production_full_graph_diff_control_present"] is False
            and row["production_live_dependency_projection_scan_present"] is False
            and row["producer_free_dependency_and_full_graph_controls_required"]
            is True
            and row["delta_invalidation_is_model_or_safety_authority"] is False
        ):
            _fail("V177 independent occurrence accounting changed")
        for source in histogram:
            histogram[source] += row_histogram[source]
        for key in totals:
            totals[key] += summary[key]
        factor_avoided += row[
            "factor_prior_sample_reduction_within_progressive_policy"
        ]
        query_avoided += row["query_policy_sample_reduction_vs_legacy_path_first"]
        occurrence_ids.append(row["occurrence_id"])
        roles.add(role)
    accounting = campaign["accounting"]
    expected_accounting = {
        "online_plan_issuance_receipt_count": totals["issuance"],
        "online_execution_join_receipt_count": totals["joins"],
        "graph_invalidations": totals["graph_invalidations"],
        "graph_retentions": totals["graph_retentions"],
        "program_invalidations": totals["program_invalidations"],
        "incremental_revalidations": totals["incremental"],
        "delta_receipts": totals["delta_receipts"],
        "delta_transition_joins": totals["delta_transition_joins"],
        "reverse_index_decision_compute": totals["reverse_index_decision_compute"],
        "production_full_graph_diff_checks": 0,
        "production_live_dependency_projection_scan_count": 0,
        "production_prior_receipt_event_scan_count": totals[
            "production_prior_receipt_event_scan_count"
        ],
        "retained_authorization_metadata_updates": totals[
            "retained_authorization_metadata_updates"
        ],
        "factor_prior_labels_avoided": factor_avoided,
        "query_policy_labels_avoided": query_avoided,
        "sample_labels_execution_steps_derivation_planning_receipt_delta_index_and_maintenance_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    if not (
        campaign["target_occurrence_ids"] == occurrence_ids
        and campaign["online_typed_plan_source_histogram"] == histogram
        and accounting == expected_accounting
        and roles
        == {
            "REVERSE_INDEX_GRAPH_AND_COMPILED_INVALIDATION",
            "REVERSE_INDEX_RETENTION_AND_INCREMENTAL_REVALIDATION",
        }
        and all(histogram[source] > 0 for source in histogram)
        and totals["graph_invalidations"] > 0
        and totals["graph_retentions"] > 0
        and totals["program_invalidations"] > 0
        and totals["incremental"] > 0
        and totals["production_full_graph_diff_checks"] == 0
        and totals["production_live_dependency_projection_scan_count"] == 0
        and totals["verifier_full_graph_diff_checks"] > 0
        and totals["verifier_full_dependency_projection_checks"] > 0
        and totals["verified_control_transition_count"]
        == totals["delta_transition_joins"]
        and factor_avoided > 0
        and query_avoided >= 0
        and campaign["registered_gate"]["passed"] is True
        and campaign["reverse_index_only_invalidation_observed"] is True
        and campaign["factor_prior_sample_tax_reduction_observed"] is True
        and campaign["production_full_graph_diff_control_present"] is False
        and campaign["production_live_dependency_projection_scan_present"] is False
        and campaign["producer_free_dependency_and_full_graph_controls_required"]
        is True
        and campaign["delta_invalidation_changes_selected_action_order"] is False
        and campaign["delta_invalidation_is_model_or_safety_authority"] is False
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
        _fail("V177 independent aggregate or claim boundary changed")
    verification_payload = {
        "schema": "acfqp.reverse_index_only_invalidation_verification.v177",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_id": CAMPAIGN_ID,
        "frozen_v176_campaign_id": V176_CAMPAIGN_ID,
        "frozen_v176_verification_id": V176_VERIFICATION_ID,
        "classifier_receipt_id": CLASSIFIER_ID,
        "verified_target_families": [family for family, _seed, _role in TARGETS],
        "verified_target_seeds": [seed for _family, seed, _role in TARGETS],
        "verified_occurrence_ids": occurrence_ids,
        "verified_online_plan_issuance_receipt_count": totals["issuance"],
        "verified_online_execution_join_receipt_count": totals["joins"],
        "verified_online_typed_plan_source_histogram": histogram,
        "verified_graph_dependency_invalidations": totals["graph_invalidations"],
        "verified_graph_dependency_retentions": totals["graph_retentions"],
        "verified_compiled_program_invalidations": totals["program_invalidations"],
        "verified_incrementally_revalidated_plan_receipts": totals["incremental"],
        "verified_certificate_local_delta_receipts": totals["delta_receipts"],
        "verified_delta_transition_joins": totals["delta_transition_joins"],
        "verified_reverse_index_decision_compute_events": totals[
            "reverse_index_decision_compute"
        ],
        "verified_production_full_graph_diff_checks": 0,
        "verified_production_live_dependency_projection_scan_count": 0,
        "verified_production_prior_receipt_event_scan_count": totals[
            "production_prior_receipt_event_scan_count"
        ],
        "verified_retained_authorization_metadata_updates": totals[
            "retained_authorization_metadata_updates"
        ],
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
        "producer_free_reverse_dependency_index_reconstruction": True,
        "producer_free_full_dependency_projection_control": True,
        "producer_free_full_graph_diff_control": True,
        "producer_free_delta_transition_join_reconstruction": True,
        "producer_free_program_invalidation_reconstruction": True,
        "producer_free_incremental_revalidation_chain_reconstruction": True,
        "producer_free_online_issuance_and_execution_join_reconstruction": True,
        "zero_production_full_graph_diff_control_independently_verified": True,
        "zero_production_live_dependency_projection_scan_independently_verified": True,
        "reverse_index_full_dependency_control_equality_independently_verified": True,
        "delta_frontier_full_diff_control_equality_independently_verified": True,
        "production_and_verifier_control_compute_axes_separate": True,
        "factor_prior_sample_tax_reduction_independently_verified": True,
        "delta_lifecycle_is_model_or_safety_authority": False,
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
        "verification_id": domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_VERIFICATION_V177_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V177 frozen independent verification changed")
    return document


__all__ = (
    "VERIFICATION_ID",
    "verify_reverse_index_only_invalidation_campaign_v177",
)
