from acfqp.generic_frontier_consensus_acquisition_v40 import (
    PRESERVED_V40_RETROSPECTIVE_DIAGNOSTIC,
    acquire_frontier_consensus_terminal_program_v40,
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


def test_v40_one_candidate_agrees_on_all_outcome_blind_query_prestates():
    library = compile_role_free_relational_template_library_v33((_program(),))
    result = acquire_frontier_consensus_terminal_program_v40(
        _evidence(),
        role_free_template_library=library,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
    )
    assert result["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    calibrated = [
        row for row in result["proposal_attempts"] if row["training_calibrated_after_all_guards"]
    ]
    assert calibrated
    assert calibrated[0]["candidate_frontier_consensus_on_all_query_pre_states"] is True
    assert result["unacquired_successor_or_label_accessed_by_frontier_guard"] is False


def test_v40_missing_semantic_class_still_abstains_without_a_label_floor():
    library = compile_role_free_relational_template_library_v33((_program(),))
    result = acquire_frontier_consensus_terminal_program_v40(
        _evidence(), role_free_template_library=library, confidence_denominator=2
    )
    assert result["status"].startswith("ABSTAINED")
    assert result["fixed_label_floor_present"] is False


def test_v40_preserves_the_failure_that_requires_successor_support():
    row = PRESERVED_V40_RETROSPECTIVE_DIAGNOSTIC
    assert row["prior_failed_noncertificate_occurrences"] == 1
    assert row["remaining_failure_requires_learned_successor_support"] is True
    assert row["registered_scientific_result"] is False
