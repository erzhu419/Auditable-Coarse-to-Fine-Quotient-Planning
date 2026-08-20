from acfqp.construction_k7_cross_occurrence_reuse_preregistration_v75 import (
    FRESH_TARGET_SEEDS,
    SOURCE_SEED_BY_FAMILY,
    campaign_config_v75,
    freeze_cross_occurrence_reuse_preregistration_v75,
    verify_cross_occurrence_reuse_preregistration_v75,
)


def test_v75_preregistration_freezes_disjoint_cross_occurrence_identities():
    value = verify_cross_occurrence_reuse_preregistration_v75(
        freeze_cross_occurrence_reuse_preregistration_v75()
    )
    document = value.to_document()
    identities = document["identity_contract"]
    targets = {seed for seeds in FRESH_TARGET_SEEDS.values() for seed in seeds}
    assert len(targets) == 4
    assert targets.isdisjoint(SOURCE_SEED_BY_FAMILY.values())
    assert identities["source_and_target_seeds_disjoint"] is True
    assert identities["source_and_target_episode_indices_disjoint"] is True
    assert document["fresh_registered_v75_execution_performed"] is False


def test_v75_gate_keeps_cross_occurrence_claim_narrow():
    document = freeze_cross_occurrence_reuse_preregistration_v75().to_document()
    assert document["registered_gate"]["required_compiled_source_count"] == 2
    assert document["registered_gate"]["required_fresh_target_occurrence_count"] == 4
    assert document["construction_contract"][
        "query_local_exact_overlay_only_safety_authority"
    ] is True
    assert document["claim_boundary"]["cross_family_model_reuse_claimed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert campaign_config_v75()["target_worker_count"] == 4
