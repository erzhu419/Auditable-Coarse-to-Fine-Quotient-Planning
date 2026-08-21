from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.construction_k7_standalone_generic_model_preregistration_v125 import campaign_config_v125
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.standalone_generic_owned_campaign_core_v126 import build_standalone_generic_owned_occurrence_v126


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v126_development_occurrence_passes_owned_loop_gate():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    row = build_standalone_generic_owned_occurrence_v126(
        campaign_config_v125(),
        seed=1_030_004,
        episode_indices=(302, 303, 304),
        artifact_factor_library=derive_artifact_factor_projection_v120(source),
        source_campaign_bytes=source,
        strict_complete_factor_library=v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    assert row["registered_gate"]["passed"] is True
    assert row["retained_v113_sequence_orchestration_present"] is False
    assert row["retained_v119_sequence_orchestration_present"] is False
    assert row["official_scalar_cost"] is None
