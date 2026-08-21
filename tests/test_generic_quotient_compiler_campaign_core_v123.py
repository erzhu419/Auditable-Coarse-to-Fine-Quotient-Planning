from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import dual_budget_config_v119
from acfqp.generic_quotient_compiler_campaign_core_v123 import (
    build_generic_quotient_compiler_occurrence_v123,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v123_development_occurrence_uses_generic_compiler_and_planner():
    sources = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    row = build_generic_quotient_compiler_occurrence_v123(
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
    assert row["legacy_shape_specific_model_builder_used_as_planning_input"] is False
    assert row["legacy_shape_specific_planner_execution_adapter_present"] is False
    assert row["accounting"]["generic_model_compiler_comparisons"] == 6
    assert row["accounting"]["direct_generic_factor_program_plans"] > 0
    assert row["official_scalar_cost"] is None
    assert row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
