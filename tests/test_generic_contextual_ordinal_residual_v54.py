import copy

from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.generic_contextual_ordinal_residual_v54 import (
    predict_version_space_group_v54,
    version_space_v54,
)
from acfqp.generic_contextual_ordinal_frontier_acquisition_v54 import _readiness


def _row(context, pre_stage, token, post_stage, transition):
    return {
        "occurrence": context,
        "transition_index": transition,
        "pre_vector": [pre_stage, 7],
        "legal_action_keys_before": [0, 1],
        "selected_action": {
            "action_key": 2 * context + (token > 30),
            "anonymous_fields": [token, 1],
        },
        "post_vector": [post_stage, 7],
        "legal_action_keys_after": [0],
        "terminal_acceptance_after": None,
        "outcome_tape_sha256": f"{transition:064x}",
        "contextual_source_member_index": context,
    }


def _evidence():
    rows = [
        _row(0, 0, 17, 1, 0),
        _row(0, 1, 43, 3, 1),
        _row(1, 0, 23, 1, 2),
        _row(1, 1, 49, 3, 3),
    ]
    return {
        "layout": {
            "state_canonical_to_raw": [0, 1],
            "action_canonical_to_raw": [0, 1],
        },
        "unknown_residual_target_columns": [0],
        "raw_transition_rows": rows,
        "contextual_action_field_supports": [
            {
                "context_index": 0,
                "source_member_id": "a" * 64,
                "action_field_supports": [[17, 43], [1]],
            },
            {
                "context_index": 1,
                "source_member_id": "b" * 64,
                "action_field_supports": [[23, 49], [1]],
            },
        ],
    }


def test_context_local_ordinal_finds_cross_token_update_old_grammar_misses():
    evidence = _evidence()
    groups = [[row] for row in evidence["raw_transition_rows"]]
    legacy = [
        [
            (tuple(row["pre_vector"]), tuple(row["post_vector"]), tuple(row["selected_action"]["anonymous_fields"]))
            for row in group
        ]
        for group in groups
    ]
    old_frontier, _ = v42._version_space(legacy, 0)  # noqa: SLF001
    frontier, _ = version_space_v54(evidence, groups, 0)
    assert old_frontier == []
    assert any(
        row["normalized_expression"] == ["R03", ["R00"], ["R05"]]
        and row["action_field_binding"] == 0
        for row in frontier
    )


def test_every_frozen_residual_candidate_is_checked_on_new_query():
    evidence = _evidence()
    groups = [[row] for row in evidence["raw_transition_rows"]]
    frontier, _ = version_space_v54(evidence, groups[:3], 0)
    spaces = [
        {
            "target_column": 0,
            "batch_exact_candidate_count": len(frontier),
            "batch_exact_candidate_frontier": copy.deepcopy(frontier),
        }
    ]
    exact = predict_version_space_group_v54(evidence, groups[3], spaces)
    assert exact["query_exact"] is True
    forged = copy.deepcopy(spaces)
    forged[0]["batch_exact_candidate_frontier"].append(
        {
            "normalized_expression": ["R00"],
            "action_field_binding": None,
            "anonymous_integer_constant_binding": None,
            "contextual_action_support_operator_used": False,
        }
    )
    rejected = predict_version_space_group_v54(evidence, groups[3], forged)
    assert rejected["query_exact"] is False


def test_context_supports_are_not_collapsed_into_a_global_rank():
    evidence = _evidence()
    groups = [[row] for row in evidence["raw_transition_rows"]]
    frontier, _ = version_space_v54(evidence, groups, 0)
    ordinal = next(
        row
        for row in frontier
        if row["normalized_expression"] == ["R03", ["R00"], ["R05"]]
        and row["action_field_binding"] == 0
    )
    assert ordinal["contextual_action_support_operator_used"] is True


def test_compiler_readiness_uses_contextual_ordinal_frontier():
    evidence = _evidence()
    program = {"status_target_column": 1}
    public, spaces = _readiness(
        evidence,
        [0, 1],
        evidence["raw_transition_rows"],
        program,
    )
    assert public["all_non_status_residual_version_spaces_nonempty"] is True
    assert public["contextual_ordinal_candidate_present"] is True
    assert spaces[0]["target_column"] == 0
    assert spaces[0]["batch_exact_candidate_count"] >= 1
