import os

import pytest

from acfqp.construction_k7_replayable_coordinate_campaign_v88 import (
    CAMPAIGN_ID,
    run_replayable_coordinate_campaign_v88,
)


def test_v88_campaign_identity_is_frozen():
    assert CAMPAIGN_ID == (
        "041f758ee32cb6fdef0b1218a23bdbfe47a115781ef1fc8f9c557a79a7b065b2"
    )


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
    assert document["sample_tax_reduction_verified"] is False
    assert document["official_scalar_cost"] is None
