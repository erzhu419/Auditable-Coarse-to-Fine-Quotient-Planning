from pathlib import Path

from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_modular_routing_adapter_v128 import FAMILY, modular_routing_config_v128
from acfqp.unified_factor_prior_ablation_campaign_core_v129 import build_unified_factor_prior_ablation_occurrence_v129


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _source():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v129_development_occurrence_reduces_labels_with_only_registered_factor_prior_switch():
    source = _source()
    document = build_unified_factor_prior_ablation_occurrence_v129(
        modular_routing_config_v128(),
        family=FAMILY,
        seed=1_030_009,
        episode_indices=(320, 321, 322),
        artifact_factor_library=derive_artifact_factor_projection_v120(source),
        source_campaign_bytes=source,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["sample_tax_comparison"]["only_arm_switch_is_registered_factor_prior"] is True
    assert document["sample_tax_comparison"]["ground_support_labels_avoided_by_factor_prior"] == 4
    assert document["factor_prior_acquisition"]["ground_support_labels"] == 19
    assert document["strict_no_prior_acquisition"]["ground_support_labels"] == 23
    assert all(row["success"] for row in document["factor_prior_owned_sequence"]["episodes"])
    assert all(row["success"] for row in document["strict_no_prior_owned_sequence"]["episodes"])
    assert document["official_scalar_cost"] is None
