from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.cross_family_generic_compiler_campaign_core_v124 import build_cross_family_generic_compiler_occurrence_v124
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY, inventory_assembly_config_v118


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v124_development_inventory_occurrence_uses_no_legacy_model_control():
    sources = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    config = inventory_assembly_config_v118()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 2_048
    row = build_cross_family_generic_compiler_occurrence_v124(
        config,
        seed=1_030_003,
        episode_indices=(290, 291, 292),
        artifact_factor_library=derive_artifact_factor_projection_v120(sources),
        source_campaign_bytes=sources,
        strict_complete_factor_library=v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    assert row["registered_gate"]["passed"] is True
    assert row["legacy_shape_specific_model_builder_called"] is False
    assert row["legacy_matched_model_control_present"] is False
    assert row["retained_v113_state_carrier_present"] is True
    assert row["accounting"]["generic_model_epoch_reconstructions"] == 6
