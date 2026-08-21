import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_sequence_wide_agreement_shielded_campaign_v100 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v100_frozen_campaign_will_not_rerun_the_same_identity():
    assert campaign.pre.PREREGISTRATION_ID == (
        "414e2cc6cd9170d4228097d756dbc7106eccbf07bc198366fc2fcd968b5ea9ea"
    )
    assert campaign.CAMPAIGN_ID == (
        "ce5886a86036c5f1163fcd98b5566c5dc5ca981405d433096944dc0d7c293a9a"
    )
    with pytest.raises(
        campaign.ConstructionK7SequenceWideAgreementShieldedCampaignV100Error
    ):
        campaign.run_sequence_wide_agreement_shielded_campaign_v100(
            b"", b"", b"", b""
        )


def test_v100_exact_registered_success_is_preserved():
    raw = Path(
        ".tmp/exact-freeze/v100_sequence_wide_agreement_shielded_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["passed_target_occurrence_count"] == 4
    assert document["accounting"]["meta_activation"] == 124
    assert document["accounting"]["no_prior_activation"] == 152
    assert document["accounting"]["meta_labels"] == 270
    assert document["accounting"]["no_prior_labels"] == 270
    assert document["accounting"]["direct_labels"] == 549
    assert all(
        row["sequence_wide_path_coverage"][
            "both_paths_observed_somewhere_in_persistent_sequence"
        ]
        for row in document["target_occurrences"]
    )
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
