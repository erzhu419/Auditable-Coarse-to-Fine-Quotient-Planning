from acfqp.generic_role_free_relational_template_v33 import (
    compile_role_free_relational_template_library_v33,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    PRESERVED_V38_RETROSPECTIVE_DIAGNOSTIC,
    acquire_semantic_coverage_terminal_program_v38,
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


def test_v38_missing_typed_terminal_class_prevents_overeager_issuance():
    library = compile_role_free_relational_template_library_v33((_program(),))
    result = acquire_semantic_coverage_terminal_program_v38(
        _evidence(), role_free_template_library=library, confidence_denominator=2
    )
    assert result["status"].startswith("ABSTAINED")
    assert all(
        attempt["semantic_class_coverage_complete"] is False
        for attempt in result["proposal_attempts"]
    )
    assert result["fixed_label_floor_present"] is False


def test_v38_same_engine_can_use_a_smaller_typed_universe_without_a_floor():
    library = compile_role_free_relational_template_library_v33((_program(),))
    result = acquire_semantic_coverage_terminal_program_v38(
        _evidence(),
        role_free_template_library=library,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
    )
    assert result["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    assert result["semantic_class_coverage_is_typed_not_fixed_label_floor"] is True
    assert result["fixed_confirmation_block_present"] is False


def test_v38_retains_the_remaining_error_as_a_nonregistered_diagnostic():
    row = PRESERVED_V38_RETROSPECTIVE_DIAGNOSTIC
    assert row["joint_validated_occurrences"] == 5
    assert row["joint_failed_noncertificate_occurrences"] == 1
    assert row["registered_scientific_result"] is False
    assert row["sample_tax_claimed"] is False
