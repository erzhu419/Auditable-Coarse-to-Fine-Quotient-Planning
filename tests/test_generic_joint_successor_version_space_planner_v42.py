from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    compile_joint_successor_version_space_model_v42,
    plan_joint_successor_version_space_v42,
    verify_joint_successor_version_space_model_v42,
)
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    run_relation_covering_learned_successor_acquisition_v41,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    synthesize_partial_factor_candidate_v15,
)
from acfqp.generic_role_free_relational_template_v33 import (
    compile_role_free_relational_template_library_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _fixture():
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
        legal_after = () if terminal else (0, 1)
        # The third raw coordinate is an exact two-valued residual support.
        # It is intentionally outside the V15 partial-factor grammar.
        for residual in (pre[2], pre[2] + delta + 1):
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    pre,
                    (0, 1),
                    catalogue[key],
                    (
                        next_position,
                        4,
                        residual,
                        9 if terminal else 4,
                    ),
                    legal_after,
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
    # Canonical layout is [status, residual, goal, position] for this opaque
    # fixture.  The source template carries no role names or target binding.
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
    acquisition = run_relation_covering_learned_successor_acquisition_v41(
        evidence,
        role_free_template_library=library,
        successor_prior_library=None,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
        successor_confidence_denominator=2,
    )
    assert acquisition["learned_successor_acquisition"]["status"] == (
        "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    )
    return candidate, catalogue, evidence, acquisition


def test_v42_rejects_foreign_inputs():
    with pytest.raises(GenericJointSuccessorVersionSpacePlannerV42Error):
        compile_joint_successor_version_space_model_v42(object(), {}, {})
    with pytest.raises(GenericJointSuccessorVersionSpacePlannerV42Error):
        verify_joint_successor_version_space_model_v42({})


def test_v42_compiles_every_residual_proposal_and_plans_without_ground_access():
    candidate, catalogue, evidence, acquisition = _fixture()
    model = compile_joint_successor_version_space_model_v42(
        candidate, evidence, acquisition
    )
    verified = verify_joint_successor_version_space_model_v42(model)
    assert verified["all_state_coordinates_represented"] is True
    assert verified["multiple_residual_proposals_jointly_compiled"] is True
    assert verified[
        "only_acquisition_prefix_outcomes_used_to_fit_successor_expressions"
    ] is True
    assert verified[
        "post_stop_heldout_rows_used_as_successor_expression_inputs"
    ] is False
    assert verified["complete_world_model_claimed"] is False
    assert verified["abstract_plan_safety_authority_present"] is False

    plan = plan_joint_successor_version_space_v42(
        model,
        candidate,
        catalogue,
        (0, 4, 10, 4),
        maximum_depth=4,
    )
    assert plan["initial_action_key"] in (0, 1)
    assert plan["retained_residual_expression_count"] > 1
    assert plan["all_residual_version_spaces_jointly_propagated"] is True
    assert plan["all_mdl_minimal_terminal_trees_jointly_propagated"] is True
    assert plan["ground_transition_accessed_during_abstract_search"] is False
    assert plan["abstract_plan_used_as_safety_authority"] is False
    assert plan["complete_world_model_claimed"] is False


def test_v42_model_identity_rejects_claim_flip():
    candidate, _catalogue, evidence, acquisition = _fixture()
    model = compile_joint_successor_version_space_model_v42(
        candidate, evidence, acquisition
    )
    model["complete_world_model_claimed"] = True
    with pytest.raises(GenericJointSuccessorVersionSpacePlannerV42Error):
        verify_joint_successor_version_space_model_v42(model)
