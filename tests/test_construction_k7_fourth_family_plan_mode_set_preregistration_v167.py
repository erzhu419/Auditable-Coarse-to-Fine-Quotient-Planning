import hashlib

import pytest

from acfqp.construction_k7_fourth_family_plan_mode_set_preregistration_v167 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    campaign_config_v167,
    freeze_fourth_family_plan_mode_set_preregistration_v167,
)


def test_v167_preregistration_is_outcome_free_and_preserves_v166_failure():
    frozen = freeze_fourth_family_plan_mode_set_preregistration_v167()
    document = frozen.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["v167_fourth_family_transfer_observed"] is False
    assert document["frozen_v166_failure"]["same_identity_rerun_forbidden"] is True
    assert document["correction"]["planner_dynamics_changed"] is False
    assert document["correction"]["execution_policy_changed"] is False
    assert all(document["registered_gate"].values())
    assert len(TARGET_OCCURRENCES) == 8
    assert len({row[0] for row in TARGET_OCCURRENCES}) == 4
    assert campaign_config_v167()["target_worker_count"] == 2


def test_v167_frozen_preregistration_identity():
    if PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V167 preregistration not frozen")
    frozen = freeze_fourth_family_plan_mode_set_preregistration_v167()
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
