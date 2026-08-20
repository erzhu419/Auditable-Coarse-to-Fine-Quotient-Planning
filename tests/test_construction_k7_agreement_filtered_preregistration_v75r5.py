from acfqp.construction_k7_agreement_filtered_preregistration_v75r5 import (
    FRESH_TARGET_SEEDS,
    freeze_agreement_filtered_preregistration_v75r5,
)


def test_v75r5_preregistration_freezes_matched_filter_ablation():
    document = freeze_agreement_filtered_preregistration_v75r5().to_document()
    assert min(seed for values in FRESH_TARGET_SEEDS.values() for seed in values) > 766_000
    contract = document["failure_driven_successor_contract"]
    assert contract["v75r4_portable_but_harmful_priority_gate_preserved"] is True
    assert contract["target_transition_outcomes_used_to_filter_priority"] is False
    assert document["construction_contract"][
        "same_v44_engine_and_stopping_rule_filtered_vs_model_only"
    ] is True
    assert document["fresh_registered_v75r5_execution_performed"] is False
