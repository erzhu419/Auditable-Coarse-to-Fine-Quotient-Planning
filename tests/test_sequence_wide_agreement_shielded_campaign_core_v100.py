import json
from pathlib import Path

from acfqp.sequence_wide_agreement_shielded_campaign_core_v100 import (
    build_sequence_wide_path_coverage_v100,
)


V99_CAMPAIGN_PATH = Path(".tmp/exact-freeze/v99_agreement_shielded_campaign.json")


def test_v100_corrects_only_the_registered_path_coverage_window():
    campaign = json.loads(V99_CAMPAIGN_PATH.read_bytes())
    failed = next(
        row for row in campaign["target_occurrences"] if row["seed"] == 1_005_101
    )
    assert failed["registered_gate"]["agreement_shield_exercised"] is False
    coverage = build_sequence_wide_path_coverage_v100(failed)
    assert coverage == {
        "schema": "acfqp.sequence_wide_agreement_shield_path_coverage.v100",
        "first_episode_accept_count": 0,
        "first_episode_disagreement_abstention_count": 16,
        "later_episode_accept_count": 2,
        "later_episode_disagreement_abstention_count": 16,
        "persistent_sequence_accept_count": 2,
        "persistent_sequence_disagreement_abstention_count": 32,
        "accept_path_observed_somewhere_in_persistent_sequence": True,
        "disagreement_path_observed_somewhere_in_persistent_sequence": True,
        "both_paths_observed_somewhere_in_persistent_sequence": True,
        "both_paths_required_in_first_episode": False,
        "path_coverage_window_fixed_before_v100_outcomes": True,
    }


def test_v100_does_not_reclassify_a_sequence_missing_either_path():
    campaign = json.loads(V99_CAMPAIGN_PATH.read_bytes())
    observation = campaign["target_occurrences"][0]
    observation["meta_prior_persistent_sequence"][
        "later_agreement_shield_accept_receipt_count"
    ] = 0
    observation["meta_prior_persistent_sequence"][
        "first_agreement_shielded_online_episode"
    ]["agreement_shield_accept_count"] = 0
    coverage = build_sequence_wide_path_coverage_v100(observation)
    assert coverage["accept_path_observed_somewhere_in_persistent_sequence"] is False
    assert coverage["both_paths_observed_somewhere_in_persistent_sequence"] is False
