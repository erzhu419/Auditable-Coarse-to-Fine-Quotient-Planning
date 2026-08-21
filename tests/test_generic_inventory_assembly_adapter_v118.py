from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as acquisition
from acfqp.generic_dependency_derived_program_branch_sequence_v117 import (
    run_dependency_derived_program_branch_sequence_v117,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    build_inventory_assembly_adapter_v118,
    inventory_assembly_config_v118,
)


def test_v118_development_inventory_acquisition_and_abstract_sequence():
    config = inventory_assembly_config_v118()
    adapter = build_inventory_assembly_adapter_v118(1_030_001, config)
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    acquired = acquisition.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )
    prior = acquired["ANONYMOUS_FACTOR_PRIOR_ON"]
    no_prior = acquired["STRICT_NO_PRIOR"]
    # Retain the unfavourable development result: this seed pays one extra
    # prior-on label.  V118 is a transfer-construction Gate, not a sample-tax
    # improvement claim.
    assert prior["document"]["ground_support_labels"] == 20
    assert no_prior["document"]["ground_support_labels"] == 19
    sequence = run_dependency_derived_program_branch_sequence_v117(
        adapter,
        prior["candidate"],
        prior["rows"],
        prior["document"]["ground_support_labels"],
        episode_indices=(257, 258, 259),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    base = sequence["dependency_derived_program_branch_base_sequence"]
    assert all(row["success"] for row in base["episodes"])
    assert base["every_new_ground_query_followed_a_failed_certificate"] is True
    assert base["planner_consumed_compiled_successor_without_raw_transition_argument"] is True
    assert sequence["compiled_model_cache_or_receipt_used_as_safety_authority"] is False
