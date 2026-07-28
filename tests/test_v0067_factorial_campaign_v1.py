from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.factorial_sample_efficiency_gate_v1 as gate
from acfqp.v0067_factorial_campaign_v1 import (
    V0067FactorialCampaignInvariantViolation,
    V0067FactorialCampaignV1,
    V0067FactorialCampaignVerificationV1,
    run_v0067_factorial_campaign_v1,
    verify_v0067_factorial_campaign_v1,
)


@pytest.fixture(scope="module")
def real_campaign() -> tuple[
    V0067FactorialCampaignV1,
    V0067FactorialCampaignVerificationV1,
]:
    campaign = run_v0067_factorial_campaign_v1()
    return campaign, verify_v0067_factorial_campaign_v1(campaign)


def test_real_factorial_gate_closes_all_registered_cells(
    real_campaign: tuple[
        V0067FactorialCampaignV1,
        V0067FactorialCampaignVerificationV1,
    ],
) -> None:
    campaign, verification = real_campaign
    assert len(campaign.arm_results) == 16
    assert campaign.gate_result.online_gate_passed
    assert verification.online_gate_passed
    assert campaign.gate_result.confidence_reconciliation.joint_tail_upper == (
        Fraction(97, 25_000)
    )
    assert (
        campaign.gate_result.confidence_reconciliation.joint_confidence_lower
        == Fraction(24_903, 25_000)
    )
    assert campaign.pairing_verification.quotient_rows_verified == 142
    assert campaign.pairing_verification.direct_rows_verified == 90


def test_real_factorial_preserves_narrow_claim_and_gate_locks(
    real_campaign: tuple[
        V0067FactorialCampaignV1,
        V0067FactorialCampaignVerificationV1,
    ],
) -> None:
    campaign, verification = real_campaign
    assert not campaign.gate_result.meta_prior_target_savings_claimed
    assert campaign.gate_result.offline_inclusive_status == "NOT_ESTABLISHED"
    assert campaign.gate_result.claim_scope == gate.REGISTERED_CLAIM_SCOPE
    assert not campaign.counter_completeness_claimed
    assert (
        campaign.counter_completeness_gate_status
        == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert (
        campaign.workload_economics_gate_status
        == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    assert campaign.official_scalar_cost is None
    assert campaign.official_N_break_even is None
    assert not campaign.official_execution_allowed
    assert not verification.independent_implementation_claimed
    assert verification.separate_semantic_replay
    assert not verification.counter_completeness_claimed


def test_real_factorial_native_accounting_is_explicit(
    real_campaign: tuple[
        V0067FactorialCampaignV1,
        V0067FactorialCampaignVerificationV1,
    ],
) -> None:
    counters = real_campaign[0].native_counters
    assert counters.source_proxy_comparison_draws == 5_451_776
    assert counters.source_proxy_physical_unique_draws == 5_242_880
    assert (
        counters.deduplicated_registered_native_target_acquisition_draws
        == 32_555_008
    )
    assert counters.factorial_comparison_target_acquisition_draws == 52_576_256
    assert (
        counters.deduplicated_registered_native_target_support_queries
        == 464
    )
    assert counters.factorial_comparison_target_support_queries == 748
    assert (
        counters.target_deduplication_semantics
        == (
            "DEDUPLICATED_REGISTERED_REAL_NATIVE_AUTHORITIES_"
            "NOT_PHYSICAL_CRN_BYTES"
        )
    )
    assert not counters.source_project_cost_complete
    assert not counters.heterogeneous_work_scalarized
    assert not counters.counter_completeness_claimed


def test_meta_sequential_cells_bind_typed_cap_narrowing_instantiations(
    real_campaign: tuple[
        V0067FactorialCampaignV1,
        V0067FactorialCampaignVerificationV1,
    ],
) -> None:
    rows = tuple(
        item
        for item in real_campaign[0].arm_results
        if item.arm == gate.META_PRIOR_SEQUENTIAL
    )
    assert len(rows) == 3
    assert all(
        type(item.target_operator_instantiation)
        is gate.TargetSequentialOperatorInstantiationV1
        and item.target_operator_instantiation.target_maximum_draws_per_row
        == 16_384
        and item.target_operator_instantiation.source_maximum_draws_per_row
        == 131_072
        and not item.target_operator_instantiation.exact_profile_transfer_claimed
        and item.target_operator_instantiation.operator_family_instantiation_only
        for item in rows
    )
    assert len(
        {
            item.target_operator_instantiation.instantiation_id
            for item in rows
        }
    ) == 3


def test_negative_control_is_feasible_exact_fallback_not_infeasibility(
    real_campaign: tuple[
        V0067FactorialCampaignV1,
        V0067FactorialCampaignVerificationV1,
    ],
) -> None:
    rows = tuple(
        item
        for item in real_campaign[0].arm_results
        if item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
    )
    assert len(rows) == 4
    assert all(
        item.terminal_class is gate.TerminalClass.PLAN_CERTIFICATE
        and item.exact_failure_probability == Fraction(2277, 16000)
        and item.work.fallback.exact_kernel_queries == 60
        for item in rows
    )


def test_campaign_claim_lock_mutations_fail(
    real_campaign: tuple[
        V0067FactorialCampaignV1,
        V0067FactorialCampaignVerificationV1,
    ],
) -> None:
    campaign, verification = real_campaign
    with pytest.raises(V0067FactorialCampaignInvariantViolation):
        replace(campaign, counter_completeness_claimed=True)
    with pytest.raises(V0067FactorialCampaignInvariantViolation):
        replace(campaign, official_scalar_cost=0)
    with pytest.raises(V0067FactorialCampaignInvariantViolation):
        replace(verification, independent_implementation_claimed=True)
    with pytest.raises(V0067FactorialCampaignInvariantViolation):
        replace(verification, separate_semantic_replay=False)
