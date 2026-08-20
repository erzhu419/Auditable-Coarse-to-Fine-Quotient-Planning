import hashlib

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_learned_successor_support_acquisition_v41 as v41
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    verify_joint_successor_version_space_model_v42,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    synthesize_partial_factor_candidate_v15,
)
from acfqp.generic_role_free_relational_template_v33 import (
    compile_role_free_relational_template_library_v33,
)
from acfqp.generic_successor_projected_acquisition_v49 import (
    acquire_successor_projected_terminal_program_v49,
    run_relation_covering_successor_projected_acquisition_v49,
)
from acfqp.generic_successor_projected_model_compiler_v49 import (
    compile_successor_projected_model_v49,
)
from acfqp.generic_version_space_retaining_acquisition_v51 import (
    acquire_version_space_retaining_terminal_program_v51,
    run_relation_covering_version_space_retaining_acquisition_v51,
)
from acfqp.generic_version_space_retaining_model_compiler_v51 import (
    compile_version_space_retaining_model_v51,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _tree(left, right):
    return {
        "kind": "RELATION",
        "opcode": "EQ",
        "left_column": left,
        "right_column": right,
        "when_true": {"kind": "LEAF", "terminal_class": "ACCEPT", "status_token": 9},
        "when_false": {"kind": "LEAF", "terminal_class": "ACTIVE", "status_token": 4},
    }


def _program():
    trees = [_tree(0, 1), _tree(0, 2)]
    frontier = []
    for index, tree in enumerate(trees):
        raw = canonical_json_bytes(tree)
        frontier.append(
            {
                "candidate_index": index,
                "decision_tree_node_count": 3,
                "decision_tree_byte_count": len(raw),
                "decision_tree_sha256": hashlib.sha256(raw).hexdigest(),
                "decision_tree": tree,
            }
        )
    return {
        "schema": "acfqp.generic_relational_terminal_program.v28",
        "terminal_program_id": "a" * 64,
        "status_target_column": 3,
        "status_token_by_terminal_class": {"ACCEPT": 9, "ACTIVE": 4},
        "decision_tree": trees[0],
        "decision_tree_node_count": 3,
        "decision_tree_candidate_frontier": frontier,
        "decision_tree_candidate_count": 2,
        "future_unseen_terminal_authority_present": False,
    }


def _row(index, pre, post, terminal):
    return {
        "pre_vector": pre,
        "post_vector": post,
        "selected_action": {"action_key": index, "anonymous_fields": [1]},
        "legal_action_keys_after": [] if terminal else [0],
        "terminal_acceptance_after": True if terminal else None,
    }


def test_v49_does_not_apply_terminal_frontier_to_query_prestates(monkeypatch):
    program = _program()
    rows = [
        _row(0, [0, 1, 0, 4], [1, 1, 1, 9], True),
        _row(1, [2, 3, 2, 4], [3, 4, 5, 4], False),
        _row(2, [4, 5, 4, 4], [5, 5, 5, 9], True),
        _row(3, [6, 7, 6, 4], [7, 8, 9, 4], False),
    ]
    evidence = {
        "layout": {
            "state_canonical_to_raw": [0, 1, 2, 3],
            "action_canonical_to_raw": [0],
        },
        "unknown_residual_target_columns": [3],
        "raw_transition_rows": rows,
    }
    prestates = tuple(tuple(row["pre_vector"]) for row in rows)
    assert v35._consensus(program, prestates) is False  # noqa: SLF001

    monkeypatch.setattr(
        v37,
        "_candidate",
        lambda *_args, **_kwargs: {
            "candidate_present": True,
            "candidate_program": program,
            "candidate_program_id": program["terminal_program_id"],
            "training_calibrated": True,
        },
    )
    monkeypatch.setattr(
        v41,
        "_learned_successor_guard",
        lambda *_args, **_kwargs: {
            "successor_model_present": True,
            "learned_successor_frontier_consensus": True,
            "successor_model_selection_compute_events": 1,
        },
    )
    monkeypatch.setattr(
        v37,
        "_predict_group",
        lambda *_args, **_kwargs: {
            "query_exact": True,
            "raw_row_predictions": [],
        },
    )
    result = acquire_successor_projected_terminal_program_v49(
        evidence,
        role_free_template_library={},
        successor_prior_library=None,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
        successor_confidence_denominator=2,
    )
    assert result["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    assert result["terminal_frontier_evaluated_on_query_prestates"] is False
    assert result["projected_future_successor_support_consensus_required"] is True
    assert result["heldout_rows_accessed_before_stop"] is False


def _compiler_fixture():
    catalogue = (
        FlatRawActionV4(0, (1, 2)),
        FlatRawActionV4(1, (2, 3)),
    )
    rows = []
    queries = (
        (0, 1, 0),
        (0, 2, 1),
        (1, 1, 0),
        (1, 2, 1),
        (2, 1, 0),
        (2, 2, 1),
        (3, 1, 0),
        (3, 2, 1),
    )
    for position, delta, key in queries:
        pre = (position, 4, 10 + position, 4)
        next_position = position + delta
        terminal = next_position >= 4
        for residual in (pre[2], pre[2] + delta + 1):
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    pre,
                    (0, 1),
                    catalogue[key],
                    (next_position, 4, residual, 9 if terminal else 4),
                    () if terminal else (0, 1),
                    True if terminal else None,
                )
            )
    candidate_rows = [*rows]
    candidate_rows.append(
        FlatRawTransitionV4(
            0,
            len(candidate_rows),
            (0, 4, 10, 4),
            (0, 1),
            catalogue[0],
            (1, 4, 109, 4),
            (0, 1),
            None,
        )
    )
    config = v57.campaign_config_v57()
    candidate = synthesize_partial_factor_candidate_v15(
        tuple(candidate_rows),
        catalogue,
        V51_FACTOR_TEMPLATE_PROJECTION,
        support_label_count=len(queries),
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
        ),
        candidate_content_id=domains_v58.extension_content_id_v58,
        minimum_factor_assignment_count=2,
    )
    tree = {
        "kind": "RELATION",
        "opcode": "GE",
        "left_column": 3,
        "right_column": 2,
        "when_true": {
            "kind": "LEAF",
            "terminal_class": "ACCEPT",
            "status_token": 9,
        },
        "when_false": {
            "kind": "LEAF",
            "terminal_class": "ACTIVE",
            "status_token": 4,
        },
    }
    encoded = canonical_json_bytes(tree)
    source_program = {
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
    library = compile_role_free_relational_template_library_v33((source_program,))
    evidence = {
        "layout": candidate.public_document["layout"],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": [row.to_document() for row in rows],
    }
    return candidate, evidence, library


def test_v49_compiles_to_verified_joint_successor_model():
    candidate, evidence, library = _compiler_fixture()
    acquisition = run_relation_covering_successor_projected_acquisition_v49(
        evidence,
        role_free_template_library=library,
        successor_prior_library=None,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
        successor_confidence_denominator=2,
    )
    assert acquisition["successor_projected_acquisition"]["status"] == (
        "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    )
    model = compile_successor_projected_model_v49(
        candidate, evidence, acquisition
    )
    verified = verify_joint_successor_version_space_model_v42(model)
    assert verified["source_acquisition_protocol"] == "SUCCESSOR_PROJECTED_V49"
    assert verified["terminal_frontier_evaluated_on_query_prestates"] is False
    assert verified["all_state_coordinates_represented"] is True
    assert verified["complete_world_model_claimed"] is False
    assert verified["abstract_plan_safety_authority_present"] is False


def test_v51_issues_without_a_residual_successor_consensus_gate(monkeypatch):
    program = _program()
    evidence = {
        "layout": {
            "state_canonical_to_raw": [0, 1, 2, 3],
            "action_canonical_to_raw": [0],
        },
        "unknown_residual_target_columns": [3],
        "raw_transition_rows": [
            _row(0, [0, 1, 0, 4], [1, 1, 1, 9], True),
            _row(1, [2, 3, 2, 4], [3, 4, 5, 4], False),
            _row(2, [4, 5, 4, 4], [5, 5, 5, 9], True),
            _row(3, [6, 7, 6, 4], [7, 8, 9, 4], False),
        ],
    }
    monkeypatch.setattr(
        v37,
        "_candidate",
        lambda *_args, **_kwargs: {
            "candidate_present": True,
            "candidate_program": program,
            "candidate_program_id": program["terminal_program_id"],
            "training_calibrated": True,
        },
    )
    monkeypatch.setattr(
        v37,
        "_predict_group",
        lambda *_args, **_kwargs: {
            "query_exact": True,
            "raw_row_predictions": [],
        },
    )
    result = acquire_version_space_retaining_terminal_program_v51(
        evidence,
        role_free_template_library={},
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
    )
    assert result["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    assert result[
        "residual_successor_version_space_consensus_required_before_issuance"
    ] is False
    assert result[
        "every_batch_exact_residual_proposal_retained_by_compiler_required"
    ] is True
    assert result["heldout_rows_accessed_before_stop"] is False


def test_v51_compiles_and_retains_joint_residual_version_space():
    candidate, evidence, library = _compiler_fixture()
    acquisition = run_relation_covering_version_space_retaining_acquisition_v51(
        evidence,
        role_free_template_library=library,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
    )
    assert acquisition["version_space_retaining_acquisition"]["status"] == (
        "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    )
    model = compile_version_space_retaining_model_v51(
        candidate, evidence, acquisition
    )
    verified = verify_joint_successor_version_space_model_v42(model)
    assert verified["source_acquisition_protocol"] == "VERSION_SPACE_RETAINING_V51"
    assert verified[
        "residual_successor_consensus_used_as_acquisition_gate"
    ] is False
    assert verified["every_batch_exact_residual_expression_retained"] is True
    assert verified["all_state_coordinates_represented"] is True
    assert verified["complete_world_model_claimed"] is False
    assert verified["abstract_plan_safety_authority_present"] is False
