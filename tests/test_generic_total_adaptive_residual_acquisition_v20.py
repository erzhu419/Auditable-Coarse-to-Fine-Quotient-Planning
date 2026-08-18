from acfqp.generic_total_adaptive_residual_acquisition_v20 import (
    acquire_total_adaptive_residual_factor_v20,
    replay_total_adaptive_residual_factor_v20,
)


def _evidence(query_count):
    rows = []
    for query in range(query_count):
        rows.append(
            {
                "occurrence": 0,
                "transition_index": query,
                "pre_vector": [query],
                "legal_action_keys_before": [query],
                "selected_action": {
                    "action_key": query,
                    "anonymous_fields": [query],
                },
                "post_vector": [query + (1 if query % 3 == 0 else 0)],
                "legal_action_keys_after": [query],
                "terminal_acceptance_after": None,
                "outcome_tape_sha256": None,
            }
        )
    return {
        "layout": {
            "state_canonical_to_raw": [0],
            "action_canonical_to_raw": [0],
        },
        "unknown_residual_target_columns": [0],
        "raw_transition_rows": rows,
    }


def test_v20_returns_typed_abstention_instead_of_positive_frontier_stop():
    evidence = _evidence(2)
    result = acquire_total_adaptive_residual_factor_v20(
        evidence, prior_library=None, confidence_denominator=64
    )
    assert result["status"] == "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE"
    assert result["ground_support_labels"] == 2
    assert result["query_pool_exhaustion_used_as_positive_stop"] is False
    replay = replay_total_adaptive_residual_factor_v20(result, evidence)
    assert replay["abstention_replayed"] is True
    assert replay["future_transition_prediction_authority_present"] is False
