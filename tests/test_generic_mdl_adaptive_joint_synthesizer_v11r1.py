from acfqp.generic_mdl_adaptive_joint_synthesizer_v11r1 import (
    mdl_confidence_or_exact_frontier_stop_update_v11r1,
)


def test_v11r1_surface_has_no_floor_or_confirmation_block():
    names = mdl_confidence_or_exact_frontier_stop_update_v11r1.__code__.co_varnames
    assert "minimum_candidate_labels" not in names
    assert "confirmation_block_size" not in names
    assert "witness_blind_reachable_frontier_exhausted" in names
