from acfqp.construction_k7_structural_rank_preregistration_v75r4 import (
    FRESH_TARGET_SEEDS,
    freeze_structural_rank_preregistration_v75r4,
)


def test_v75r4_preregistration_freezes_structural_rank_successor():
    document = freeze_structural_rank_preregistration_v75r4().to_document()
    assert min(seed for values in FRESH_TARGET_SEEDS.values() for seed in values) > 765_000
    assert document["failure_driven_successor_contract"][
        "target_transition_outcomes_used_to_translate_priority"
    ] is False
    assert document["construction_contract"][
        "target_local_priority_cannot_supply_ground_or_safety_authority"
    ] is True
    assert document["fresh_registered_v75r4_execution_performed"] is False
