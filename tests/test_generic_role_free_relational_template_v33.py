from acfqp.generic_role_free_relational_template_v33 import (
    compile_role_free_relational_template_library_v33,
    instantiate_role_free_relational_template_v33,
)


def _program(left, right):
    tree = {
        "kind": "RELATION",
        "opcode": "EQ",
        "left_column": left,
        "right_column": right,
        "when_true": {"kind": "LEAF", "terminal_class": "ACCEPT", "status_token": 9},
        "when_false": {"kind": "LEAF", "terminal_class": "ACTIVE", "status_token": 4},
    }
    import hashlib
    from acfqp.phase3e_ids import canonical_json_bytes

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


def _row(post, legal, terminal):
    return {
        "post_vector": post,
        "legal_action_keys_after": legal,
        "terminal_acceptance_after": terminal,
    }


def test_v33_column_permutations_compile_to_one_role_free_template_and_rebind():
    library = compile_role_free_relational_template_library_v33(
        (_program(0, 2), _program(3, 1))
    )
    assert library["role_free_template_count"] == 1
    evidence = {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row([1, 2, 4], [0], None),
            _row([3, 3, 9], [], True),
        ],
    }
    result = instantiate_role_free_relational_template_v33(library, evidence)
    assert result["exact_target_instantiation_count"] > 0
    assert result["unmatched_target_rejected_as_ood"] is False
    assert result["instantiated_terminal_program"]["schema"].endswith(".v28")
    assert result["abstract_plan_safety_authority_present"] is False


def test_v33_incompatible_target_is_rejected_without_transfer():
    library = compile_role_free_relational_template_library_v33((_program(0, 2),))
    evidence = {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row([1, 2, 4], [0], None),
            _row([3, 4, 9], [], True),
        ],
    }
    result = instantiate_role_free_relational_template_v33(library, evidence)
    assert result["exact_target_instantiation_count"] == 0
    assert result["unmatched_target_rejected_as_ood"] is True
