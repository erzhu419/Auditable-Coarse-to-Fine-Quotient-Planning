import pytest

from acfqp.certificate_delta_invalidation_campaign_core_v175 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    build_certificate_delta_invalidation_occurrence_v175,
    certificate_delta_invalidation_campaign_config_v175,
)


def test_v175_campaign_config_keeps_matched_family_caps():
    config = certificate_delta_invalidation_campaign_config_v175()
    assert config["families"][PACKET_FAMILY]["maximum_acquisition_labels"] == 2_048
    assert config["families"][RESERVOIR_FAMILY]["maximum_acquisition_labels"] == 2_048


def test_v175_occurrence_rejects_unregistered_family_before_outcomes():
    with pytest.raises(ValueError, match="not registered"):
        build_certificate_delta_invalidation_occurrence_v175(
            {},
            family="UNREGISTERED",
            seed=1,
            episode_indices=(1, 2),
            bank_raw=b"",
            verification_raw=b"",
            classifier_receipt_raw=b"",
        )

