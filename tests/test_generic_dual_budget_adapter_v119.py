from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_genesis_authorized_program_branch_sequence_v119 import (
    run_genesis_authorized_program_branch_sequence_v119,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    build_dual_budget_adapter_v119,
    dual_budget_config_v119,
)
from acfqp.source_unseen_partial_acquisition_v119 import (
    acquire_source_unseen_partial_model_v119,
)


def test_v119_development_source_unseen_partial_model_and_sequence():
    config = dual_budget_config_v119()
    adapter = build_dual_budget_adapter_v119(1_031_001, config)
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    acquired = acquire_source_unseen_partial_model_v119(
        adapter, factor_library, config
    )
    prior = acquired["partial"]
    candidate = prior["candidate"].public_document
    assert candidate["complete_world_model_claimed"] is False
    assert candidate["unknown_residual_target_columns"]
    strict = acquired["strict_control"]["document"]
    assert strict["outcome_kind"] == "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR"
    assert strict["complete_candidate"] is None
    sequence = run_genesis_authorized_program_branch_sequence_v119(
        adapter,
        prior["candidate"],
        prior["rows"],
        prior["document"]["ground_support_labels"],
        episode_indices=(260, 261, 262),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    base = sequence["genesis_authorized_base_sequence"]
    assert all(row["success"] for row in base["episodes"])
    assert base["every_new_ground_query_followed_a_failed_certificate"] is True
    assert base["planner_consumed_compiled_successor_without_raw_transition_argument"] is True
    assert sequence["compiled_model_cache_or_receipt_used_as_safety_authority"] is False
    assert sequence["same_epoch_genesis_authorized_cache_hit_count"] > 0
