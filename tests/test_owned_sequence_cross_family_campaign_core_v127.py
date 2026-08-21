from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import dual_budget_config_v119
from acfqp.owned_sequence_cross_family_campaign_core_v127 import build_owned_sequence_cross_family_occurrence_v127


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v127_development_reuses_v126_owned_sequence_on_dual_budget():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    config = dual_budget_config_v119()
    config["families"]["STOCHASTIC_DUAL_BUDGET_COMPOSITION"]["maximum_acquisition_labels"] = 2_048
    row = build_owned_sequence_cross_family_occurrence_v127(
        config,
        seed=1_030_005,
        episode_indices=(308, 309, 310),
        artifact_factor_library=derive_artifact_factor_projection_v120(source),
        source_campaign_bytes=source,
        strict_complete_factor_library=v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    assert row["registered_gate"]["passed"] is True
    assert row["same_v126_owned_sequence_reused_without_family_dispatch"] is True
    assert row["target_family"] == "STOCHASTIC_DUAL_BUDGET_COMPOSITION"
    assert row["retained_v113_sequence_orchestration_present"] is False
    assert row["official_scalar_cost"] is None
