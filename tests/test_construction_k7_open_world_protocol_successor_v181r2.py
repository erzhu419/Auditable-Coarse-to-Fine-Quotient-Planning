from __future__ import annotations

from acfqp import construction_k7_open_world_protocol_successor_v181r2 as successor


def test_v181r2_successor_preserves_failure_and_changes_semantics_not_cap() -> None:
    document = successor.freeze_open_world_protocol_successor_v181r2().to_document()
    assert document["preserved_v181r1_failure_id"] == successor.PRESERVED_V181R1_FAILURE_ID
    assert document["predecessor_failure_reclassified_as_success"] is False
    assert document["same_v181r1_identity_rerun_forbidden"] is True
    assert document["correction"]["resource_cap_increased_relative_to_v181r1"] is False
    assert document["correction"]["cyclic_residual_carrier_derived_from_observed_coordinate"] is True
    assert document["durable_progress_protocol"]["checkpoint_after_every_acquisition_block"] is True


def test_v181r2_successor_is_outcome_free_and_keeps_all_claims_locked() -> None:
    document = successor.freeze_open_world_protocol_successor_v181r2().to_document()
    assert document["manifest_count"] == 3
    assert document["manifest_reveal_bytes_embedded"] is False
    assert document["target_outcomes_accessed"] is False
    assert document["target_denominator"]["total_episode_count"] == 72
    assert all(
        value in {False, None, "NOT_RUN"}
        for value in document["claim_locks"].values()
    )
