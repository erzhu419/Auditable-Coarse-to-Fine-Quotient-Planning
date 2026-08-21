from pathlib import Path

import pytest

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import build_dual_budget_adapter_v119, dual_budget_config_v119
from acfqp.generic_inventory_assembly_adapter_v118 import build_inventory_assembly_adapter_v118, inventory_assembly_config_v118
from acfqp.generic_modular_routing_adapter_v128 import build_modular_routing_adapter_v128, modular_routing_config_v128
from acfqp.unified_factor_prior_ablation_acquisition_v129 import acquire_matched_unified_factor_arms_v129


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
        (build_inventory_assembly_adapter_v118, inventory_assembly_config_v118, 1_030_007),
        (build_dual_budget_adapter_v119, dual_budget_config_v119, 1_030_008),
        (build_modular_routing_adapter_v128, modular_routing_config_v128, 1_030_009),
    ),
)
def test_v129_development_matched_arms_share_synthesizer_carrier_and_stop(builder, config_builder, seed):
    source = _source()
    config = config_builder()
    config["families"][builder(seed, config).family]["maximum_acquisition_labels"] = 2_048
    adapter = builder(seed, config)
    arms = acquire_matched_unified_factor_arms_v129(
        adapter,
        derive_artifact_factor_projection_v120(source),
        source,
        config,
    )
    prior = arms["FACTOR_PRIOR_ON"]["document"]
    strict = arms["STRICT_NO_PRIOR"]["document"]
    assert prior["only_arm_switch_is_registered_factor_prior"] is True
    assert strict["only_arm_switch_is_registered_factor_prior"] is True
    assert prior["same_generic_atomic_hypothesis_pool"] is True
    assert strict["same_generic_atomic_hypothesis_pool"] is True
    assert prior["same_stopping_rule_function"] is True
    assert strict["same_stopping_rule_function"] is True
    assert prior["ground_support_labels"] <= 2_048
    assert strict["ground_support_labels"] <= 2_048
    assert prior["complete_world_model_claimed"] is False
