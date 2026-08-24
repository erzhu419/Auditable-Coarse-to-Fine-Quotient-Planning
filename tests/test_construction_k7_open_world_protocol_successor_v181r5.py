from acfqp import construction_k7_open_world_protocol_successor_v181r5 as protocol


def test_v181r5_preregisters_safe_prior_and_cache_without_outcomes() -> None:
    document = protocol.freeze_open_world_protocol_successor_v181r5().to_document()
    assert document["target_outcomes_accessed"] is False
    assert document["manifest_reveal_bytes_embedded"] is False
    assert len(set(document["manifest_commitments"])) == 3
    correction = document["correction"]
    assert correction["v181r4_prior_labels_avoided"] == -32
    assert correction["archive_mdl_discount_removed"] is True
    assert correction["same_mdl_objective_both_arms"] is True
    assert correction["persistent_model_bound_rank_cache_added"] is True
    assert correction["resource_cap_increased_relative_to_v181r4"] is False
    assert correction["finite_candidate_program_catalog_added"] is False
    matched = document["matched_protocol"]
    assert matched["same_confidence_formula_both_arms"] is True
    assert (
        matched[
            "prior_credit_requires_selected_archive_reference_revalidated_on_current_rows"
        ]
        is True
    )
    assert document["protocol_successor_id"] == protocol.EXPECTED_SUCCESSOR_ID


def test_v181r5_claims_remain_locked() -> None:
    locks = protocol.freeze_open_world_protocol_successor_v181r5().to_document()["claim_locks"]
    assert locks["open_world_campaign_completed"] is False
    assert locks["broad_iid_sample_efficiency_claimed"] is False
    assert locks["total_work_dominance_claimed"] is False
    assert locks["official_execution_allowed"] is False
    assert locks["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert locks["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
