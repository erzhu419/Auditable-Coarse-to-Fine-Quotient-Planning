from pathlib import Path

import pytest

from acfqp import construction_k7_generic_factor_planner_preregistration_v122 as pre


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def _freeze():
    return pre.freeze_generic_factor_planner_preregistration_v122(
        _sources(),
        (ROOT / "v121r1_generic_subprogram_campaign.json").read_bytes(),
        (ROOT / "v121r1_generic_subprogram_verification.json").read_bytes(),
    )


def test_v122_preregistration_is_outcome_free_and_source_closed():
    value = _freeze()
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["source_closure"][
        "frozen_before_any_registered_v122_target_outcome"
    ] is True
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "legacy_shape_specific_planner_execution_adapter_present"
    ] is False
    assert document["claim_boundary"]["registered_v122_target_outcome_observed"] is False
    assert document["claim_boundary"]["generic_planner_execution_adapter_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v122_preregistration_rejects_changed_predecessor():
    changed = bytearray((ROOT / "v121r1_generic_subprogram_campaign.json").read_bytes())
    changed[len(changed) // 2] ^= 1
    pre._CACHE = None
    with pytest.raises(Exception):
        pre.freeze_generic_factor_planner_preregistration_v122(
            _sources(), bytes(changed),
            (ROOT / "v121r1_generic_subprogram_verification.json").read_bytes(),
        )
    pre._CACHE = None
