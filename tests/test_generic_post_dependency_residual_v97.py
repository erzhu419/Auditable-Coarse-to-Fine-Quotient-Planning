from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import DiscoveredLayoutV5
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_post_dependency_residual_v97 import (
    plan_post_dependency_abstract_program_v97,
    synthesize_post_dependency_multi_residual_v97,
)


def _fixture():
    actions = (FlatRawActionV4(0, (1, 0)), FlatRawActionV4(1, (0, 1)))
    rows = (
        FlatRawTransitionV4(
            0, 0, (0, 0, 0, 100), (0, 1), actions[0], (1, 0, 1, 100), (0, 1), None
        ),
        FlatRawTransitionV4(
            0, 1, (1, 0, 1, 100), (0, 1), actions[0], (2, 0, 2, 200), (0, 1), None
        ),
        FlatRawTransitionV4(
            0, 2, (2, 0, 2, 200), (0, 1), actions[0], (3, 0, 3, 300), (), True
        ),
    )
    layout = DiscoveredLayoutV5(
        (0, 1, 2, 3),
        (0, 1),
        ("s0", "s1", "s2", "s3"),
        ("a0", "a1"),
        "schema",
        1,
        1,
        "layout",
    )
    public = {
        "candidate_id": "partial",
        "layout": layout.to_document(),
        "unknown_residual_target_columns": [2, 3],
    }
    partial = PartialFactorCandidateV15(
        public,
        layout,
        (
            {
                "target_column": 0,
                "expression": ["E07", ["E00", 0], ["E05", ["E00", 0], ["E01", 0]]],
            },
            {"target_column": 1, "expression": ["E00", 1]},
        ),
        rows,
    )
    ordinary = {
        "target_column": 2,
        "normalized_expression": ["R03", ["R00"], ["R01"]],
        "action_field_binding": 0,
        "anonymous_integer_constant_binding": None,
        "predictive_support_excess": 0,
        "candidate_id": "ordinary",
    }
    base = {
        "schema": "acfqp.generic_multi_residual_acquisition.v24",
        "multi_residual_acquisition_id": "base",
        "compilable_candidates": [ordinary],
        "proposal_only_not_safety_authority": True,
    }
    evidence = {
        "layout": layout.to_document(),
        "unknown_residual_target_columns": [2, 3],
        "raw_transition_rows": [row.to_document() for row in rows],
    }
    source = {
        "schema": "acfqp.post_dependency_structure_library.v97",
        "source_library_id": "source",
        "normalized_structure": [
            "PD03",
            ["PD00", "DRIVER_POST_COLUMN"],
            ["PD01", "LOWER_THRESHOLD"],
            ["PD01", "UPPER_THRESHOLD"],
            ["PD02", "FINITE_LEAF_SUPPORTS"],
        ],
    }
    return actions, rows, partial, base, evidence, source


def test_v97_discovers_anonymous_successor_dependency_and_jointly_plans():
    actions, rows, partial, base, evidence, source = _fixture()
    acquisition = synthesize_post_dependency_multi_residual_v97(
        evidence, base, structural_prior_library=source
    )
    assert acquisition["compilable_target_columns"] == [2, 3]
    assert acquisition["compilable_candidate_count"] == 2
    dependency = acquisition["retrospective_post_dependency_candidates"][0]
    assert dependency["driver_post_column"] == 2
    assert dependency["leaf_supports"] == [[100], [200], [300]]
    assert dependency["structure_prior_supplied_driver_thresholds_or_leaf_values"] is False
    plan = plan_post_dependency_abstract_program_v97(
        partial,
        rows,
        actions,
        (0, 0, 0, 100),
        acquisition,
        maximum_depth=4,
    )
    assert plan["initial_action_key"] == 0
    assert plan["dependency_candidate_ids"] == [dependency["candidate_id"]]
    assert plan["ground_transition_accessed_during_abstract_search"] is False
    assert plan["abstract_plan_used_as_safety_authority"] is False


def test_v97_prior_switch_changes_only_code_length_not_rebound_program():
    _actions, _rows, _partial, base, evidence, source = _fixture()
    with_prior = synthesize_post_dependency_multi_residual_v97(
        evidence, base, structural_prior_library=source
    )
    without = synthesize_post_dependency_multi_residual_v97(
        evidence, base, structural_prior_library=None
    )
    left = with_prior["retrospective_post_dependency_candidates"][0]
    right = without["retrospective_post_dependency_candidates"][0]
    assert left["driver_post_column"] == right["driver_post_column"]
    assert left["lower_inclusive_threshold"] == right["lower_inclusive_threshold"]
    assert left["upper_inclusive_threshold"] == right["upper_inclusive_threshold"]
    assert left["leaf_supports"] == right["leaf_supports"]
    assert left["description_length_bits"] < right["description_length_bits"]
    assert with_prior["shared_physical_ground_support_labels"] == without[
        "shared_physical_ground_support_labels"
    ]
