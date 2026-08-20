from acfqp.construction_k7_successor_version_space_preregistration_v72 import (
    BALANCED_TARGET_SEEDS,
    COUPLED_TARGET_SEEDS,
    MAINTENANCE_TARGET_SEEDS,
    campaign_config_v72,
    freeze_successor_version_space_preregistration_v72,
    verify_successor_version_space_preregistration_v72,
)


def test_v72_preregistration_is_outcome_free_and_fresh():
    value = verify_successor_version_space_preregistration_v72(
        freeze_successor_version_space_preregistration_v72()
    )
    document = value.to_document()
    seeds = BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    assert len(seeds) == len(set(seeds)) == 6
    assert min(seeds) > 730_000
    assert document["source_closure"][
        "frozen_before_any_registered_v72_target_outcome"
    ] is True
    assert document["fresh_registered_target_execution_performed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v72_only_switches_terminal_prior_and_separates_accounting_axes():
    document = freeze_successor_version_space_preregistration_v72().to_document()
    contract = document["matched_acquisition_contract"]
    assert contract["only_terminal_program_prior_switched"] is True
    assert contract["same_v41_successor_version_space_guard"] is True
    assert contract["status_output_coordinate_used_as_successor_guard_input"] is False
    assert document["registered_gate"]["sample_reduction_required"] is False
    assert all(document["accounting_contract"].values())
    config = campaign_config_v72()
    assert config["worker_count"] == 6
    assert config["maximum_successor_support_states"] == 4_096
