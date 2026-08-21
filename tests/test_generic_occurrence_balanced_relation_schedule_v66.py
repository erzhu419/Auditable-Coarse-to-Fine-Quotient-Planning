from acfqp.generic_occurrence_balanced_relation_schedule_v66 import (
    schedule_occurrence_balanced_relation_queries_v66,
)


def _row(occurrence, index, pre, key):
    return {
        "occurrence": occurrence,
        "transition_index": index,
        "pre_vector": pre,
        "legal_action_keys_before": [key],
        "selected_action": {"action_key": key, "anonymous_fields": [key, 1]},
        "post_vector": pre,
        "legal_action_keys_after": [key],
        "terminal_acceptance_after": None,
        "outcome_tape_sha256": None,
    }


def test_v66_round_robins_occurrences_without_outcome_fields():
    evidence = {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row(0, 0, [1, 2, 0], 0),
            _row(0, 1, [2, 3, 0], 1),
            _row(1, 0, [5, 6, 0], 2),
            _row(1, 1, [6, 7, 0], 3),
        ],
    }
    result = schedule_occurrence_balanced_relation_queries_v66(evidence)
    signatures = [row["occurrence_signature"] for row in result["schedule"]]
    assert signatures == [[0], [1], [0], [1]]
    assert result["post_state_fields_accessed_by_ranking"] is False
    assert result["terminal_acceptance_label_accessed_by_ranking"] is False
    assert result["fixed_label_floor_present"] is False
