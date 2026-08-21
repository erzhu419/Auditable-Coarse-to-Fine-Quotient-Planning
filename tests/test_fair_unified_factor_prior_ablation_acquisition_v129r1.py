from pathlib import Path

import pytest

from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import build_dual_budget_adapter_v119, dual_budget_config_v119
from acfqp.generic_inventory_assembly_adapter_v118 import build_inventory_assembly_adapter_v118, inventory_assembly_config_v118
from acfqp.generic_modular_routing_adapter_v128 import build_modular_routing_adapter_v128, modular_routing_config_v128
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import acquire_matched_fair_unified_factor_arms_v129r1


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _source():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


@pytest.mark.parametrize(
    ("builder", "config_builder", "seed"),
    (
        (build_inventory_assembly_adapter_v118, inventory_assembly_config_v118, 1_030_021),
        (build_dual_budget_adapter_v119, dual_budget_config_v119, 1_030_023),
        (build_modular_routing_adapter_v128, modular_routing_config_v128, 1_030_022),
    ),
)
def test_v129r1_fair_development_arms_close_and_prior_reduces_labels(builder, config_builder, seed):
    source = _source()
    config = config_builder()
    adapter = builder(seed, config)
    config["families"][adapter.family]["maximum_acquisition_labels"] = 320
    arms = acquire_matched_fair_unified_factor_arms_v129r1(
        adapter,
        derive_artifact_factor_projection_v120(source),
        source,
        config,
    )
    prior = arms["FACTOR_PRIOR_ON"]["document"]
    strict = arms["STRICT_NO_PRIOR"]["document"]
    assert prior["fair_witness_blind_path_first_backtracking"] is True
    assert prior["generation_witness_accessed"] is False
    assert prior["reachable_frontier_exhaustion_used_as_stopping_input"] is False
    assert prior["ground_support_labels"] < strict["ground_support_labels"] <= 320
