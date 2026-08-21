from pathlib import Path

from acfqp.fair_unified_factor_prior_ablation_campaign_core_v129r1 import (
    build_fair_unified_factor_prior_ablation_occurrence_v129r1,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY,
    modular_routing_config_v128,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _source():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v129r1_development_occurrence_runs_owned_sequence_and_reduces_labels():
    source = _source()
    config = modular_routing_config_v128()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 320
    document = build_fair_unified_factor_prior_ablation_occurrence_v129r1(
        config,
        family=FAMILY,
        seed=1_030_024,
        episode_indices=(326, 327, 328),
        artifact_factor_library=derive_artifact_factor_projection_v120(source),
        source_campaign_bytes=source,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["sample_tax_comparison"][
        "same_fair_witness_blind_path_first_backtracking_policy"
    ] is True
    assert document["accounting"]["acquisition_labels_avoided_by_factor_prior"] > 0
    assert all(
        episode["success"]
        for arm in ("factor_prior_owned_sequence", "strict_no_prior_owned_sequence")
        for episode in document[arm]["episodes"]
    )
    assert document["official_scalar_cost"] is None
