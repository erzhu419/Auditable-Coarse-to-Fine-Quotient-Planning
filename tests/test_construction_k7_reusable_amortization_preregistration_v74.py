from acfqp.construction_k7_reusable_amortization_preregistration_v74 import (
    AMORTIZATION_TARGET_EPISODE_INDICES,
    campaign_config_v74,
    freeze_reusable_amortization_preregistration_v74,
    verify_reusable_amortization_preregistration_v74,
)


def test_v74_preregistration_freezes_fresh_multi_episode_target_horizon():
    value = verify_reusable_amortization_preregistration_v74(
        freeze_reusable_amortization_preregistration_v74()
    )
    document = value.to_document()
    identity = document["identity_contract"]
    assert tuple(identity["fresh_target_episode_indices"]) == tuple(range(2, 34))
    assert len(AMORTIZATION_TARGET_EPISODE_INDICES) == 32
    assert identity["target_episodes_disjoint_from_v73_target_episode_one"] is True
    assert identity["target_episodes_disjoint_from_source"] is True
    assert document["fresh_registered_v74_execution_performed"] is False


def test_v74_gate_and_incremental_sample_amortization_are_preregistered():
    document = freeze_reusable_amortization_preregistration_v74().to_document()
    gate = document["registered_gate"]
    contract = document["sample_amortization_contract"]
    assert gate["positive_aggregate_savings_required_in_every_target_episode"] is True
    assert gate["incremental_break_even_required_within_registered_horizon"] is True
    assert contract["shared_partial_acquisition_excluded_as_common_to_both_arms"] is True
    assert contract["empirical_incremental_sample_amortization_only"] is True
    assert contract["official_N_break_even_claimed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign_config_v74()["worker_count"] == 6
