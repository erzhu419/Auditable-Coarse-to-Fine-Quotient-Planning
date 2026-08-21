from pathlib import Path

from acfqp.generic_hierarchical_abstract_execution_receipt_v104 import (
    build_hierarchical_abstract_execution_receipt_v104,
)
from acfqp.hierarchical_abstract_utilization_campaign_core_v104 import (
    derive_hierarchical_utilization_v104,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v104_derivation_on_frozen_v103_sequence_counts_honest_partial_fallback():
    campaign = loads_canonical_json(
        Path(".tmp/exact-freeze/v103_receipted_utilization_campaign.json").read_bytes()
    )
    predecessor = campaign["target_occurrences"][0][
        "meta_prior_persistent_receipted_sequence"
    ]
    episodes = [
        predecessor["first_agreement_shielded_online_episode"],
        *predecessor["later_persistent_episodes"],
    ]
    receipts = [
        build_hierarchical_abstract_execution_receipt_v104(
            episode_index=episode["episode_index"], base_receipt=receipt
        )
        for episode in episodes
        for receipt in episode["abstract_execution_receipts"]
    ]
    sequence = {
        "v103_receipted_sequence": predecessor,
        "hierarchical_abstract_execution_receipts": receipts,
        "full_post_dependency_world_model_match_count": 3,
        "compiled_partial_world_model_fallback_match_count": 21,
        "exact_certificate_policy_only_count": 0,
        "abstract_model_ordered_execution_count": 24,
    }
    utilization = derive_hierarchical_utilization_v104(sequence)
    assert utilization["abstract_model_ordered_execution_count"] == 24
    assert utilization[
        "strict_majority_of_executed_actions_ordered_by_full_or_explicit_partial_world_model"
    ] is True
    assert utilization["full_post_dependency_world_model_match_count"] == 3
    assert utilization["partial_world_model_incompleteness_is_explicit"] is True
