from pathlib import Path

import pytest

from acfqp import construction_k7_indexed_lazy_invalidation_campaign_v178r1 as subject


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v178r1_frozen_campaign_constants_are_terminal_consistent():
    if subject.ATTEMPT_TERMINAL_STATE == "UNEXECUTED":
        assert subject.CAMPAIGN_ID == "0" * 64
        assert subject.FAILURE_ID == "0" * 64
    else:
        assert subject.ATTEMPT_TERMINAL_STATE in {"FROZEN_SUCCESS", "FROZEN_FAILURE"}
        assert (subject.CAMPAIGN_ID != "0" * 64) != (subject.FAILURE_ID != "0" * 64)


def test_v178r1_frozen_attempt_cannot_rerun_after_terminal():
    if subject.ATTEMPT_TERMINAL_STATE == "UNEXECUTED":
        pytest.skip("fresh V178r1 outcome is not yet executed")
    with pytest.raises(subject.ConstructionK7IndexedLazyInvalidationCampaignV178R1Error):
        subject.run_indexed_lazy_invalidation_campaign_v178r1(
            (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
            (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
            (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        )
