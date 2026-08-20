from acfqp.construction_k7_reusable_version_space_preregistration_v73 import (
    BALANCED_TARGET_SEEDS,
    COUPLED_TARGET_SEEDS,
    MAINTENANCE_TARGET_SEEDS,
    campaign_config_v73,
    freeze_reusable_version_space_preregistration_v73,
    verify_reusable_version_space_preregistration_v73,
)


def test_v73_preregistration_freezes_fresh_cross_episode_identities():
    value = verify_reusable_version_space_preregistration_v73(
        freeze_reusable_version_space_preregistration_v73()
    )
    document = value.to_document()
    seeds = BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    assert len(seeds) == len(set(seeds)) == 6
    assert min(seeds) > 750_000
    identities = document["fresh_occurrence_identities"]
    assert identities["source_and_target_episode_disjoint"] is True
    assert document["source_closure"][
        "frozen_before_any_registered_v73_source_or_target_outcome"
    ] is True
    assert document["fresh_registered_v73_execution_performed"] is False


def test_v73_gate_requires_actual_target_label_reduction_without_authority_upgrade():
    document = freeze_reusable_version_space_preregistration_v73().to_document()
    assert document["registered_gate"][
        "aggregate_actual_target_label_reduction_required"
    ] is True
    assert document["registered_gate"]["minimum_compiled_occurrence_count"] == 3
    assert document["construction_contract"][
        "query_local_exact_overlay_only_safety_authority"
    ] is True
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign_config_v73()["worker_count"] == 6
