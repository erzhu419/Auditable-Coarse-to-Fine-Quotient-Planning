from acfqp.construction_k7_portable_priority_preregistration_v75r1 import (
    FRESH_TARGET_SEEDS,
    SOURCE_SEED_BY_FAMILY,
    campaign_config_v75r1,
    freeze_portable_priority_preregistration_v75r1,
    verify_portable_priority_preregistration_v75r1,
)


def test_v75r1_preregistration_freezes_fresh_successor_identities():
    value = verify_portable_priority_preregistration_v75r1(
        freeze_portable_priority_preregistration_v75r1()
    )
    document = value.to_document()
    targets = {seed for seeds in FRESH_TARGET_SEEDS.values() for seed in seeds}
    assert len(targets) == 4
    assert min(targets) > 762_000
    assert targets.isdisjoint(SOURCE_SEED_BY_FAMILY.values())
    assert document["identity_contract"][
        "source_priority_and_target_episode_indices_pairwise_disjoint"
    ] is True
    assert document["fresh_registered_v75r1_execution_performed"] is False


def test_v75r1_contract_preserves_failure_and_query_only_authority():
    document = freeze_portable_priority_preregistration_v75r1().to_document()
    assert document["failure_driven_successor_contract"][
        "v75_gate_or_target_identity_reused"
    ] is False
    assert document["failure_driven_successor_contract"][
        "portable_priority_is_not_a_ground_or_safety_authority"
    ] is True
    assert document["registered_gate"]["required_fresh_target_occurrence_count"] == 4
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign_config_v75r1()["target_worker_count"] == 4
