import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_persistent_second_domain_campaign_v95 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v95_frozen_campaign_will_not_rerun_the_same_identity():
    assert campaign.CAMPAIGN_ID == (
        "7d23704aa7d6513182d59e6f782417d99c7b9f1dc467fe84f9fba30722ee5eb4"
    )
    with pytest.raises(campaign.ConstructionK7PersistentSecondDomainCampaignV95Error):
        campaign.run_persistent_second_domain_campaign_v95(b"", b"")


def test_v95_exact_successful_persistent_second_domain_campaign_is_preserved():
    raw = Path(
        ".tmp/exact-freeze/v95_persistent_second_domain_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["meta_prior_lifetime_unique_target_labels"] == 78
    assert document["accounting"]["no_prior_lifetime_unique_target_labels"] == 90
    assert document["accounting"]["strict_cold_direct_lifetime_target_labels"] == 310
    assert all(
        row["meta_prior_persistent_sequence"]["transfer_episodes"][1][
            "new_certificate_labels_charged_this_episode"
        ]
        == 0
        for row in document["target_occurrences"]
    )
    assert document[
        "sample_tax_reduction_replicated_in_second_registered_domain"
    ] is True
    assert document[
        "sample_tax_reduction_generalized_beyond_two_registered_domain_families"
    ] is False
    assert document["official_execution_allowed"] is False
