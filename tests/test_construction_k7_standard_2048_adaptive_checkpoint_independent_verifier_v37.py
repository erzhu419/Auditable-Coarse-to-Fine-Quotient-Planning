from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_adaptive_checkpoint_campaign_v37 as campaign
from acfqp import construction_k7_standard_2048_adaptive_checkpoint_independent_verifier_v37 as verifier


@pytest.fixture(scope="module")
def verified():
    produced = campaign.run_standard_2048_adaptive_checkpoint_campaign_v37()
    return verifier.verify_standard_2048_adaptive_checkpoint_bytes_independently_v37(
        produced.canonical_bytes
    )


def test_checkpoint_binding_is_reconstructed_without_producer() -> None:
    binding = verifier._binding_expected()
    assert binding["target_probability_query_count_in_segment"] == 0
    assert len(binding["source_facts"]) == 4


def test_checkpoint_campaign_replays_independently(verified) -> None:
    document = verified.to_document()
    assert document["all_checkpoint_h3_certificates_independently_replayed"] is True
    assert document["all_global_index_seeded_transitions_independently_replayed"] is True
    assert document["all_registered_cold_target_checkpoints_independently_replayed"] is True
    assert document["v35_proof_and_overlay_binding_verified"] is True
    assert document["zero_additional_model_labels_verified"] is True
    assert document["failed_verification_attempt"] == verifier.FAILED_VERIFICATION_ATTEMPT
    assert document["verification_successor_replays_retained_campaign_bytes"] is True
    assert document["official_execution_allowed"] is False


def test_campaign_semantic_tamper_is_rejected() -> None:
    document = campaign.run_standard_2048_adaptive_checkpoint_campaign_v37().to_document()
    forged = copy.deepcopy(document)
    forged["episodes"][0]["decisions"][0]["global_decision_index"] = 127
    from acfqp.phase3e_ids import canonical_json_bytes

    with pytest.raises(
        verifier.ConstructionK7Standard2048AdaptiveCheckpointIndependentVerifierV37Error
    ):
        verifier.verify_standard_2048_adaptive_checkpoint_bytes_independently_v37(
            canonical_json_bytes(forged)
        )
