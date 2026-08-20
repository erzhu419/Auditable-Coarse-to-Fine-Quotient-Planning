import copy

from acfqp.generic_relation_covering_schedule_v39 import (
    PRESERVED_V39_RETROSPECTIVE_DIAGNOSTIC,
    schedule_relation_covering_queries_v39,
)


def _row(pre, key, post):
    return {
        "pre_vector": pre,
        "post_vector": post,
        "selected_action": {"action_key": key, "anonymous_fields": [key, -key]},
        "legal_action_keys_after": [0],
        "terminal_acceptance_after": None,
        "outcome_tape_sha256": None,
    }


def _evidence():
    return {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row([1, 2, 4], 0, [2, 3, 4]),
            _row([3, 3, 4], 1, [4, 4, 9]),
            _row([8, 2, 4], 2, [9, 3, 4]),
            _row([5, 5, 4], 3, [6, 6, 9]),
        ],
    }


def test_v39_schedule_is_invariant_to_all_outcome_witnesses():
    original = schedule_relation_covering_queries_v39(_evidence())
    changed = copy.deepcopy(_evidence())
    for row in changed["raw_transition_rows"]:
        row["post_vector"] = [99, 98, 97]
        row["legal_action_keys_after"] = []
        row["terminal_acceptance_after"] = False
        row["outcome_tape_sha256"] = "f" * 64
    replay = schedule_relation_covering_queries_v39(changed)
    assert original["schedule"] == replay["schedule"]
    assert original["query_source_projection_sha256"] == replay[
        "query_source_projection_sha256"
    ]
    assert original["terminal_acceptance_label_accessed"] is False


def test_v39_round_robin_exposes_each_relation_stratum_before_repeats():
    result = schedule_relation_covering_queries_v39(_evidence())
    first_round = [
        row for row in result["schedule"] if row["coverage_round"] == 0
    ]
    assert len(first_round) == result["relation_signature_stratum_count"]
    assert len({row["relation_signature_sha256"] for row in first_round}) == len(
        first_round
    )
    assert result["fixed_label_floor_present"] is False


def test_v39_retains_the_remaining_coupled_failure_and_no_reduction():
    row = PRESERVED_V39_RETROSPECTIVE_DIAGNOSTIC
    assert row["prior_failed_noncertificate_occurrences"] == 1
    assert row["prior_counterfactual_consumed_labels"] == row[
        "strict_counterfactual_consumed_labels"
    ]
    assert row["sample_tax_reduction_observed"] is False
    assert row["registered_scientific_result"] is False
