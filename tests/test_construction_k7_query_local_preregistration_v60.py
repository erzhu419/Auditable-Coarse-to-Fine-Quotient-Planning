from acfqp import construction_k7_query_local_preregistration_v60 as subject


def test_v60_preregistration_is_outcome_free_query_local_and_raw_replayable():
    document = subject.freeze_query_local_preregistration_v60().to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["raw_evidence_contract"]["symmetric_common_prefix_reconstructible_from_bytes"] is True
    assert document["query_local_recovery_contract"]["stream_prefix_residual_recovery_available"] is False
    assert document["query_local_recovery_contract"]["every_ground_legality_or_transition_query_requires_prior_failed_certificate"] is True
    assert document["matched_stopping_contract"]["reachable_frontier_exhaustion_stop_available"] is False
