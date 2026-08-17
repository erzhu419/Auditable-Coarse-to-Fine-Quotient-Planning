from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_layout_factorization_campaign_v50 as campaign
from acfqp import construction_k7_layout_factorization_failure_v50 as failure


def test_v50_registered_failure_is_frozen_and_gates_remain_locked() -> None:
    frozen = failure.freeze_layout_factorization_failure_v50()
    assert failure.verify_layout_factorization_failure_v50(frozen) is frozen
    assert frozen.failure_id == failure.FAILURE_ID
    assert len(frozen.canonical_bytes) == failure.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == failure.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["failed_seed"] == 501_401
    assert document["failed_decision_index"] == 0
    assert document["same_identity_rerun_forbidden"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v50_campaign_public_runner_refuses_same_identity_rerun() -> None:
    with pytest.raises(
        campaign.ConstructionK7LayoutFactorizationCampaignV50Error,
        match="same-identity rerun is forbidden",
    ):
        campaign.run_layout_factorization_campaign_v50()
