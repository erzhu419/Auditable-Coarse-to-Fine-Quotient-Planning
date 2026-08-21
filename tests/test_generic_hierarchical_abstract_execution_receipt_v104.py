from pathlib import Path

from acfqp.generic_hierarchical_abstract_execution_receipt_v104 import (
    build_hierarchical_abstract_execution_receipt_v104,
    verify_hierarchical_abstract_execution_receipt_v104,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v104_frozen_v103_receipts_separate_full_partial_and_exact_sources():
    campaign = loads_canonical_json(
        Path(".tmp/exact-freeze/v103_receipted_utilization_campaign.json").read_bytes()
    )
    counts = {"FULL_POST_DEPENDENCY_WORLD_MODEL": 0, "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK": 0, "EXACT_CERTIFICATE_POLICY_ONLY": 0}
    for occurrence in campaign["target_occurrences"]:
        sequence = occurrence["meta_prior_persistent_receipted_sequence"]
        episodes = [sequence["first_agreement_shielded_online_episode"], *sequence["later_persistent_episodes"]]
        for episode in episodes:
            for base in episode["abstract_execution_receipts"]:
                receipt = verify_hierarchical_abstract_execution_receipt_v104(
                    build_hierarchical_abstract_execution_receipt_v104(
                        episode_index=episode["episode_index"], base_receipt=base
                    )
                )
                counts[receipt["abstract_ordering_source"]] += 1
    assert counts == {
        "FULL_POST_DEPENDENCY_WORLD_MODEL": 13,
        "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK": 52,
        "EXACT_CERTIFICATE_POLICY_ONLY": 6,
    }
