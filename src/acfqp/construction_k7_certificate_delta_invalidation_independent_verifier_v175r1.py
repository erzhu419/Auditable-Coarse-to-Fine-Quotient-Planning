"""Producer-free verification of the successful V175r1 evidence.

This verifier does not import the V175/V175r1 producer, campaign core, or
sequence implementation.  It reexecutes target outcomes through the retained
V172 independent runner, reconstructs every certificate-local delta from the
stored episode/model facts, and independently rebuilds the receipt-driven
invalidation, retention, revalidation, and execution-join lifecycle.
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v174 as domains_v174
from acfqp import construction_k7_domain_registry_extension_v175 as domains_v175
from acfqp import construction_k7_domain_registry_extension_v175r1 as domains
from acfqp import construction_k7_receipt_driven_invalidation_independent_verifier_v174 as previous
from acfqp.generic_packet_batching_adapter_v134 import FAMILY as PACKET_FAMILY
from acfqp.generic_reservoir_dispatch_adapter_v171 import FAMILY as RESERVOIR_FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "6c0a89a8267f87ed18e2e898c74eb94c6f4e5c3b0f98f5090c4e48cb23b00ff8"
PREREGISTRATION_BYTE_COUNT = 4_894
PREREGISTRATION_SHA256 = "90020a85870fcdb960613daccab47790964814fc927d632c95099577d600a691"
CAMPAIGN_ID = "6552685740a9244d3a9b77c3bfdf78ce065cc98bbc8f2348cf0826c247c72f63"
CAMPAIGN_BYTE_COUNT = 59_473_200
CAMPAIGN_SHA256 = "31f4846627ed9750401b13a906dbc91b3242506c43e7df61fc3a14b7e4b2edf2"
V175_FAILURE_ID = "431ac86701677586b6b8a95a75a7b9153941a75f7581703edec1637da8e0e476"
V175_FAILURE_BYTE_COUNT = 1_812
V175_FAILURE_SHA256 = "323f55deb1287dacff7df3759a54be54b5325d0fecf9715189b5f6ae15140dcd"
CLASSIFIER_ID = "893a5b0597fe2c9d0544defcf3655ce6e186950e7c1342a7a7502de0d4f1378d"
TARGETS = (
    (PACKET_FAMILY, 1_139_861, "DELTA_GRAPH_AND_COMPILED_INVALIDATION"),
    (PACKET_FAMILY, 1_139_862, "DELTA_GRAPH_AND_COMPILED_INVALIDATION"),
    (RESERVOIR_FAMILY, 1_149_861, "DELTA_RETENTION_AND_INCREMENTAL_REVALIDATION"),
    (RESERVOIR_FAMILY, 1_149_862, "DELTA_RETENTION_AND_INCREMENTAL_REVALIDATION"),
)
EPISODES = (1_045, 1_046, 1_047, 1_048)
TARGET_WORKERS = 2
VERIFICATION_ID = "bd5276748e2e136381c2058ff5c9f95c6ca55e4a1faf03cf43adbb48878240c0"
EXPECTED_CANONICAL_BYTE_COUNT = 2_978
EXPECTED_CANONICAL_SHA256 = "31470c5194dac8c59086b86a6e269a7a555746895b4d61239ae34024f3ebf85c"


class ConstructionK7CertificateDeltaInvalidationIndependentVerifierV175R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateDeltaInvalidationIndependentVerifierV175R1Error(
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
        _fail(f"V175r1 independent frozen {name} changed")
    return document


def _v174_or_v175_sequence_content_id(domain_tag, payload):
    if domain_tag == domains_v175.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN:
        return domains_v175.extension_content_id_v175(domain_tag, payload)
    return domains_v174.extension_content_id_v174(domain_tag, payload)


_SEQUENCE_DOMAINS = SimpleNamespace(**domains_v174.__dict__)
_SEQUENCE_DOMAINS.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN = (
    domains_v175.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN
)
_SEQUENCE_DOMAINS.extension_content_id_v174 = _v174_or_v175_sequence_content_id


_DELTA_CONTEXT = None


def _adjacency(model: Mapping[str, Any]):
    return previous._adjacency(model)  # noqa: SLF001


def _expected_delta(sequence, offset, rules):
    episode = sequence["episodes"][offset]
    previous_model = sequence["quotient_models_before_each_episode"][offset]
    current_model = sequence["quotient_models_after_each_episode"][offset]
    before_edges = {
        (tuple(row["projected_pre"]), row["action_key"], tuple(row["projected_post"]))
        for row in previous_model["projected_edge_rows"]
    }
    after_edges = {
        (tuple(row["projected_pre"]), row["action_key"], tuple(row["projected_post"]))
        for row in current_model["projected_edge_rows"]
    }
    inserted = sorted(after_edges - before_edges)
    removed = sorted(before_edges - after_edges)
    if removed:
        _fail("V175r1 independent registered monotone delta removed an edge")
    changed_states = sorted({pre for pre, _action, _post in inserted})
    input_rows = episode["raw_incremental_transition_rows"]
    update = episode["standalone_model_update_after_episode"]
    payload = {
        "schema": "acfqp.certificate_local_model_delta.v175",
        "previous_successor_state_id": episode[
            "standalone_model_state_id_before_episode"
        ],
        "current_successor_state_id": episode[
            "standalone_model_state_id_after_episode"
        ],
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "source_incremental_update_receipt_id": update["update_receipt_id"],
        "delta_input_raw_row_count": len(input_rows),
        "delta_input_raw_rows_sha256": previous._sha(input_rows),  # noqa: SLF001
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
        "previous_terminal_projection_rule": [dict(row) for row in rules],
        "current_terminal_projection_rule": [dict(row) for row in rules],
        "terminal_projection_rule_changed": False,
        "delta_derivation_compute_events": len(input_rows) + len(inserted),
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "changed_state_frontier_derived_from_incremental_state_indices": True,
        "only_certificate_local_post_failure_rows_enter_delta": True,
        "delta_receipt_is_cache_maintenance_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "certificate_delta_receipt_id": domains_v175.extension_content_id_v175(
            domains_v175.CONSTRUCTION_K7_CERTIFICATE_DELTA_V175_DOMAIN, payload
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
    context = _DELTA_CONTEXT
    if context is None:
        _fail("V175r1 independent delta context is absent")
    offset = context["cursor"]
    expected_delta = _expected_delta(context["sequence"], offset, rules)
    actual_delta = context["deltas"][offset]
    if canonical_json_bytes(expected_delta) != canonical_json_bytes(actual_delta):
        _fail("V175r1 independent certificate-local delta reconstruction changed")
    previous_adjacency = _adjacency(previous_model)
    current_adjacency = _adjacency(current_model)
    changed = tuple(tuple(row) for row in expected_delta["changed_projected_states"])
    all_states = tuple(sorted(set(previous_adjacency) | set(current_adjacency)))
    matched_changed = tuple(
        state
        for state in all_states
        if previous_adjacency.get(state, ()) != current_adjacency.get(state, ())
    )
    if changed != matched_changed:
        _fail("V175r1 independent delta/full-diff frontier mismatch")
    changed_set = set(changed)
    invalidated = {
        identity
        for identity in active
        if {
            tuple(row["projected_state"])
            for row in dependencies[identity]["ordered_bfs_dependency_rows"]
        }
        & changed_set
    }
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
    changed_rows = [
        {
            "projected_state": list(state),
            "previous_outgoing_edges": [
                {"action_key": key, "projected_post": list(post)}
                for key, post in previous_adjacency.get(state, ())
            ],
            "current_outgoing_edges": [
                {"action_key": key, "projected_post": list(post)}
                for key, post in current_adjacency.get(state, ())
            ],
        }
        for state in changed
    ]
    matched_checks = sum(
        1
        + len(previous_adjacency.get(state, ()))
        + len(current_adjacency.get(state, ()))
        for state in all_states
    ) + 2 * len(rules)
    payload = {
        "schema": "acfqp.delta_driven_model_epoch_transition.v175",
        "certificate_delta_receipt_id": expected_delta[
            "certificate_delta_receipt_id"
        ],
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "quotient_graph_identity_equal": previous_model["quotient_graph_id"]
        == current_model["quotient_graph_id"],
        "identity_short_circuit_applied": previous_model["quotient_graph_id"]
        == current_model["quotient_graph_id"],
        "previous_terminal_projection_rule": [dict(row) for row in rules],
        "current_terminal_projection_rule": [dict(row) for row in rules],
        "terminal_projection_rule_changed": False,
        "delta_derived_changed_projected_state_rows": changed_rows,
        "delta_derived_changed_projected_state_count": len(changed_rows),
        "cache_entry_ids_before_transition": sorted(active),
        "dependency_projection_ids_by_dependency_receipt_id": {
            identity: sorted(projection_ids[identity]) for identity in sorted(active)
        },
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "invalidated_online_plan_issuance_receipt_ids": affected_receipts,
        "retained_online_plan_issuance_receipt_ids": retained_receipts,
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": 0,
        "delta_dependency_projection_checks": sum(
            len(dependencies[identity]["ordered_bfs_dependency_rows"])
            for identity in active
        ),
        "serialized_full_graph_rows_scanned_for_invalidation_decision": 0,
        "matched_full_graph_diff_checks": matched_checks,
        "matched_full_graph_diff_changed_states": [
            list(state) for state in matched_changed
        ],
        "delta_decision_precedes_matched_full_graph_diff": True,
        "matched_full_graph_diff_used_only_as_uncharged_control": True,
        "reverse_dependency_index_lookups": len(changed),
        "receipt_dependency_projection_drove_invalidation": True,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    transition = {
        **payload,
        "epoch_transition_receipt_id": domains_v175.extension_content_id_v175(
            domains_v175.CONSTRUCTION_K7_EPOCH_TRANSITION_V175_DOMAIN, payload
        ),
    }
    context["expected_transitions"].append(transition)
    context["rules"] = [dict(row) for row in rules]
    context["cursor"] += 1
    return transition, invalidated, retained


_VERIFY_GLOBALS = dict(previous._verify_sequence.__globals__)  # noqa: SLF001
_VERIFY_GLOBALS.update(
    domains=_SEQUENCE_DOMAINS,
    _transition_expected=_transition_expected,
    _fail=_fail,
)
_VERIFY_HISTORICAL = FunctionType(
    previous._verify_sequence.__code__,  # noqa: SLF001
    _VERIFY_GLOBALS,
    name="_verify_v175_historical_receipt_lifecycle",
)


_V175_WRAPPER_FIELDS = {
    "source_v174_shape_sequence_id",
    "certificate_local_model_delta_receipts",
    "certificate_local_model_delta_receipt_count",
    "delta_transition_joins",
    "delta_transition_join_count",
    "terminal_delta_not_consumed_because_no_later_planning_epoch",
    "delta_driven_invalidation_decision_compute_events",
    "serialized_full_graph_rows_scanned_for_invalidation_decision",
    "matched_full_graph_diff_control_checks",
    "full_graph_diff_checks_avoided_on_invalidation_decision_path",
    "certificate_local_delta_drives_changed_state_frontier",
    "matched_full_graph_diff_is_only_uncharged_control",
}


_V168_WRAPPER_FIELDS = {
    "source_v154_sequence_id",
    "applicable_plan_receipt_mode",
    "applicable_plan_receipt_modes",
    "registered_plan_receipt_set_class",
    "abstract_plan_receipt_count_by_registered_mode",
    "actual_v109_receipt_count_by_registered_mode",
    "registered_plan_receipt_set_totalized",
    "at_least_one_registered_plan_mode_exercised",
    "mixed_registered_plan_mode_sequence",
    "empty_registered_plan_mode_set_is_failure",
    "none_path_defers_to_v109_and_query_local_certificate",
    "each_abstract_receipt_contains_one_concrete_plan_document",
    "multiple_registered_modes_mean_temporal_receipt_use_not_action_competition",
    "all_executed_actions_have_v109_receipts",
    "registered_plan_mode_set_changes_planning_or_execution",
    "registered_plan_mode_set_is_safety_authority",
}


def _v175_source_view(sequence):
    source = {
        key: value
        for key, value in sequence.items()
        if key not in _V168_WRAPPER_FIELDS and key not in {"schema", "sequence_id"}
    }
    source["schema"] = "acfqp.certificate_delta_driven_invalidation_sequence.v175"
    source["sequence_id"] = sequence["source_v154_sequence_id"]
    payload = {key: value for key, value in source.items() if key != "sequence_id"}
    if source["sequence_id"] != domains_v175.extension_content_id_v175(
        domains_v175.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN, payload
    ):
        _fail("V175r1 independent V168 source projection changed")
    return source


def _historical_view(sequence):
    historical = {
        key: value
        for key, value in sequence.items()
        if key not in _V175_WRAPPER_FIELDS and key not in {"schema", "sequence_id"}
    }
    historical["schema"] = "acfqp.receipt_driven_minimal_invalidation_sequence.v174"
    historical["sequence_id"] = sequence["source_v174_shape_sequence_id"]
    payload = {key: value for key, value in historical.items() if key != "sequence_id"}
    if historical["sequence_id"] != domains_v175.extension_content_id_v175(
        domains_v175.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN, payload
    ):
        _fail("V175r1 independent historical sequence projection changed")
    return historical


def _verify_sequence(sequence, replayed):
    global _DELTA_CONTEXT
    payload = {key: value for key, value in sequence.items() if key != "sequence_id"}
    if sequence.get("sequence_id") != domains_v175.extension_content_id_v175(
        domains_v175.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN, payload
    ):
        _fail("V175r1 independent sequence identity changed")
    deltas = sequence["certificate_local_model_delta_receipts"]
    if len(deltas) != len(sequence["episodes"]):
        _fail("V175r1 independent delta/episode cardinality changed")
    context = {
        "sequence": sequence,
        "deltas": deltas,
        "cursor": 0,
        "rules": None,
        "expected_transitions": [],
    }
    if _DELTA_CONTEXT is not None:
        _fail("V175r1 independent delta verifier is reentrant")
    _DELTA_CONTEXT = context
    try:
        summary = _VERIFY_HISTORICAL(
            _historical_view(_v175_source_view(sequence)), replayed
        )
    finally:
        _DELTA_CONTEXT = None
    if context["cursor"] != len(deltas) - 1 or context["rules"] is None:
        _fail("V175r1 independent transition/delta consumption changed")
    final_delta = _expected_delta(sequence, len(deltas) - 1, context["rules"])
    if canonical_json_bytes(final_delta) != canonical_json_bytes(deltas[-1]):
        _fail("V175r1 independent terminal delta reconstruction changed")
    joins = []
    for ordinal, (delta, transition) in enumerate(
        zip(deltas, context["expected_transitions"], strict=False)
    ):
        join_payload = {
            "schema": "acfqp.certificate_delta_transition_join.v175",
            "join_ordinal": ordinal,
            "certificate_delta_receipt_id": delta["certificate_delta_receipt_id"],
            "epoch_transition_receipt_id": transition[
                "epoch_transition_receipt_id"
            ],
            "delta_changed_projected_states": delta["changed_projected_states"],
            "transition_changed_projected_states": [
                row["projected_state"]
                for row in transition["delta_derived_changed_projected_state_rows"]
            ],
            "delta_issued_before_transition_decision": True,
            "delta_frontier_exactly_drives_transition": True,
            "join_is_cache_maintenance_not_safety_authority": True,
        }
        joins.append(
            {
                **join_payload,
                "delta_transition_join_id": domains_v175.extension_content_id_v175(
                    domains_v175.CONSTRUCTION_K7_DELTA_TRANSITION_JOIN_V175_DOMAIN,
                    join_payload,
                ),
            }
        )
    control_checks = sum(
        row["matched_full_graph_diff_checks"]
        for row in context["expected_transitions"]
    )
    delta_compute = sum(
        row["delta_derivation_compute_events"] for row in deltas[:-1]
    )
    if not (
        canonical_json_bytes(joins)
        == canonical_json_bytes(sequence["delta_transition_joins"])
        and sequence["certificate_local_model_delta_receipt_count"] == len(deltas)
        and sequence["delta_transition_join_count"] == len(joins)
        and sequence["terminal_delta_not_consumed_because_no_later_planning_epoch"]
        == deltas[-1]["certificate_delta_receipt_id"]
        and sequence["delta_driven_invalidation_decision_compute_events"]
        == delta_compute
        and sequence["serialized_full_graph_rows_scanned_for_invalidation_decision"]
        == 0
        and sequence["matched_full_graph_diff_control_checks"] == control_checks
        and sequence[
            "full_graph_diff_checks_avoided_on_invalidation_decision_path"
        ]
        == control_checks
        and sequence["certificate_local_delta_drives_changed_state_frontier"]
        is True
        and sequence["matched_full_graph_diff_is_only_uncharged_control"] is True
        and sequence["receipt_dependency_lifecycle_is_model_or_safety_authority"]
        is False
        and sequence["query_local_exact_overlay_remains_only_safety_authority"]
        is True
    ):
        _fail("V175r1 independent delta sequence accounting changed")
    return {
        **summary,
        "delta_receipts": len(deltas),
        "delta_transition_joins": len(joins),
        "delta_decision_compute": delta_compute,
        "full_graph_control_checks": control_checks,
        "full_graph_diff_checks_avoided": control_checks,
    }


def _replay(args):
    config, family, seed, bank_raw, verification_raw, classifier_raw = args
    return previous.base._BASE_V168(  # noqa: SLF001
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
        _fail(f"V175r1 independent preregistration input missing: {name}")
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
        _fail(f"V175r1 independent runtime input changed: {name}")
    return document


def verify_certificate_delta_invalidation_campaign_v175r1(
    preregistration_raw: bytes,
    campaign_raw: bytes,
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v175_failure_raw: bytes,
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
    failure = _frozen(
        v175_failure_raw,
        count=V175_FAILURE_BYTE_COUNT,
        digest=V175_FAILURE_SHA256,
        identity_key="failure_id",
        identity=V175_FAILURE_ID,
        name="V175 failure",
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
    campaign_payload = {
        key: value for key, value in campaign.items() if key != "campaign_id"
    }
    if not (
        campaign["campaign_id"]
        == domains.extension_content_id_v175r1(
            domains.CONSTRUCTION_K7_CAMPAIGN_V175R1_DOMAIN, campaign_payload
        )
        and campaign["preregistration_id"] == preregistration["preregistration_id"]
        and campaign["frozen_v175_failure_id"] == failure["failure_id"]
        and campaign["corrected_classifier_receipt_id"]
        == classifier["classifier_receipt_id"]
        and campaign["same_v175_preregistration_identity_reused"] is False
        and failure["same_preregistration_identity_may_be_rerun"] is False
        and failure["target_outcomes_accessed"] is False
        and bank_verification["bank_id"] == bank["bank_id"]
        and preregistration["target_worker_count"] == TARGET_WORKERS
        and preregistration["target_episode_indices"] == list(EPISODES)
    ):
        _fail("V175r1 independent campaign ancestry changed")
    config = previous.base._config()  # noqa: SLF001
    args = [
        (config, family, seed, bank_raw, bank_verification_raw, classifier_raw)
        for family, seed, _role in TARGETS
    ]
    with ProcessPoolExecutor(max_workers=TARGET_WORKERS) as executor:
        replayed = list(executor.map(_replay, args))
    rows = campaign["target_occurrences"]
    if len(rows) != len(replayed) or len(rows) != len(TARGETS):
        _fail("V175r1 independent target cardinality changed")
    histogram = {source: 0 for source in previous.TAXONOMY.values()}
    total_keys = (
        "issuance",
        "joins",
        "graph_invalidations",
        "graph_retentions",
        "program_invalidations",
        "incremental",
        "delta_receipts",
        "delta_transition_joins",
        "delta_decision_compute",
        "full_graph_control_checks",
        "full_graph_diff_checks_avoided",
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
            and row["frozen_v175_failure_id"] == V175_FAILURE_ID
            and row["corrected_classifier_receipt_id"] == CLASSIFIER_ID
            and canonical_json_bytes(row["progressive_prior_acquisition"])
            == canonical_json_bytes(replay["progressive_prior_acquisition"])
            and canonical_json_bytes(row["progressive_strict_acquisition"])
            == canonical_json_bytes(replay["progressive_strict_acquisition"])
            and row["factor_prior_sample_reduction_within_progressive_policy"]
            == replay["factor_prior_sample_reduction_within_progressive_policy"]
            and row["query_policy_sample_reduction_vs_legacy_path_first"]
            == replay["query_policy_sample_reduction_vs_legacy_path_first"]
        ):
            _fail("V175r1 independent occurrence target replay changed")
        prior = _verify_sequence(
            row["progressive_prior_sequence"], replay["progressive_prior_sequence"]
        )
        strict = _verify_sequence(
            row["progressive_strict_sequence"], replay["progressive_strict_sequence"]
        )
        summary = {
            key: prior[key] + strict[key]
            for key in total_keys
        }
        row_histogram = {
            source: prior["histogram"][source] + strict["histogram"][source]
            for source in histogram
        }
        row_payload = {
            key: value for key, value in row.items() if key != "occurrence_id"
        }
        if not (
            row["occurrence_id"]
            == domains.extension_content_id_v175r1(
                domains.CONSTRUCTION_K7_OCCURRENCE_V175R1_DOMAIN, row_payload
            )
            and row["online_typed_plan_source_histogram"] == row_histogram
            and row["online_plan_issuance_receipt_count"] == summary["issuance"]
            and row["online_execution_join_receipt_count"] == summary["joins"]
            and row["delta_invalidation_metrics"]
            == {
                "graph_invalidations": summary["graph_invalidations"],
                "graph_retentions": summary["graph_retentions"],
                "program_invalidations": summary["program_invalidations"],
                "incremental_revalidations": summary["incremental"],
                "delta_receipts": summary["delta_receipts"],
                "delta_transition_joins": summary["delta_transition_joins"],
                "delta_decision_compute": summary["delta_decision_compute"],
                "full_graph_control_checks": summary["full_graph_control_checks"],
                "full_graph_diff_checks_avoided": summary[
                    "full_graph_diff_checks_avoided"
                ],
            }
            and row["registered_gate"]["passed"] is True
            and row["delta_invalidation_is_model_or_safety_authority"] is False
        ):
            _fail("V175r1 independent occurrence accounting changed")
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
        "delta_decision_compute": totals["delta_decision_compute"],
        "full_graph_control_checks": totals["full_graph_control_checks"],
        "full_graph_diff_checks_avoided": totals[
            "full_graph_diff_checks_avoided"
        ],
        "factor_prior_labels_avoided": factor_avoided,
        "query_policy_labels_avoided": query_avoided,
        "sample_labels_execution_steps_derivation_planning_receipt_delta_and_control_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    if not (
        campaign["target_occurrence_ids"] == occurrence_ids
        and campaign["online_typed_plan_source_histogram"] == histogram
        and accounting == expected_accounting
        and roles
        == {
            "DELTA_GRAPH_AND_COMPILED_INVALIDATION",
            "DELTA_RETENTION_AND_INCREMENTAL_REVALIDATION",
        }
        and all(histogram[source] > 0 for source in histogram)
        and totals["graph_invalidations"] > 0
        and totals["graph_retentions"] > 0
        and totals["program_invalidations"] > 0
        and totals["incremental"] > 0
        and totals["full_graph_diff_checks_avoided"] > 0
        and factor_avoided > 0
        and query_avoided >= 0
        and campaign["registered_gate"]["passed"] is True
        and campaign["certificate_delta_driven_invalidation_observed"] is True
        and campaign["factor_prior_sample_tax_reduction_observed"] is True
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
        _fail("V175r1 independent aggregate or claim boundary changed")
    verification_payload = {
        "schema": "acfqp.certificate_delta_invalidation_verification.v175r1",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_id": CAMPAIGN_ID,
        "preserved_v175_failure_id": V175_FAILURE_ID,
        "corrected_classifier_receipt_id": CLASSIFIER_ID,
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
        "verified_delta_decision_compute_events": totals["delta_decision_compute"],
        "verified_full_graph_control_checks": totals["full_graph_control_checks"],
        "verified_full_graph_diff_checks_avoided_on_decision_path": totals[
            "full_graph_diff_checks_avoided"
        ],
        "verified_factor_prior_labels_avoided": factor_avoided,
        "verified_query_policy_labels_avoided": query_avoided,
        "producer_free_target_outcome_reexecution": True,
        "producer_free_certificate_delta_reconstruction": True,
        "producer_free_delta_transition_join_reconstruction": True,
        "producer_free_minimal_invalidation_reconstruction": True,
        "producer_free_unaffected_dependency_retention_reconstruction": True,
        "producer_free_program_invalidation_reconstruction": True,
        "producer_free_incremental_revalidation_chain_reconstruction": True,
        "producer_free_online_issuance_and_execution_join_reconstruction": True,
        "zero_serialized_full_graph_scan_on_decision_path_independently_verified": True,
        "delta_frontier_full_diff_control_equality_independently_verified": True,
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
        "verification_id": domains.extension_content_id_v175r1(
            domains.CONSTRUCTION_K7_VERIFICATION_V175R1_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V175r1 frozen independent verification changed")
    return document


__all__ = (
    "VERIFICATION_ID",
    "verify_certificate_delta_invalidation_campaign_v175r1",
)
