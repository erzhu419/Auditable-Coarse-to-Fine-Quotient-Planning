from pathlib import Path

import pytest

from acfqp import construction_k7_generic_factor_planner_campaign_v122 as producer


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
CAMPAIGN = ROOT / "v122_generic_factor_planner_campaign.json"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def _run():
    return producer.run_generic_factor_planner_campaign_v122(
        _sources(),
        (ROOT / "v121r1_generic_subprogram_campaign.json").read_bytes(),
        (ROOT / "v121r1_generic_subprogram_verification.json").read_bytes(),
    )


def test_v122_campaign_is_not_frozen_before_registered_execution():
    if producer.CAMPAIGN_ID == "0" * 64:
        assert not CAMPAIGN.exists()
    else:
        assert CAMPAIGN.exists()


@pytest.mark.skipif(
    producer.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN.exists(),
    reason="V122 registered campaign has not been frozen",
)
def test_v122_exact_campaign_is_preserved():
    assert CAMPAIGN.read_bytes() == _run().canonical_bytes
