from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_expression_checkpoint_campaign_v33 as campaign
from acfqp import construction_k7_standard_2048_expression_checkpoint_independent_verifier_v33 as verifier


@pytest.fixture(scope="module")
def verified():
    produced = campaign.run_standard_2048_expression_checkpoint_campaign_v33()
    return verifier.verify_standard_2048_expression_checkpoint_bytes_independently_v33(
        produced.canonical_bytes
    )


def test_checkpoint_binding_is_reconstructed_without_producer() -> None:
    binding = verifier._binding_expected()
    assert binding["target_probability_query_count_in_segment"] == 0
    assert len(binding["source_facts"]) == 4


def test_checkpoint_campaign_replays_independently(verified) -> None:
    document = verified.to_document()
    count = document["independently_replayed_checkpoint_certificate_count"]
    assert document["all_registered_checkpoint_h3_certificates_independently_replayed"] is True
    assert 0 < count <= 512
    assert document["all_registered_global_index_seeded_transitions_independently_replayed"] is True
    assert 2 <= document["independently_replayed_cold_target_checkpoint_count"] <= 6
    assert document["four_labels_amortized_over_all_cumulative_certificates_verified"] is True
    assert document["cumulative_certificate_count"] == sum(
        campaign.pre.SOURCE_DECISION_COUNTS
    ) + count
    assert document["full_game_or_tile_2048_verified"] is True
    assert document["official_execution_allowed"] is False


def test_campaign_semantic_tamper_is_rejected() -> None:
    document = campaign.run_standard_2048_expression_checkpoint_campaign_v33().to_document()
    forged = copy.deepcopy(document)
    forged["episodes"][1]["closure_reason"] = "REGISTERED_CHECKPOINT_LIMIT"
    from acfqp.phase3e_ids import canonical_json_bytes

    with pytest.raises(
        verifier.ConstructionK7Standard2048ExpressionCheckpointIndependentVerifierV33Error
    ):
        verifier.verify_standard_2048_expression_checkpoint_bytes_independently_v33(
            canonical_json_bytes(forged)
        )
