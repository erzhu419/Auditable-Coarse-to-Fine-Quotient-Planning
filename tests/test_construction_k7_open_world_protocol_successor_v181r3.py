from acfqp import construction_k7_open_world_protocol_successor_v181r3 as protocol


def test_v181r3_successor_is_outcome_free_and_fresh() -> None:
    document = protocol.freeze_open_world_protocol_successor_v181r3().to_document()
    assert document["manifest_reveal_bytes_embedded"] is False
    assert document["target_outcomes_accessed"] is False
    assert len(document["manifest_commitments"]) == 3
    assert len(set(document["manifest_commitments"])) == 3
    assert document["preserved_v181r2_failure_id"].startswith("6033595c")
    assert document["same_v181r2_identity_rerun_forbidden"] is True


def test_v181r3_correction_is_accuracy_preserving_and_budget_neutral() -> None:
    correction = protocol.freeze_open_world_protocol_successor_v181r3().to_document()[
        "correction"
    ]
    assert correction["cyclic_residual_search_applied_to_every_integer_coordinate"] is True
    assert correction["full_recompile_required_only_after_model_support_or_terminal_mismatch"] is True
    assert correction["covered_confirmation_block_requires_zero_enumeration_events"] is True
    assert correction["resource_cap_increased_relative_to_v181r2"] is False
    assert correction["finite_candidate_program_catalog_added"] is False


def test_v181r3_claims_remain_locked_before_execution() -> None:
    locks = protocol.freeze_open_world_protocol_successor_v181r3().to_document()[
        "claim_locks"
    ]
    assert locks["open_world_campaign_completed"] is False
    assert locks["broad_iid_sample_efficiency_claimed"] is False
    assert locks["total_work_dominance_claimed"] is False
    assert locks["official_execution_allowed"] is False
    assert locks["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert locks["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
