import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_agreement_shielded_campaign_v99 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v99_frozen_failure_will_not_rerun_the_same_identity():
    assert campaign.pre.PREREGISTRATION_ID == (
        "1fa4860d395dd4c4d869d51c960d92b61565e3f06713c51e3ef40648ab4fcae6"
    )
    assert campaign.CAMPAIGN_ID == (
        "2af478cf92b8f6ccb1869042a923487c0f5eb859dc4cbacfdef4a47643930bfd"
    )
    with pytest.raises(campaign.ConstructionK7AgreementShieldedCampaignV99Error):
        campaign.run_agreement_shielded_campaign_v99(b"", b"", b"", b"")


def test_v99_exact_registered_failure_is_preserved():
    raw = Path(".tmp/exact-freeze/v99_agreement_shielded_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["passed_target_occurrence_count"] == 3
    assert document["registered_gate"][
        "aggregate_model_activation_sample_tax_strictly_reduced"
    ] is True
    assert document["registered_gate"]["aggregate_negative_transfer_absent"] is True
    assert document["accounting"]["meta_activation"] == 175
    assert document["accounting"]["no_prior_activation"] == 199
    assert document["accounting"]["meta_labels"] == 320
    assert document["accounting"]["no_prior_labels"] == 320
    failed = [
        row for row in document["target_occurrences"] if not row["registered_gate"]["passed"]
    ]
    assert len(failed) == 1
    assert failed[0]["seed"] == 1_005_101
    assert failed[0]["registered_gate"]["agreement_shield_exercised"] is False
    assert failed[0]["meta_prior_persistent_sequence"][
        "later_agreement_shield_accept_receipt_count"
    ] == 2
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
