from acfqp.generic_context_stratified_schedule_v55 import (
    schedule_context_stratified_queries_v55,
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
