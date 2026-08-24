from acfqp import construction_k7_open_world_ranked_machine_protocol_v183 as protocol


def test_v183_protocol_is_outcome_free_and_claim_bounded() -> None:
    frozen = protocol.freeze_open_world_ranked_machine_protocol_v183()
    document = frozen.to_document()
    assert document["protocol_id"] == protocol.EXPECTED_PROTOCOL_ID
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["candidate_admission_requires_structural_ranking_proof"] is True
    assert document["finite_carrier_totality_enumeration_forbidden"] is True
    assert document["general_program_termination_decided"] is False
    assert document["proof_system_complete_for_all_terminating_programs"] is False
    assert document["current_occurrence_candidate_set_finite"] is True
    assert document["official_execution_allowed"] is False
