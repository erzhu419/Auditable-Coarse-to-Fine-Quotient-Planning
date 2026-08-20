from acfqp.generic_adaptive_role_free_terminal_acquisition_v35 import (
    acquire_adaptive_role_free_terminal_program_v35,
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


def _row(pre, post, action, legal, terminal):
    return {
        "pre_vector": pre,
        "post_vector": post,
        "selected_action": {"action_key": action, "anonymous_fields": [action]},
        "legal_action_keys_after": legal,
        "terminal_acceptance_after": terminal,
    }


def _evidence():
    return {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row([0, 1, 4], [1, 2, 4], 0, [0], None),
            _row([1, 2, 4], [2, 3, 4], 1, [0], None),
            _row([2, 3, 4], [3, 3, 9], 2, [], True),
            _row([3, 3, 9], [4, 5, 4], 3, [0], None),
            _row([4, 5, 4], [6, 6, 9], 4, [], True),
        ],
    }


def test_v35_same_engine_keeps_heldout_out_of_stopping_and_separates_labels():
    library = compile_role_free_relational_template_library_v33((_program(),))
    prior = acquire_adaptive_role_free_terminal_program_v35(
        _evidence(), role_free_template_library=library
    )
    strict = acquire_adaptive_role_free_terminal_program_v35(
        _evidence(), role_free_template_library=None
    )
    assert prior["witness_blind_query_order_sha256"] == strict[
        "witness_blind_query_order_sha256"
    ]
    assert prior["same_candidate_consensus_stopping_rule_for_both_arms"] is True
    assert prior["heldout_rows_accessed_before_stop"] is False
    assert strict["heldout_rows_accessed_before_stop"] is False
    assert prior["proposal_only_not_safety_authority"] is True
    assert prior["fixed_label_floor_present"] is False
    assert prior["fixed_confirmation_block_present"] is False
