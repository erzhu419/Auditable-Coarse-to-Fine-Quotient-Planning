from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as subject


def test_v59_preregistration_is_fresh_outcome_free_and_symmetric():
    value = subject.freeze_true_bit_symmetric_preregistration_v59()
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["matched_acquisition_contract"]["either_arm_may_stop_first"] is True
    assert document["matched_acquisition_contract"]["symmetric_minimum_common_prefix_post_audit"] is True
    assert document["matched_acquisition_contract"]["reachable_frontier_exhaustion_stop_available"] is False
    assert sum(len(row["target_seeds"]) for key, row in document["target_families"].items() if isinstance(row, dict) and "target_seeds" in row) == 36
