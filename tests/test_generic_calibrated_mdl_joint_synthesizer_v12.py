from acfqp.generic_calibrated_mdl_joint_synthesizer_v12 import (
    calibrated_mdl_predictive_stop_update_v12,
)


def test_v12_stop_surface_has_no_floor_block_or_frontier_input():
    names = calibrated_mdl_predictive_stop_update_v12.__code__.co_varnames
    assert "minimum_candidate_labels" not in names
    assert "confirmation_block_size" not in names
    assert "witness_blind_reachable_frontier_exhausted" not in names
    assert "post_issuance_exact_prediction_success_count" in names
    assert "global_alpha_denominator" in names
    assert "success_evalue_multiplier_denominator" in names
