from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_artifact_subprogram_acquisition_v121 import acquire_generic_artifact_subprogram_model_v121
from acfqp.generic_incremental_abstract_successor_v113 import IncrementalAbstractSuccessorStateV113
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY, build_inventory_assembly_adapter_v118, inventory_assembly_config_v118
from acfqp.standalone_generic_model_epoch_v125 import (
    StandaloneGenericModelEpochStateV125,
    initialize_standalone_generic_model_v125,
    verify_standalone_generic_model_full_rebuild_v125,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v125_state_carrier_is_not_v113_and_rebuilds_generically():
    sources = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    config = inventory_assembly_config_v118()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 2_048
    adapter = build_inventory_assembly_adapter_v118(1_030_003, config)
    acquired = acquire_generic_artifact_subprogram_model_v121(
        adapter,
        derive_artifact_factor_projection_v120(sources),
        sources,
        v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        config,
    )["partial"]
    state, bootstrap = initialize_standalone_generic_model_v125(acquired["candidate"], acquired["rows"], adapter.catalogue)
    assert type(state) is StandaloneGenericModelEpochStateV125
    assert not isinstance(state, IncrementalAbstractSuccessorStateV113)
    assert state.model["schema"] == "acfqp.standalone_generic_model_epoch.v125"
    assert bootstrap["retained_v113_state_carrier_present"] is False
    match = verify_standalone_generic_model_full_rebuild_v125(
        state,
        acquired["candidate"],
        acquired["rows"],
        adapter.catalogue,
        update_receipt=None,
    )
    assert match["model_bytes_exactly_equal_full_generic_rebuild"] is True
    assert match["retained_v113_state_carrier_present"] is False
