from acfqp.construction_k7_normalized_priority_preregistration_v75r2 import (
    FRESH_TARGET_SEEDS,
    SOURCE_SEED_BY_FAMILY,
    campaign_config_v75r2,
    freeze_normalized_priority_preregistration_v75r2,
    verify_normalized_priority_preregistration_v75r2,
)


def test_v75r2_preregistration_freezes_fresh_corrective_identities():
    value = verify_normalized_priority_preregistration_v75r2(
        freeze_normalized_priority_preregistration_v75r2()
    )
    document = value.to_document()
    targets = {seed for seeds in FRESH_TARGET_SEEDS.values() for seed in seeds}
    assert len(targets) == 4
    assert min(targets) > 763_000
    assert targets.isdisjoint(SOURCE_SEED_BY_FAMILY.values())
    assert document["failure_driven_successor_contract"][
        "v75r1_pre_campaign_adapter_failure_preserved"
    ] is True
    assert document["fresh_registered_v75r2_execution_performed"] is False


def test_v75r2_contract_separates_domain_and_flat_actions():
    document = freeze_normalized_priority_preregistration_v75r2().to_document()
    contract = document["construction_contract"]
    assert contract["domain_actions_used_only_for_kernel_calls"] is True
    assert contract["flat_raw_actions_used_for_generic_receipts_and_planning"] is True
    assert contract["query_local_exact_overlay_only_safety_authority"] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign_config_v75r2()["target_worker_count"] == 4
