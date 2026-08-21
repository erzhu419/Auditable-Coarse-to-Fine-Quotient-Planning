from acfqp import construction_k7_identity_short_circuited_epoch_preregistration_v111 as v111_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_identity_short_circuited_epoch_sequence_v111 import (
    run_identity_short_circuited_epoch_sequence_v111,
)
from acfqp.generic_incremental_abstract_successor_sequence_v113 import (
    run_incremental_abstract_successor_sequence_v113,
)


def test_v113_incremental_successor_matches_full_rebuild_and_v111_execution():
    config = v111_pre.campaign_config_v111()
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "MAINTENANCE_CASCADE", 1_023_103, config
    )
    acquisition = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = {
        "episode_indices": (201, 202),
        "maximum_abstract_depth": config["maximum_abstract_depth"],
        "maximum_execution_steps": config["maximum_execution_steps"],
        "maximum_incremental_certificate_ground_support_labels": 100_000,
    }
    incremental = run_incremental_abstract_successor_sequence_v113(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    full_rebuild = run_identity_short_circuited_epoch_sequence_v111(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    assert [row["action_keys"] for row in incremental["episodes"]] == [
        row["action_keys"] for row in full_rebuild["episodes"]
    ]
    assert [
        row["abstract_execution_receipts"] for row in incremental["episodes"]
    ] == [row["abstract_execution_receipts"] for row in full_rebuild["episodes"]]
    assert incremental["lifetime_target_ground_support_labels"] == full_rebuild[
        "lifetime_target_ground_support_labels"
    ]
    assert incremental["execution_step_count"] == full_rebuild[
        "execution_step_count"
    ]
    assert incremental[
        "planner_consumed_compiled_successor_without_raw_transition_argument"
    ] is True
    assert incremental[
        "all_model_successors_exactly_equal_full_v105_rebuild"
    ] is True
    assert incremental["model_compilation_events_avoided_against_full_rebuild"] > 0
    assert incremental["every_new_ground_query_followed_a_failed_certificate"] is True
    assert incremental["complete_ground_world_model_synthesized"] is False
    assert incremental["official_execution_allowed"] is False
