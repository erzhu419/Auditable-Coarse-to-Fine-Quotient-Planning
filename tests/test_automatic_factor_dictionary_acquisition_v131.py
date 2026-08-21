from pathlib import Path

import pytest

from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.automatic_minimal_factor_dictionary_v131 import (
    derive_automatic_minimal_factor_dictionary_v131,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    build_dual_budget_adapter_v119,
    dual_budget_config_v119,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    build_inventory_assembly_adapter_v118,
    inventory_assembly_config_v118,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.automatic_factor_dictionary_acquisition_v131 import (
    acquire_matched_automatic_dictionary_factor_arms_v131,
)


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
        (build_inventory_assembly_adapter_v118, inventory_assembly_config_v118, 1_031_101),
        (build_dual_budget_adapter_v119, dual_budget_config_v119, 1_031_102),
        (build_modular_routing_adapter_v128, modular_routing_config_v128, 1_031_103),
    ),
)
def test_v131_automatic_dictionary_development_arms_close_without_fixed_multiplier(
    builder, config_builder, seed
):
    source = _source()
    source_library = derive_artifact_factor_projection_v120(source)
    dictionary = derive_automatic_minimal_factor_dictionary_v131(
        source_library, source
    )
    config = config_builder()
    adapter = builder(seed, config)
    config["families"][adapter.family]["maximum_acquisition_labels"] = 320
    arms = acquire_matched_automatic_dictionary_factor_arms_v131(
        adapter,
        dictionary,
        source,
        config,
    )
    prior = arms["NORMALIZED_FACTOR_PRIOR_ON"]["document"]
    strict = arms["STRICT_NO_PRIOR"]["document"]
    assert prior["ground_support_labels"] < strict["ground_support_labels"] <= 320
    assert prior["terminal_stop_update"][
        "fixed_two_to_library_cardinality_prior_multiplier_present"
    ] is False
    assert prior["terminal_stop_update"][
        "combined_normalized_prior_odds_denominator"
    ] > 0
    assert prior["candidate"]["automatic_dictionary_calibration"][
        "fixed_mixture_weight_supplied_by_target"
    ] is False
    assert prior["candidate"]["automatic_dictionary_calibration"][
        "target_outcomes_accessed"
    ] is False
    assert prior["candidate"]["normalized_artifact_uniform_mixture_prior_present"] is True
    assert strict["candidate"]["normalized_artifact_uniform_mixture_prior_present"] is False
