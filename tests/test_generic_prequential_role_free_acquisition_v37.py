from acfqp.generic_prequential_role_free_acquisition_v37 import (
    acquire_prequential_role_free_terminal_program_v37,
)
from acfqp.generic_role_free_relational_template_v33 import (
    compile_role_free_relational_template_library_v33,
)


def _program():
    import hashlib
    from acfqp.phase3e_ids import canonical_json_bytes

    tree = {
        "kind": "RELATION",
        "opcode": "EQ",
        "left_column": 0,
        "right_column": 1,
        "when_true": {"kind": "LEAF", "terminal_class": "ACCEPT", "status_token": 9},
        "when_false": {"kind": "LEAF", "terminal_class": "ACTIVE", "status_token": 4},
    }
    encoded = canonical_json_bytes(tree)
    return {
        "schema": "acfqp.generic_relational_terminal_program.v28",
        "terminal_program_id": hashlib.sha256(encoded).hexdigest(),
        "decision_tree_candidate_frontier": [
            {
                "candidate_index": 0,
                "decision_tree_node_count": 3,
                "decision_tree_byte_count": len(encoded),
                "decision_tree_sha256": hashlib.sha256(encoded).hexdigest(),
                "decision_tree": tree,
            }
        ],
        "empirical_program_only": True,
        "future_unseen_terminal_authority_present": False,
    }


def _row(index, left, right, terminal):
    return {
        "pre_vector": [index, index + 1, 4],
        "post_vector": [left, right, 9 if terminal else 4],
        "selected_action": {"action_key": index, "anonymous_fields": [index]},
        "legal_action_keys_after": [] if terminal else [0],
        "terminal_acceptance_after": True if terminal else None,
    }


def _evidence():
    return {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row(0, 1, 2, False),
            _row(1, 3, 3, True),
            _row(2, 4, 5, False),
            _row(3, 6, 6, True),
            _row(4, 7, 8, False),
            _row(5, 9, 9, True),
        ],
    }


def test_v37_requires_a_prediction_frozen_before_the_confirmation_outcome():
    library = compile_role_free_relational_template_library_v33((_program(),))
    result = acquire_prequential_role_free_terminal_program_v37(
        _evidence(),
        role_free_template_library=library,
        confidence_denominator=2,
    )
    assert result["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    assert result["stopped_physical_ground_support_labels"] < result[
        "full_query_stream_ground_support_labels"
    ]
    assert result["prequential_prediction_ledger"][-1][
        "prediction_frozen_before_query_outcome"
    ] is True
    assert result["heldout_rows_accessed_before_stop"] is False
    assert result["fixed_confirmation_block_present"] is False
    assert result["statistical_coverage_claimed"] is False


def test_v37_uses_the_same_calibration_engine_without_a_prior():
    strict = acquire_prequential_role_free_terminal_program_v37(
        _evidence(),
        role_free_template_library=None,
        confidence_denominator=2,
    )
    assert strict["same_prequential_state_machine_in_both_arms"] is True
    assert strict["proposal_only_not_safety_authority"] is True
