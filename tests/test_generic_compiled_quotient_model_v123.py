from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v121 as domains_v121
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_artifact_subprogram_instantiator_v121 import synthesize_generic_artifact_factor_candidate_v121
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4, FlatRawTransitionV4
from acfqp.generic_compiled_quotient_model_v123 import (
    compile_generic_quotient_model_v123,
    generic_incremental_runtime_v123,
)
from acfqp.generic_dual_budget_adapter_v119 import build_dual_budget_adapter_v119, dual_budget_config_v119
from acfqp.generic_incremental_abstract_successor_v113 import initialize_incremental_abstract_successor_v113
from acfqp.generic_layout_factorized_world_model_v5 import DiscoveredLayoutV5
from acfqp.generic_observation_quotient_graph_v105 import compile_observation_quotient_graph_v105
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def _development():
    config = dual_budget_config_v119()
    adapter = build_dual_budget_adapter_v119(1_033_002, config)
    rows = []
    for label, batch in enumerate(v59.predecessor.predecessor.ground._witness_blind_depth_frontier(adapter), 1):
        rows.extend(batch)
        if label == 40:
            break
    projection = derive_artifact_factor_projection_v120(_sources())["v15_partial_synthesizer_projection"]
    candidate = synthesize_generic_artifact_factor_candidate_v121(
        tuple(rows), adapter.catalogue, projection,
        support_label_count=40,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=domains_v121.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_ACQUISITION_V121_DOMAIN,
        candidate_content_id=domains_v121.extension_content_id_v121,
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
    )
    return adapter, tuple(rows), candidate


def test_v123_generic_compiler_matches_retained_v113_on_current_library():
    adapter, rows, candidate = _development()
    assert compile_generic_quotient_model_v123(candidate, rows, adapter.catalogue) == (
        compile_observation_quotient_graph_v105(candidate, rows, adapter.catalogue)
    )
    generic, _ = generic_incremental_runtime_v123().initialize(candidate, rows, adapter.catalogue)
    legacy, _ = initialize_incremental_abstract_successor_v113(candidate, rows, adapter.catalogue)
    assert generic.model == legacy.model
    assert generic.terminal_rules == legacy.terminal_rules


def test_v123_compiles_unseen_expression_rejected_by_v105_shape_adapter():
    layout = DiscoveredLayoutV5((0,), (0,), ("x",), ("a",), "schema", 0, 0, "l" * 64)
    candidate = PartialFactorCandidateV15(
        {
            "candidate_id": "c" * 64,
            "layout": layout.to_document(),
            "unknown_residual_target_columns": [],
        },
        layout,
        ({
            "target_column": 0,
            "result_type": "INT",
            "expression": ["E05", ["E00", 0], ["E01", 0]],
            "signature_sha256": "e" * 64,
            "state_dependencies": [0],
            "action_dependencies": [0],
        },),
        (),
    )
    actions = (FlatRawActionV4(0, (1,)), FlatRawActionV4(1, (2,)))
    rows = (
        FlatRawTransitionV4(0, 0, (0,), (0, 1), actions[0], (1,), (0, 1), None),
        FlatRawTransitionV4(0, 1, (1,), (0, 1), actions[1], (3,), (), True),
    )
    model = compile_generic_quotient_model_v123(candidate, rows, actions)
    assert model["projected_edge_count"] == 2
    with pytest.raises(Exception):
        compile_observation_quotient_graph_v105(candidate, rows, actions)
