import pytest

from acfqp.indexed_lazy_invalidation_campaign_core_v178 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    build_indexed_lazy_invalidation_occurrence_v178,
    indexed_lazy_invalidation_campaign_config_v178,
)


def test_v178_campaign_config_preserves_matched_family_caps():
    config = indexed_lazy_invalidation_campaign_config_v178()
    assert config["families"][PACKET_FAMILY]["maximum_acquisition_labels"] == 2_048
    assert config["families"][RESERVOIR_FAMILY]["maximum_acquisition_labels"] == 2_048


def test_v178_occurrence_rejects_unregistered_family_before_outcomes():
    with pytest.raises(ValueError, match="not registered"):
        build_indexed_lazy_invalidation_occurrence_v178(
            {},
            family="UNREGISTERED",
            seed=1,
            episode_indices=(1, 2),
            bank_raw=b"",
            verification_raw=b"",
            classifier_receipt_raw=b"",
        )
