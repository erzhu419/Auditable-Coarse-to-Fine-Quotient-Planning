from pathlib import Path
from types import SimpleNamespace

from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.receipt_driven_minimal_invalidation_sequence_v174 import (
    COMPILED_STATE_DEPENDENCY,
    GRAPH_DEPENDENCY,
    _ACTIVE,
    _program_invalidation,
    _receipt_driven_transition,
    run_receipt_driven_minimal_invalidation_sequence_v174,
)
from acfqp.online_typed_plan_receipt_sequence_v172 import _plan_id
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _graph_entry(identity, state):
    return {
        "dependency": {
            "dependency_receipt_id": identity,
            "ordered_bfs_dependency_rows": [{"projected_state": [state]}],
        },
        "authorized_quotient_graph_id": "before",
        "epoch_authorization_chain": [],
    }


def _graph_projection(identity, state, projection_id):
    return {
        "dependency_kind": GRAPH_DEPENDENCY,
        "quotient_dependency_receipt_id": identity,
        "ordered_projected_state_dependencies": [[state]],
        "dependency_projection_id": projection_id,
    }


def test_v174_receipt_projection_invalidates_only_changed_dependency():
    a = "a" * 64
    b = "b" * 64
    entries = {a: _graph_entry(a, 0), b: _graph_entry(b, 2)}
    entries[a]["source_plan"] = {"unused": True}
    entries[b]["source_plan"] = {"unused": True}
    cache = {"a": [entries[a]], "b": [entries[b]]}
    reverse = {(0,): {a}, (2,): {b}}
    pa = _graph_projection(a, 0, "1" * 64)
    pb = _graph_projection(b, 2, "2" * 64)
    lifecycle = {
        "projections": {pa["dependency_projection_id"]: pa, pb["dependency_projection_id"]: pb},
        "events": [
            {
                "dependency": pa,
                "receipt": {"online_plan_issuance_receipt_id": "3" * 64},
            },
            {
                "dependency": pb,
                "receipt": {"online_plan_issuance_receipt_id": "4" * 64},
            },
        ],
        "epoch_transitions": [],
        "program_transitions": [],
    }
    token = _ACTIVE.set(lifecycle)
    try:
        receipt = _receipt_driven_transition(
            previous_model={
                "quotient_graph_id": "before",
                "projected_edge_rows": [
                    {"projected_pre": [0], "action_key": 0, "projected_post": [1]},
                    {"projected_pre": [2], "action_key": 0, "projected_post": [3]},
                ],
            },
            current_model={
                "quotient_graph_id": "after",
                "projected_edge_rows": [
                    {"projected_pre": [0], "action_key": 0, "projected_post": [4]},
                    {"projected_pre": [2], "action_key": 0, "projected_post": [3]},
                ],
            },
            previous_rules=({"kind": "EQUAL", "value": 9},),
            current_rules=({"kind": "EQUAL", "value": 9},),
            cache=cache,
            entries=entries,
            reverse_index=reverse,
        )
    finally:
        _ACTIVE.reset(token)
    assert receipt["invalidated_dependency_receipt_ids"] == [a]
    assert receipt["retained_dependency_receipt_ids"] == [b]
    assert receipt["invalidated_online_plan_issuance_receipt_ids"] == ["3" * 64]
    assert set(entries) == {b}
    assert set(cache) == {"b"}
    assert entries[b]["authorized_quotient_graph_id"] == "after"
    assert entries[b]["epoch_authorization_chain"] == [receipt]


def test_v174_program_receipt_closes_cache_only_on_successor_state_change():
    source_plan = {
        "schema": "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "planning_source": "COMPILED_FACTOR_PROGRAM_FALLBACK",
        "legality_conditioned_quotient_plan_id": "5" * 64,
    }
    source_plan_id = _plan_id(source_plan)
    lifecycle = {
        "events": [
            {
                "dependency": {
                    "dependency_kind": COMPILED_STATE_DEPENDENCY,
                    "current_successor_state_id": "old",
                },
                "receipt": {
                    "source_plan_id": source_plan_id,
                    "online_plan_issuance_receipt_id": "6" * 64,
                },
            }
        ],
        "program_transitions": [],
    }
    stats = {
        "_program_cache_successor_state_id": "old",
        "_program_cache": {"key": {"source_plan": source_plan}},
        "_program_branch_cache": {"branch": ()},
    }
    _program_invalidation(SimpleNamespace(state_id="new"), stats, lifecycle)
    assert stats["_program_cache"] == {}
    assert stats["_program_cache_successor_state_id"] == "new"
    assert lifecycle["program_transitions"][0][
        "authorizing_online_plan_issuance_receipt_ids"
    ] == ["6" * 64]


def test_v174_live_sequence_issues_dependencies_and_incrementally_revalidates():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_047_503, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_receipt_driven_minimal_invalidation_sequence_v174(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(651, 652),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    projection_ids = {
        row["dependency_projection_id"]
        for row in sequence["online_dependency_projections"]
    }
    assert sequence["online_plan_issuance_receipt_count"] > 0
    assert sequence["online_execution_join_receipt_count"] == sequence[
        "execution_step_count"
    ]
    assert all(
        row["dependency_projection_id"] in projection_ids
        for row in sequence["online_plan_issuance_receipts"]
    )
    assert sequence["receipt_driven_graph_dependency_retention_count"] > 0
    assert sequence["incrementally_revalidated_plan_receipt_count"] > 0
    assert sequence[
        "unaffected_graph_dependencies_reauthorized_without_per_hit_rescan"
    ] is True
    assert sequence["query_local_exact_overlay_remains_only_safety_authority"] is True
