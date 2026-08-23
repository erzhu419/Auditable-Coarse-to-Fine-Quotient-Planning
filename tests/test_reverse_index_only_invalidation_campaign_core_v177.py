import pytest

from acfqp.reverse_index_only_invalidation_campaign_core_v177 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    build_reverse_index_only_invalidation_occurrence_v177,
    reverse_index_only_invalidation_campaign_config_v177,
)


def test_v177_campaign_config_preserves_matched_family_caps():
    config = reverse_index_only_invalidation_campaign_config_v177()
    assert config["families"][PACKET_FAMILY]["maximum_acquisition_labels"] == 2_048
    assert config["families"][RESERVOIR_FAMILY]["maximum_acquisition_labels"] == 2_048


def test_v177_occurrence_rejects_unregistered_family_before_outcomes():
    with pytest.raises(ValueError, match="not registered"):
        build_reverse_index_only_invalidation_occurrence_v177(
            {},
            family="UNREGISTERED",
            seed=1,
            episode_indices=(1, 2),
            bank_raw=b"",
            verification_raw=b"",
            classifier_receipt_raw=b"",
        )
