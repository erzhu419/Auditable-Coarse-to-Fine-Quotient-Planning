import os

import pytest

from acfqp.construction_k7_replayable_coordinate_campaign_v88 import (
    CAMPAIGN_ID,
    run_replayable_coordinate_campaign_v88,
)


def test_v88_campaign_identity_starts_unfrozen():
    assert CAMPAIGN_ID == "0" * 64


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REPLAYABLE_COORDINATE_V88") != "1",
    reason="explicit fresh V88 campaign",
)
def test_v88_real_campaign_runs_once():
    document = run_replayable_coordinate_campaign_v88().to_document()
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "raw_alignment_inputs_embedded_on_every_completed_target"
    ] is True
    assert document["official_scalar_cost"] is None
