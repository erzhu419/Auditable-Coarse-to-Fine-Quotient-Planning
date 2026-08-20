from acfqp.construction_k7_successor_version_space_failure_v72 import FAILURE_ID
from acfqp.construction_k7_successor_version_space_preregistration_v72r1 import (
    BALANCED_TARGET_SEEDS,
    COUPLED_TARGET_SEEDS,
    MAINTENANCE_TARGET_SEEDS,
    campaign_config_v72r1,
    freeze_successor_version_space_preregistration_v72r1,
    verify_successor_version_space_preregistration_v72r1,
)


def test_v72r1_preregistration_binds_failure_and_fresh_identities():
    value = verify_successor_version_space_preregistration_v72r1(
        freeze_successor_version_space_preregistration_v72r1()
    )
    document = value.to_document()
    seeds = BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    assert min(seeds) > 740_000
    assert len(seeds) == len(set(seeds)) == 6
    assert document["frozen_predecessors"]["preserved_v72_failure_id"] == FAILURE_ID
    assert document["failure_correction"]["same_v72_identity_rerun"] is False
    assert document["source_closure"][
        "frozen_before_any_registered_v72r1_target_outcome"
    ] is True
    assert document["fresh_registered_target_execution_performed"] is False


def test_v72r1_gate_and_resource_schedule_are_frozen():
    document = freeze_successor_version_space_preregistration_v72r1().to_document()
    assert document["registered_gate"]["sample_reduction_required"] is False
    assert document["registered_gate"]["abstention_allowed"] is True
    assert document["resource_schedule"]["worker_count_frozen_cap"] == 6
    assert campaign_config_v72r1()["worker_count"] == 6
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
