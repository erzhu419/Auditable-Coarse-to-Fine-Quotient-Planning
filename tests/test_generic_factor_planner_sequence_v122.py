from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_artifact_subprogram_acquisition_v121 import (
    acquire_generic_artifact_subprogram_model_v121,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    build_dual_budget_adapter_v119,
    dual_budget_config_v119,
)
from acfqp.generic_factor_planner_sequence_v122 import (
    run_generic_factor_planner_sequence_v122,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v122_development_sequence_uses_generic_program_fallback():
    config = dual_budget_config_v119()
    adapter = build_dual_budget_adapter_v119(1_033_002, config)
    sources = _sources()
    acquired = acquire_generic_artifact_subprogram_model_v121(
        adapter,
        derive_artifact_factor_projection_v120(sources),
        sources,
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        config,
    )
    partial = acquired["partial"]
    sequence = run_generic_factor_planner_sequence_v122(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        episode_indices=(272, 273, 274),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    verification = sequence["generic_execution_verification"]
    assert verification["direct_generic_factor_program_plan_count"] > 0
    assert verification["every_compiled_model_edge_replayed_by_generic_interpreter"] is True
    assert verification["legacy_shape_specific_planner_execution_adapter_called"] is False
    assert sequence["generic_planner_execution_adapter_verified"] is True
    assert sequence["legacy_shape_specific_planner_execution_adapter_present"] is False
    assert sequence["complete_ground_world_model_synthesized"] is False
