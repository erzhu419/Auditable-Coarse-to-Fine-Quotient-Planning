import pytest

from acfqp.certificate_delta_only_invalidation_campaign_core_v176 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    build_certificate_delta_only_invalidation_occurrence_v176,
    certificate_delta_only_invalidation_campaign_config_v176,
)


def test_v176_campaign_config_preserves_matched_family_caps():
    config = certificate_delta_only_invalidation_campaign_config_v176()
    assert config["families"][PACKET_FAMILY]["maximum_acquisition_labels"] == 2_048
    assert config["families"][RESERVOIR_FAMILY]["maximum_acquisition_labels"] == 2_048


def test_v176_occurrence_rejects_unregistered_family_before_outcomes():
    with pytest.raises(ValueError, match="not registered"):
        build_certificate_delta_only_invalidation_occurrence_v176(
            {},
            family="UNREGISTERED",
            seed=1,
            episode_indices=(1, 2),
            bank_raw=b"",
            verification_raw=b"",
            classifier_receipt_raw=b"",
        )
