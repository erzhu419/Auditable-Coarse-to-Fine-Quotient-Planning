from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_artifact_subprogram_acquisition_v121 import acquire_generic_artifact_subprogram_model_v121
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY, build_inventory_assembly_adapter_v118, inventory_assembly_config_v118
from acfqp.standalone_generic_model_sequence_v125 import run_standalone_generic_model_sequence_v125


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v125_development_sequence_uses_standalone_state_carrier():
    sources = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    config = inventory_assembly_config_v118()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 2_048
    adapter = build_inventory_assembly_adapter_v118(1_030_003, config)
    partial = acquire_generic_artifact_subprogram_model_v121(
        adapter,
        derive_artifact_factor_projection_v120(sources),
        sources,
        v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        config,
    )["partial"]
    sequence = run_standalone_generic_model_sequence_v125(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        episode_indices=(290, 291, 292),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    assert sequence["standalone_v125_state_carrier_verified"] is True
    assert sequence["retained_v113_state_carrier_present"] is False
    assert sequence["retained_v113_sequence_orchestration_present"] is True
    assert sequence["standalone_generic_model_reconstruction"]["all_state_and_update_receipts_use_v125_domains"] is True
