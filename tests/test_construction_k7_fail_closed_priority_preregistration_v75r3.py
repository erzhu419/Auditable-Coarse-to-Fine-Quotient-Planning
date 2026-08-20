from acfqp.construction_k7_fail_closed_priority_preregistration_v75r3 import (
    FRESH_TARGET_SEEDS,
    freeze_fail_closed_priority_preregistration_v75r3,
)


def test_v75r3_preregistration_freezes_fail_closed_fresh_targets():
    document = freeze_fail_closed_priority_preregistration_v75r3().to_document()
    assert min(seed for values in FRESH_TARGET_SEEDS.values() for seed in values) > 764_000
    assert document["failure_driven_successor_contract"][
        "v75r2_aggregation_failure_preserved"
    ] is True
    assert document["construction_contract"][
        "target_arm_failures_are_retained_before_aggregation"
    ] is True
    assert document["fresh_registered_v75r3_execution_performed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
