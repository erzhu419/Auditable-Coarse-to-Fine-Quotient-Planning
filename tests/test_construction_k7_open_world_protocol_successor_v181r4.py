from acfqp import construction_k7_open_world_protocol_successor_v181r4 as protocol


def test_v181r4_preregisters_rank_decrease_without_outcomes() -> None:
    document = protocol.freeze_open_world_protocol_successor_v181r4().to_document()
    assert document["target_outcomes_accessed"] is False
    assert document["manifest_reveal_bytes_embedded"] is False
    assert len(set(document["manifest_commitments"])) == 3
    correction = document["correction"]
    assert correction["minimum_worst_case_terminal_distance_computed"] is True
    assert correction["selected_action_requires_strict_rank_decrease_for_every_successor"] is True
    assert correction["resource_cap_increased_relative_to_v181r3"] is False
    assert correction["finite_candidate_program_catalog_added"] is False


def test_v181r4_claims_remain_locked() -> None:
    locks = protocol.freeze_open_world_protocol_successor_v181r4().to_document()["claim_locks"]
    assert locks["open_world_campaign_completed"] is False
    assert locks["broad_iid_sample_efficiency_claimed"] is False
    assert locks["total_work_dominance_claimed"] is False
    assert locks["official_execution_allowed"] is False
    assert locks["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert locks["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
