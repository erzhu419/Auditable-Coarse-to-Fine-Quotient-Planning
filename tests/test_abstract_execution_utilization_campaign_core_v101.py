import json
from pathlib import Path

from acfqp.abstract_execution_utilization_campaign_core_v101 import (
    derive_abstract_execution_utilization_v101,
)


def test_v101_metric_uses_actual_executed_actions_not_search_receipt_count():
    campaign = json.loads(
        Path(
            ".tmp/exact-freeze/v100_sequence_wide_agreement_shielded_campaign.json"
        ).read_bytes()
    )
    expected = {
        1_007_101: (13, 22),
        1_007_102: (15, 20),
        1_007_103: (10, 13),
        1_007_104: (11, 15),
    }
    for occurrence in campaign["target_occurrences"]:
        sequence = occurrence["frozen_v99_algorithm_observation"][
            "meta_prior_persistent_sequence"
        ]
        result = derive_abstract_execution_utilization_v101(sequence)
        matches, steps = expected[occurrence["seed"]]
        assert result["persistent_sequence_abstract_execution_match_count"] == matches
        assert result["persistent_sequence_execution_step_count"] == steps
        assert result[
            "strict_majority_of_executed_actions_match_abstract_proposal"
        ] is True
        assert result["query_local_exact_overlay_remains_only_safety_authority"] is True


def test_v101_majority_gate_is_strict():
    campaign = json.loads(
        Path(
            ".tmp/exact-freeze/v100_sequence_wide_agreement_shielded_campaign.json"
        ).read_bytes()
    )
    sequence = campaign["target_occurrences"][0][
        "frozen_v99_algorithm_observation"
    ]["meta_prior_persistent_sequence"]
    sequence["first_agreement_shielded_online_episode"][
        "shielded_joint_execution_action_match_count"
    ] = 0
    sequence["later_execution_action_matches_abstract_proposal_count"] = 11
    assert derive_abstract_execution_utilization_v101(sequence)[
        "strict_majority_of_executed_actions_match_abstract_proposal"
    ] is False
