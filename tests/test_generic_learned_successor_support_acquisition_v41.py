from acfqp.generic_learned_successor_support_acquisition_v41 import (
    RETAINED_V71_DEVELOPMENT_DIAGNOSTIC_V41,
    acquire_learned_successor_support_terminal_program_v41,
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


def _row(index, pre, post):
    action = [post[column] - pre[column] for column in range(3)]
    terminal = post[0] == post[1]
    return {
        "pre_vector": pre,
        "post_vector": post,
        "selected_action": {"action_key": index, "anonymous_fields": action},
        "legal_action_keys_after": [] if terminal else [0],
        "terminal_acceptance_after": True if terminal else None,
    }


def _evidence():
    return {
        "layout": {
            "state_canonical_to_raw": [0, 1, 2],
            "action_canonical_to_raw": [0, 1, 2],
        },
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row(0, [0, 2, 4], [1, 2, 4]),
            _row(1, [2, 3, 4], [3, 3, 9]),
            _row(2, [4, 6, 4], [5, 6, 4]),
            _row(3, [6, 7, 4], [7, 7, 9]),
            _row(4, [8, 10, 4], [9, 10, 4]),
            _row(5, [10, 11, 4], [11, 11, 9]),
            _row(6, [12, 14, 4], [13, 14, 4]),
            _row(7, [14, 15, 4], [15, 15, 9]),
        ],
    }


def test_v41_guard_uses_only_acquired_rows_and_future_query_projections():
    library = compile_role_free_relational_template_library_v33((_program(),))
    result = acquire_learned_successor_support_terminal_program_v41(
        _evidence(),
        role_free_template_library=library,
        successor_prior_library=None,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
        successor_confidence_denominator=2,
    )
    guarded = [
        row["learned_successor_guard"]
        for row in result["proposal_attempts"]
        if row["learned_successor_guard"].get("successor_model_present") is True
    ]
    assert guarded
    assert all(
        row.get("unacquired_successor_or_label_accessed") is False
        for row in guarded
        if row.get(
            "all_terminal_dependency_coordinates_batch_exact_on_acquired_queries"
        )
        is True
    )
    assert all(row["terminal_dependency_columns"] == [0, 1] for row in guarded)
    assert all(
        all(item["candidate_count"] > 0 for item in row["per_coordinate_batch_exact_candidate_counts"])
        for row in guarded
    )
    assert result["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    assert result["status_output_coordinate_used_as_successor_guard_input"] is False
    assert result["batch_exact_successor_version_space_not_point_estimate"] is True
    assert result["successor_model_derivation_compute_events"] >= 0
    assert result["proposal_only_not_safety_authority"] is True


def test_v41_default_three_class_universe_abstains_on_two_class_evidence():
    library = compile_role_free_relational_template_library_v33((_program(),))
    result = acquire_learned_successor_support_terminal_program_v41(
        _evidence(),
        role_free_template_library=library,
        successor_prior_library=None,
        confidence_denominator=2,
        successor_confidence_denominator=2,
    )
    assert result["status"].startswith("ABSTAINED")
    assert result["fixed_label_floor_present"] is False


def test_v41_retained_v71_diagnostic_is_explicitly_development_only():
    row = RETAINED_V71_DEVELOPMENT_DIAGNOSTIC_V41
    assert row["role_free_factor_prior_on"]["heldout_failed_noncertificate_occurrence_count"] == 0
    assert row["strict_no_role_free_factor_prior"]["heldout_failed_noncertificate_occurrence_count"] == 0
    assert row["jointly_comparable_label_reduction"] == 34
    assert row["development_only_not_preregistered"] is True
    assert row["fresh_confirmatory_sample_tax_claim_present"] is False
