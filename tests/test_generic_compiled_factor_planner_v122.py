from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v121 as domains_v121
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    synthesize_generic_artifact_factor_candidate_v121,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_compiled_factor_planner_v122 import (
    derive_generic_terminal_rules_v122,
    generic_factor_successor_projections_v122,
    plan_generic_factor_program_v122,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    build_dual_budget_adapter_v119,
    dual_budget_config_v119,
)
from acfqp.generic_incremental_abstract_successor_v113 import (
    initialize_incremental_abstract_successor_v113,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    partial_factor_successor_projections_v15,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def _development_candidate():
    config = dual_budget_config_v119()
    adapter = build_dual_budget_adapter_v119(1_033_002, config)
    rows = []
    for label, batch in enumerate(
        v59.predecessor.predecessor.ground._witness_blind_depth_frontier(adapter), 1
    ):
        rows.extend(batch)
        if label == 40:
            break
    projection = derive_artifact_factor_projection_v120(_sources())[
        "v15_partial_synthesizer_projection"
    ]
    candidate = synthesize_generic_artifact_factor_candidate_v121(
        tuple(rows),
        adapter.catalogue,
        projection,
        support_label_count=40,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains_v121.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_ACQUISITION_V121_DOMAIN
        ),
        candidate_content_id=domains_v121.extension_content_id_v121,
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
    )
    return adapter, tuple(rows), candidate


def test_v122_generic_successors_and_terminal_rules_match_frozen_library():
    adapter, rows, candidate = _development_candidate()
    state, _receipt = initialize_incremental_abstract_successor_v113(
        candidate, rows, adapter.catalogue
    )
    model = state.model
    generic_rules = derive_generic_terminal_rules_v122(
        candidate, model["projected_edge_rows"], model["projected_terminal_rows"]
    )
    assert generic_rules == state.terminal_rules
    actions = {
        action.key: FlatRawActionV4(
            action.key,
            tuple(
                action.fields[index]
                for index in candidate.layout.action_canonical_to_raw
            ),
        )
        for action in adapter.catalogue
    }
    for edge in model["projected_edge_rows"]:
        pre = tuple(edge["projected_pre"])
        generic = generic_factor_successor_projections_v122(
            candidate, pre, actions[edge["action_key"]]
        )
        legacy = partial_factor_successor_projections_v15(
            candidate, pre, actions[edge["action_key"]]
        )
        assert generic == legacy
        assert tuple(edge["projected_post"]) in generic


def test_v122_executes_expression_that_v15_planner_cannot_dispatch():
    _adapter, _rows, base = _development_candidate()
    assignments = (
        {
            "target_column": 0,
            "result_type": "INT",
            "expression": ["E05", ["E01", 0], ["E01", 1]],
            "signature_sha256": "a" * 64,
            "state_dependencies": [],
            "action_dependencies": [0, 1],
        },
        {
            "target_column": 1,
            "result_type": "INT",
            "expression": [
                "E12",
                ["E09", ["E00", 1], 0],
                ["E05", ["E00", 1], ["E01", 0]],
                ["E00", 1],
            ],
            "signature_sha256": "b" * 64,
            "state_dependencies": [1],
            "action_dependencies": [0],
        },
    )
    candidate = PartialFactorCandidateV15(
        {
            "candidate_id": "c" * 64,
            "unknown_residual_target_columns": [],
        },
        base.layout,
        assignments,
        (),
    )
    action = FlatRawActionV4(7, (2, 3))
    assert generic_factor_successor_projections_v122(candidate, (11, 1), action) == (
        (5, 3),
    )
    with pytest.raises(Exception):
        partial_factor_successor_projections_v15(candidate, (11, 1), action)


def test_v122_generic_program_plans_without_shape_dispatch():
    _adapter, _rows, base = _development_candidate()
    candidate = PartialFactorCandidateV15(
        {
            "candidate_id": "d" * 64,
            "unknown_residual_target_columns": [],
        },
        base.layout,
        (
            {
                "target_column": 0,
                "result_type": "INT",
                "expression": ["E05", ["E00", 0], ["E01", 0]],
                "signature_sha256": "e" * 64,
                "state_dependencies": [0],
                "action_dependencies": [0],
            },
        ),
        (),
    )
    raw_width = len(base.layout.action_canonical_to_raw)
    first_raw = base.layout.action_canonical_to_raw[0]

    def action(key, increment):
        fields = [0] * raw_width
        fields[first_raw] = increment
        return FlatRawActionV4(key, tuple(fields))

    plan = plan_generic_factor_program_v122(
        candidate,
        (action(3, 1), action(4, 2)),
        ({"target_column": 0, "kind": "AT_LEAST", "value": 4},),
        (0,),
        frozenset({3, 4}),
        {},
        maximum_depth=4,
    )
    assert plan["action_keys"] == [4, 4]
    assert plan["generic_planner_execution_adapter_verified"] is True
    assert plan["legacy_shape_specific_planner_execution_adapter_present"] is False


def test_v122_has_no_v15_expression_shape_dispatch():
    source = Path(__import__(
        "acfqp.generic_compiled_factor_planner_v122", fromlist=["x"]
    ).__file__).read_text()
    assert 'expression[0] == "E07"' not in source
    assert 'expression[0] == "E00"' not in source
    assert 'expression[0] == "E01"' not in source
