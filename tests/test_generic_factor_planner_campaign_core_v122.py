from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import dual_budget_config_v119
from acfqp.generic_factor_planner_campaign_core_v122 import (
    build_generic_factor_planner_occurrence_v122,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v122_development_occurrence_uses_generic_planner():
    sources = _sources()
    row = build_generic_factor_planner_occurrence_v122(
        dual_budget_config_v119(),
        seed=1_033_002,
        episode_indices=(272, 273, 274),
        artifact_factor_library=derive_artifact_factor_projection_v120(sources),
        source_campaign_bytes=sources,
        strict_complete_factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["registered_gate"]["generic_program_fallback_exercised"] is True
    assert row["legacy_shape_specific_planner_execution_adapter_present"] is False
    assert row["generic_planner_execution_adapter_verified"] is True
    assert row["complete_ground_world_model_synthesized"] is False
    assert row["official_scalar_cost"] is None
