from acfqp.construction_k7_coordinate_aligned_target_preregistration_v87r1 import (
    PREREGISTRATION_ID,
    freeze_coordinate_aligned_target_preregistration_v87r1,
    verify_coordinate_aligned_target_preregistration_v87r1,
)


def test_v87r1_preregistration_is_outcome_free_and_failure_bound():
    value = verify_coordinate_aligned_target_preregistration_v87r1(
        freeze_coordinate_aligned_target_preregistration_v87r1()
    )
    document = value.to_document()
    assert document["frozen_predecessors"]["v87_failed_campaign_id"] == (
        "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
    )
    assert document["fresh_registered_v87r1_execution_performed"] is False
    assert document["construction_contract"][
        "exactly_one_projection_required_before_target_episode"
    ] is True
    assert document["registered_gate"]["target_sample_reduction_required"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v87r1_preregistration_identity_is_frozen():
    assert PREREGISTRATION_ID == (
        "dca32845cd12818f18f5fd463c61c9244c9591317a03590dfa23358e4c74660f"
    )
