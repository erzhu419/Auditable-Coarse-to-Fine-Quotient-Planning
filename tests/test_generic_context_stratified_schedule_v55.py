from acfqp.generic_context_stratified_schedule_v55 import (
    schedule_context_stratified_queries_v55,
)
from acfqp.generic_projected_disagreement_acquisition_v56 import (
    projected_disagreement_score_v56,
)


def _row(context, pre, key, index):
    return {
        "pre_vector": [pre, 10, 20],
        "selected_action": {"action_key": key, "anonymous_fields": [key, 1]},
        "post_vector": [pre + 1, 10, 20],
        "legal_action_keys_before": [0, 1],
        "legal_action_keys_after": [0, 1],
        "terminal_acceptance_after": None,
        "transition_index": index,
        "occurrence": context,
        "outcome_tape_sha256": f"{index:064x}",
        "contextual_source_member_index": context,
    }


def test_v55_round_robins_contexts_without_reading_outcomes():
    rows = [
        *[_row(0, index, index % 2, index) for index in range(6)],
        *[_row(1, 20 + index, index % 2, 10 + index) for index in range(3)],
    ]
    evidence = {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": rows,
        "contextual_action_field_supports": [
            {"context_index": 0},
            {"context_index": 1},
        ],
        "contextual_action_supports_derived_from_catalogue_only": True,
        "unacquired_successor_or_terminal_used_for_action_supports": False,
    }
    schedule = schedule_context_stratified_queries_v55(evidence)
    contexts = [row["contextual_source_member_index"] for row in schedule["schedule"]]
    assert contexts[:6] == [0, 1, 0, 1, 0, 1]
    assert schedule["post_state_fields_accessed"] is False
    assert schedule["terminal_acceptance_label_accessed"] is False
    assert schedule["outcome_tape_accessed"] is False


def test_v56_scores_terminal_disagreement_on_model_projected_successors():
    group = [_row(0, 4, 1, 99)]
    group[0]["pre_vector"] = [4, 4, 9]
    group[0]["selected_action"]["anonymous_fields"] = [43, 1]
    evidence = {
        "layout": {
            "state_canonical_to_raw": [0, 1, 2],
            "action_canonical_to_raw": [0, 1],
        },
        "known_partial_factor_assignments": [
            {"target_column": 1, "expression": ["E00", 1]}
        ],
        "contextual_action_field_supports": [
            {
                "context_index": 0,
                "source_member_id": "a" * 64,
                "action_field_supports": [[17, 43], [1]],
            }
        ],
    }
    active_leaf = {
        "kind": "LEAF",
        "terminal_class": "ACTIVE",
        "status_token": 9,
    }
    relational = {
        "kind": "RELATION",
        "opcode": "GE",
        "left_column": 0,
        "right_column": 1,
        "when_true": {
            "kind": "LEAF",
            "terminal_class": "ACCEPT",
            "status_token": 8,
        },
        "when_false": active_leaf,
    }
    program = {
        "status_target_column": 2,
        "decision_tree_candidate_frontier": [
            {"decision_tree": active_leaf},
            {"decision_tree": relational},
        ],
    }
    spaces = [
        {
            "target_column": 0,
            "batch_exact_candidate_frontier": [
                {
                    "normalized_expression": ["R03", ["R00"], ["R05"]],
                    "action_field_binding": 0,
                    "anonymous_integer_constant_binding": None,
                }
            ],
        }
    ]
    score = projected_disagreement_score_v56(evidence, group, program, spaces)
    assert score["candidate_disagreement_score"] > 0
    assert score["projected_disagreement_state_count"] > 0
    assert score["unacquired_post_state_or_label_accessed"] is False
